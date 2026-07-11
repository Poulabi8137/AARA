from __future__ import annotations

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.ingestion.cleaner import DocumentCleaner
from app.ai.ingestion.indexer import IndexedPaper, PaperIndexer
from app.ai.ingestion.pdf_downloader import DownloadResult, PdfDownloader
from app.ai.ingestion.pdf_parser import ParsedPaper, ParsedSection, PdfParser
from app.ai.retrieval.chunking import ChunkingStrategy
from app.ai.search.models import PaperMetadata

# =============================================================================
# PDF Downloader Tests
# =============================================================================

class TestDownloadResult:
    def test_defaults(self):
        r = DownloadResult(success=False)
        assert r.file_path == ""
        assert r.content_type == ""
        assert r.file_size == 0
        assert r.source_url == ""
        assert r.error_message == ""

    def test_full(self):
        r = DownloadResult(
            success=True, file_path="/tmp/test.pdf",
            content_type="application/pdf", file_size=1024,
            source_url="https://example.com/paper.pdf",
        )
        assert r.success is True
        assert r.file_size == 1024


class TestPdfDownloader:
    @pytest.fixture
    def downloader(self):
        return PdfDownloader(timeout=5.0, max_retries=2)

    async def test_empty_url(self, downloader):
        result = await downloader.download("")
        assert result.success is False
        assert "empty" in result.error_message.lower()

    def _make_stream(self, mock_response):
        stream = MagicMock()
        stream.__aenter__ = AsyncMock(return_value=mock_response)
        stream.__aexit__ = AsyncMock()
        return stream

    @staticmethod
    def _aiter_bytes(chunks):
        async def gen():
            for c in chunks:
                yield c
        return gen

    async def test_invalid_content_type(self, downloader):
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html"}

        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=self._make_stream(mock_response))

        with patch.object(downloader, "_get_client", new=AsyncMock(return_value=mock_client)):
            result = await downloader.download("https://example.com/paper")

        assert result.success is False
        assert "content type" in result.error_message.lower()

    async def test_http_404(self, downloader):
        mock_response = AsyncMock()
        mock_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=self._make_stream(mock_response))

        with patch.object(downloader, "_get_client", new=AsyncMock(return_value=mock_client)):
            result = await downloader.download("https://example.com/missing")

        assert result.success is False

    async def test_successful_download(self, downloader, tmp_path):
        downloader._download_dir = str(tmp_path)

        pdf_content = b"%PDF-1.4 mock content"
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/pdf"}
        mock_response.aiter_bytes = self._aiter_bytes([pdf_content])

        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=self._make_stream(mock_response))

        with patch.object(downloader, "_get_client", new=AsyncMock(return_value=mock_client)):
            result = await downloader.download("https://example.com/paper.pdf")

        assert result.success is True
        assert result.file_size > 0
        assert "pdf" in result.content_type
        assert os.path.exists(result.file_path)

    async def test_retry_on_429(self, downloader, tmp_path):
        downloader._download_dir = str(tmp_path)

        pdf_content = b"%PDF-1.4 mock content"
        mock_429 = AsyncMock()
        mock_429.status_code = 429

        mock_200 = AsyncMock()
        mock_200.status_code = 200
        mock_200.headers = {"content-type": "application/pdf"}
        mock_200.aiter_bytes = self._aiter_bytes([pdf_content])

        mock_client = AsyncMock()
        mock_client.stream = MagicMock(side_effect=[
            self._make_stream(mock_429),
            self._make_stream(mock_200),
        ])

        with patch.object(downloader, "_get_client", new=AsyncMock(return_value=mock_client)):
            result = await downloader.download("https://example.com/paper.pdf")

        assert result.success is True
        assert result.file_size > 0

    async def test_all_retries_exhausted(self, downloader):
        mock_429 = AsyncMock()
        mock_429.status_code = 429

        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=self._make_stream(mock_429))

        with patch.object(downloader, "_get_client", new=AsyncMock(return_value=mock_client)):
            result = await downloader.download("https://example.com/paper.pdf")

        assert result.success is False
        assert "retries" in result.error_message.lower()

    def test_is_valid_pdf(self, downloader):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4 content")
            path = f.name
        try:
            assert downloader._is_valid_pdf(path) is True
        finally:
            os.remove(path)

    def test_is_invalid_pdf(self, downloader):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"not a pdf")
            path = f.name
        try:
            assert downloader._is_valid_pdf(path) is False
        finally:
            os.remove(path)

    def test_is_valid_pdf_content_type(self, downloader):
        assert downloader._is_valid_pdf_content_type("application/pdf") is True
        assert downloader._is_valid_pdf_content_type("application/x-pdf") is True
        assert downloader._is_valid_pdf_content_type("application/octet-stream") is True
        assert downloader._is_valid_pdf_content_type("text/html") is False
        assert downloader._is_valid_pdf_content_type("image/png") is False


# =============================================================================
# PDF Parser Tests
# =============================================================================

class TestParsedSection:
    def test_defaults(self):
        s = ParsedSection(heading="Intro", content="Text")
        assert s.heading == "Intro"
        assert s.content == "Text"
        assert s.page_number == 0


class TestParsedPaper:
    def test_defaults(self):
        p = ParsedPaper(title="Test")
        assert p.title == "Test"
        assert p.authors == []
        assert p.body == ""
        assert p.sections == []
        assert p.references == []
        assert p.page_count == 0


class TestPdfParser:
    @pytest.fixture
    def parser(self):
        return PdfParser()

    @pytest.fixture
    def real_pdf_path(self):
        import fitz
        path = os.path.join(tempfile.gettempdir(), f"test_doc_{os.getpid()}.pdf")
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Test Paper Title", fontsize=14)
        page.insert_text((50, 80), "Alice Author", fontsize=10)
        page.insert_text((50, 100), "Bob Researcher", fontsize=10)
        page.insert_text((50, 140), "Abstract", fontsize=12)
        page.insert_text((50, 160), "This is a test abstract.", fontsize=10)
        page.insert_text((50, 200), "1. Introduction", fontsize=12)
        page.insert_text((50, 220), "Introduction text here.", fontsize=10)
        page.insert_text((50, 260), "2. Method", fontsize=12)
        page.insert_text((50, 280), "Method description.", fontsize=10)
        page.insert_text((50, 320), "References", fontsize=12)
        page.insert_text((50, 340), "[1] Author. 2024. Paper title.", fontsize=10)
        doc.save(path)
        doc.close()
        yield path
        if os.path.exists(path):
            os.remove(path)

    def test_parse_pymupdf(self, parser, real_pdf_path):
        result = parser.parse(real_pdf_path)
        assert result.title == "Test Paper Title"
        assert result.extraction_method == "pymupdf"
        assert result.page_count > 0
        assert len(result.body) > 0

    def test_extract_structure(self, parser):
        text = (
            "Test Paper Title\n"
            "Alice Author\n"
            "Abstract\n"
            "This is a test abstract.\n"
            "1. Introduction\n"
            "Introduction text here.\n"
            "2. Method\n"
            "Method description.\n"
            "References\n"
            "[1] Author. 2024. Paper title.\n"
        )
        title, authors, abstract, body, sections, references = (
            parser._extract_structure(text)
        )
        assert title == "Test Paper Title"
        assert any("Introduction" in s.heading for s in sections)
        assert any("Method" in s.heading for s in sections)
        assert any("References" in s.heading for s in sections)

    def test_is_reference_line(self, parser):
        assert parser._is_reference_line("[1] Author. 2024. Title.") is True
        assert parser._is_reference_line("[10] Name et al. 2023.") is True
        assert parser._is_reference_line("https://doi.org/10.1234/abc") is True
        assert parser._is_reference_line("arXiv:2301.12345") is True
        assert parser._is_reference_line("This is body text") is False
        assert parser._is_reference_line("Introduction") is False

    def test_fallback_to_pdfplumber(self, parser):
        with (
            patch.object(parser, "_parse_pymupdf", side_effect=Exception("fail")),
            patch.object(parser, "_parse_pdfplumber", return_value=ParsedPaper(
                title="Fallback Paper", body="body", page_count=1,
                extraction_method="pdfplumber",
            )),
        ):
            result = parser.parse("/fake/path.pdf")
            assert result.title == "Fallback Paper"
            assert result.extraction_method == "pdfplumber"

    def test_both_fail(self, parser):
        with (
            patch.object(parser, "_parse_pymupdf", side_effect=Exception("fail")),
            patch.object(parser, "_parse_pdfplumber", side_effect=Exception("fail")),
        ):
            result = parser.parse("/fake/path.pdf")
            assert result.extraction_method == "failed"
            assert result.title == ""
            assert result.body == ""


# =============================================================================
# Document Cleaner Tests
# =============================================================================

class TestDocumentCleaner:
    @pytest.fixture
    def cleaner(self):
        return DocumentCleaner()

    def test_unicode_normalize(self, cleaner):
        text = "\u0041\u030a"  # A + combining ring
        normalized = cleaner._unicode_normalize(text)
        assert normalized == "\u00c5"  # Å (NFC)

    def test_clean_whitespace(self, cleaner):
        text = "Line1\r\nLine2\rLine3\tTab\n\n\nExtra\n\n"
        cleaned = cleaner._clean_whitespace(text)
        assert "\r" not in cleaned
        assert "\t" not in cleaned
        assert "\n\n\n" not in cleaned
        assert "\n\n" in cleaned
        assert "Line1\nLine2" in cleaned

    def test_remove_headers_footers(self, cleaner):
        text = "arXiv:2301.12345\nHeader2\nBody line 1\nBody line 2\n42\nBody line 3"
        cleaned = cleaner._remove_headers_footers(text)
        assert "arXiv:2301.12345" not in cleaned
        assert "Body line 1" in cleaned
        assert "Body line 2" in cleaned
        assert "Body line 3" in cleaned

    def test_remove_duplicate_lines(self, cleaner):
        text = "Line 1\nLine 2\nLine 2\nLine 3\nLine 3\nLine 3\nLine 4"
        cleaned = cleaner._remove_duplicate_lines(text)
        lines = cleaned.split("\n")
        assert len(lines) == 4
        assert lines == ["Line 1", "Line 2", "Line 3", "Line 4"]

    def test_remove_empty_pages(self, cleaner):
        text = "Page1 content\f \fPage3 content"
        cleaned = cleaner._remove_empty_pages(text)
        assert "Page1 content" in cleaned
        assert "Page3 content" in cleaned
        assert "\f" in cleaned

    def test_remove_empty_pages_single(self, cleaner):
        text = "Single page content"
        cleaned = cleaner._remove_empty_pages(text)
        assert cleaned == text

    def test_full_clean_pipeline(self, cleaner):
        parsed = ParsedPaper(
            title="Test \u0041\u030a Paper",  # A with combining ring
            body="Line 1\n\n\nLine 2\nLine 2\narXiv:1234.5678\nLine 3\n42\nLine 4",
            sections=[
                ParsedSection(heading="Intro", content="Content\xa0here", page_number=1),
            ],
            page_count=2,
        )
        result = cleaner.clean(parsed)
        assert "\u00c5" in result.title  # NFC normalized
        assert "Line 2\nLine 3" in result.body or "Line 2\nLine 2" not in result.body

    def test_short_text_not_affected(self, cleaner):
        text = "Short"
        cleaned = cleaner._remove_headers_footers(text)
        assert cleaned == text


# =============================================================================
# Paper Indexer Tests
# =============================================================================

class TestIndexedPaper:
    def test_defaults(self):
        meta = PaperMetadata(title="Test", doi="10.1/a")
        ip = IndexedPaper(metadata=meta)
        assert ip.metadata.title == "Test"
        assert ip.parsed_text == ""
        assert ip.sections == []
        assert ip.references == []
        assert ip.chunks is None
        assert ip.download is None


class TestPaperIndexer:
    @pytest.fixture
    def indexer(self):
        return PaperIndexer()

    async def test_no_pdf_url(self, indexer):
        paper = PaperMetadata(title="No PDF", doi="10.1/a", pdf_url=None)
        result = await indexer.index(paper)
        assert result.chunks is None
        assert result.pdf_path == ""
        assert result.download is None

    async def test_download_failure(self, indexer):
        paper = PaperMetadata(title="Fail", doi="10.1/b", pdf_url="https://example.com/fail.pdf")
        mock_downloader = AsyncMock()
        mock_downloader.download = AsyncMock(return_value=DownloadResult(
            success=False, source_url="https://example.com/fail.pdf",
            error_message="Download failed",
        ))
        indexer._downloader = mock_downloader

        result = await indexer.index(paper)
        assert result.download is not None
        assert result.download.success is False
        assert result.chunks is None

    async def test_parse_failure(self, indexer):
        paper = PaperMetadata(
            title="Parse Fail", doi="10.1/c",
            pdf_url="https://example.com/paper.pdf",
        )
        mock_downloader = AsyncMock()
        mock_downloader.download = AsyncMock(return_value=DownloadResult(
            success=True, file_path="/tmp/paper.pdf",
            content_type="application/pdf", file_size=100,
            source_url="https://example.com/paper.pdf",
        ))

        mock_parser = MagicMock()
        mock_parser.parse = MagicMock(return_value=ParsedPaper(
            title="", body="", page_count=0, extraction_method="failed",
        ))

        indexer._downloader = mock_downloader
        indexer._parser = mock_parser

        result = await indexer.index(paper)
        assert result.extraction_method == "failed"
        assert result.chunks is None

    async def test_successful_index(self, indexer):
        import fitz
        pdf_path = os.path.join(tempfile.gettempdir(), f"test_index_{os.getpid()}.pdf")
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Test Paper", fontsize=14)
        page.insert_text((50, 100), "Abstract\nThis is the abstract.", fontsize=10)
        page.insert_text((50, 160), "Introduction\nIntro text here.", fontsize=10)
        page.insert_text((50, 220), "Method\nMethod text here.", fontsize=10)
        page.insert_text((50, 280), "Conclusion\nConclusion text here.", fontsize=10)
        doc.save(pdf_path)
        doc.close()

        try:
            paper = PaperMetadata(
                title="Test Paper", doi="10.1/test",
                pdf_url="https://example.com/test.pdf",
            )
            mock_downloader = AsyncMock()
            mock_downloader.download = AsyncMock(return_value=DownloadResult(
                success=True, file_path=pdf_path,
                content_type="application/pdf", file_size=os.path.getsize(pdf_path),
                source_url="https://example.com/test.pdf",
            ))

            indexer._downloader = mock_downloader

            result = await indexer.index(paper)
            assert result.chunks is not None
            assert len(result.chunks.chunks) > 0
            assert result.pdf_path == pdf_path
            assert result.extraction_method == "pymupdf"
            assert result.metadata.title == "Test Paper"
        finally:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

    async def test_chunk_strategy_respected(self, indexer):
        import fitz
        pdf_path = os.path.join(tempfile.gettempdir(), f"test_chunk_{os.getpid()}.pdf")
        doc = fitz.open()
        page = doc.new_page()
        long_text = "Word " * 1000
        page.insert_text((50, 50), long_text[:2000], fontsize=10)
        doc.save(pdf_path)
        doc.close()

        try:
            paper = PaperMetadata(
                title="Chunk Test", doi="10.1/chunk",
                pdf_url="https://example.com/chunk.pdf",
            )
            mock_downloader = AsyncMock()
            mock_downloader.download = AsyncMock(return_value=DownloadResult(
                success=True, file_path=pdf_path,
                content_type="application/pdf", file_size=os.path.getsize(pdf_path),
                source_url="https://example.com/chunk.pdf",
            ))
            indexer._downloader = mock_downloader

            result = await indexer.index(
                paper,
                chunk_strategy=ChunkingStrategy.FIXED_SIZE,
                chunk_size=50,
                chunk_overlap=5,
            )
            assert result.chunks is not None
            assert result.chunks.strategy == "fixed_size"
            assert result.chunks.chunk_size == 50
            assert result.chunks.overlap == 5
            assert len(result.chunks.chunks) > 1
        finally:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)


# =============================================================================
# Provider Result Tests
# =============================================================================

class TestProviderResult:
    def test_defaults(self):
        from app.ai.search.models import ProviderResult
        r = ProviderResult(
            provider="test", status="success",
            latency=0.5, paper_count=10,
        )
        assert r.provider == "test"
        assert r.status == "success"
        assert r.latency == 0.5
        assert r.paper_count == 10
        assert r.error_message == ""

    async def test_service_tracks_results(self):
        from app.ai.search.service import AcademicSearchService

        class MockProvider:
            provider_id = "mock_provider"
            async def search(self, query, limit=20):
                return [PaperMetadata(title="A")]

        service = AcademicSearchService(providers=[MockProvider()])
        results = await service.search("test", limit=5)
        assert len(results) == 1

        provider_results = service.last_provider_results
        assert len(provider_results) == 1
        assert provider_results[0].provider == "mock_provider"
        assert provider_results[0].status == "success"
        assert provider_results[0].latency >= 0
        assert provider_results[0].paper_count == 1

    async def test_service_tracks_errors(self):
        from app.ai.search.service import AcademicSearchService

        class FailingProvider:
            provider_id = "failing"
            async def search(self, query, limit=20):
                raise RuntimeError("API down")

        service = AcademicSearchService(providers=[FailingProvider()])
        results = await service.search("test", limit=5)
        assert results == []

        provider_results = service.last_provider_results
        assert len(provider_results) == 1
        assert provider_results[0].provider == "failing"
        assert provider_results[0].status == "error"
        assert "API down" in provider_results[0].error_message
        assert provider_results[0].paper_count == 0
