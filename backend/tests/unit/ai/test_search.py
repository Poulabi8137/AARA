from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.ai.search.arxiv import ArxivProvider
from app.ai.search.models import PaperMetadata
from app.ai.search.openalex import OpenAlexProvider
from app.ai.search.semantic_scholar import SemanticScholarProvider
from app.ai.search.service import AcademicSearchService


class TestPaperMetadata:
    def test_defaults(self):
        p = PaperMetadata(title="Test")
        assert p.title == "Test"
        assert p.authors == []
        assert p.abstract == ""
        assert p.doi is None
        assert p.year is None
        assert p.venue == ""
        assert p.citation_count == 0
        assert p.pdf_url is None
        assert p.landing_page is None
        assert p.source == ""
        assert p.keywords == []

    def test_full_construction(self):
        p = PaperMetadata(
            title="Full Paper",
            authors=["Alice", "Bob"],
            abstract="An abstract.",
            doi="10.1234/test",
            year=2024,
            venue="Test Venue",
            citation_count=42,
            pdf_url="https://example.com/paper.pdf",
            landing_page="https://example.com",
            source="test",
            keywords=["AI", "ML"],
        )
        assert p.title == "Full Paper"
        assert p.authors == ["Alice", "Bob"]


class TestSemanticScholarProvider:
    @pytest.fixture
    def provider(self):
        return SemanticScholarProvider(api_key=None, timeout=5.0)

    def test_parse_paper_full(self, provider):
        data = {
            "paperId": "abc123",
            "title": "Test Paper",
            "authors": [{"name": "Alice"}, {"name": "Bob"}],
            "abstract": "This is an abstract.",
            "externalIds": {"DOI": "10.1234/test"},
            "year": 2024,
            "venue": "Test Venue",
            "citationCount": 42,
            "openAccessPdf": {"url": "https://example.com/paper.pdf"},
            "url": "https://semanticscholar.org/paper/abc123",
            "fieldsOfStudy": ["Computer Science", "AI"],
        }
        paper = provider._parse_paper(data)
        assert paper.title == "Test Paper"
        assert paper.authors == ["Alice", "Bob"]
        assert paper.abstract == "This is an abstract."
        assert paper.doi == "10.1234/test"
        assert paper.year == 2024
        assert paper.venue == "Test Venue"
        assert paper.citation_count == 42
        assert paper.pdf_url == "https://example.com/paper.pdf"
        assert paper.landing_page == "https://semanticscholar.org/paper/abc123"
        assert paper.source == "semantic_scholar"
        assert paper.keywords == ["Computer Science", "AI"]

    def test_parse_paper_minimal(self, provider):
        data = {
            "paperId": "min",
            "title": "Minimal",
            "authors": [],
            "externalIds": None,
            "openAccessPdf": None,
        }
        paper = provider._parse_paper(data)
        assert paper.title == "Minimal"
        assert paper.authors == []
        assert paper.abstract == ""
        assert paper.doi is None
        assert paper.year is None
        assert paper.citation_count == 0
        assert paper.pdf_url is None

    async def test_search_empty_response(self, provider):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch.object(provider, "_get_client", new=AsyncMock(return_value=mock_client)):
            results = await provider.search("test", limit=5)

        assert results == []

    async def test_search_http_error(self, provider):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=mock_response,
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch.object(provider, "_get_client", new=AsyncMock(return_value=mock_client)):
            results = await provider.search("test", limit=5)

        assert results == []

    async def test_rate_limit_retry(self, provider):
        mock_429 = MagicMock(spec=httpx.Response)
        mock_429.status_code = 429
        mock_429.raise_for_status.side_effect = httpx.HTTPStatusError(
            "rate limited", request=MagicMock(), response=mock_429,
        )

        mock_200 = MagicMock(spec=httpx.Response)
        mock_200.status_code = 200
        mock_200.json.return_value = {
            "data": [{"paperId": "a", "title": "Paper", "authors": []}],
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[mock_429, mock_200])

        with patch.object(provider, "_get_client", new=AsyncMock(return_value=mock_client)):
            results = await provider.search("test", limit=5)

        assert len(results) == 1
        assert results[0].title == "Paper"

    async def test_all_retries_exhausted(self, provider):
        mock_429 = MagicMock(spec=httpx.Response)
        mock_429.status_code = 429
        mock_429.raise_for_status.side_effect = httpx.HTTPStatusError(
            "rate limited", request=MagicMock(), response=mock_429,
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_429)

        with patch.object(provider, "_get_client", new=AsyncMock(return_value=mock_client)):
            results = await provider.search("test", limit=5)

        assert results == []


class TestOpenAlexProvider:
    @pytest.fixture
    def provider(self):
        return OpenAlexProvider(timeout=5.0)

    def test_parse_paper_full(self, provider):
        data = {
            "id": "https://openalex.org/W123",
            "title": "OpenAlex Paper",
            "authorships": [
                {"author": {"display_name": "Alice"}},
                {"author": {"display_name": "Bob"}},
            ],
            "doi": "https://doi.org/10.1234/oa",
            "publication_year": 2023,
            "primary_location": {
                "source": {"display_name": "Nature"},
            },
            "cited_by_count": 100,
            "open_access": {"oa_url": "https://example.com/oa.pdf"},
            "keywords": [{"display_name": "ML"}, {"display_name": "AI"}],
        }
        paper = provider._parse_paper(data)
        assert paper.title == "OpenAlex Paper"
        assert paper.authors == ["Alice", "Bob"]
        assert paper.doi == "10.1234/oa"
        assert paper.year == 2023
        assert paper.venue == "Nature"
        assert paper.citation_count == 100
        assert paper.pdf_url == "https://example.com/oa.pdf"
        assert paper.source == "openalex"
        assert paper.keywords == ["ML", "AI"]

    def test_parse_minimal(self, provider):
        data = {"id": "", "title": ""}
        paper = provider._parse_paper(data)
        assert paper.title == ""
        assert paper.authors == []
        assert paper.doi is None
        assert paper.year is None
        assert paper.venue == ""
        assert paper.citation_count == 0
        assert paper.pdf_url is None
        assert paper.keywords == []

    def test_parse_abstract_inverted_index(self, provider):
        data = {
            "abstract_inverted_index": {
                "This": [0],
                "is": [1],
                "a": [2],
                "test": [3],
            },
        }
        abstract = provider._parse_abstract(data.get("abstract_inverted_index"))
        assert abstract == "This is a test"

    def test_parse_abstract_empty(self, provider):
        assert provider._parse_abstract(None) == ""
        assert provider._parse_abstract({}) == ""

    async def test_search_success(self, provider):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "meta": {"count": 1},
            "results": [
                {"id": "W1", "title": "Result", "authorships": []},
            ],
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch.object(provider, "_get_client", new=AsyncMock(return_value=mock_client)):
            results = await provider.search("test", limit=5)

        assert len(results) == 1
        assert results[0].title == "Result"

    async def test_search_empty(self, provider):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"meta": {"count": 0}, "results": []}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch.object(provider, "_get_client", new=AsyncMock(return_value=mock_client)):
            results = await provider.search("test", limit=5)

        assert results == []


class TestArxivProvider:
    @pytest.fixture
    def provider(self):
        return ArxivProvider(timeout=5.0)

    def test_parse_response(self, provider):
        xml = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2301.12345</id>
    <title>Test arXiv Paper</title>
    <author><name>Alice</name></author>
    <author><name>Bob</name></author>
    <summary>This is an abstract.</summary>
    <published>2023-01-15T00:00:00Z</published>
    <arxiv:primary_category xmlns:arxiv="http://arxiv.org/schemas/atom" term="cs.AI"/>
  </entry>
</feed>"""
        papers = provider._parse_response(xml)
        assert len(papers) == 1
        p = papers[0]
        assert p.title == "Test arXiv Paper"
        assert p.authors == ["Alice", "Bob"]
        assert p.abstract == "This is an abstract."
        assert p.year == 2023
        assert p.venue == "arXiv"
        assert p.source == "arxiv"
        assert p.keywords == ["cs.AI"]
        assert p.landing_page == "http://arxiv.org/abs/2301.12345"
        assert p.pdf_url == "https://arxiv.org/pdf/2301.12345"
        assert p.citation_count == 0

    def test_parse_response_with_doi(self, provider):
        xml = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2301.67890</id>
    <title>Paper with DOI</title>
    <author><name>Author</name></author>
    <summary>Abstract text.</summary>
    <published>2023-06-01T00:00:00Z</published>
    <link title="doi" href="https://doi.org/10.1234/arxiv.doi" rel="related"/>
  </entry>
</feed>"""
        papers = provider._parse_response(xml)
        assert len(papers) == 1
        assert papers[0].doi == "10.1234/arxiv.doi"

    def test_parse_response_empty(self, provider):
        xml = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
</feed>"""
        papers = provider._parse_response(xml)
        assert papers == []

    def test_parse_response_invalid_xml(self, provider):
        papers = provider._parse_response("not xml")
        assert papers == []

    def test_clean_html(self, provider):
        assert provider._clean_html("Test <b>Paper</b>") == "Test Paper"
        assert provider._clean_html("  Multiple   spaces  ") == "Multiple spaces"
        assert provider._clean_html("No tags") == "No tags"
        assert provider._clean_html("") == ""

    async def test_search_success(self, provider):
        xml = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2301.12345</id>
    <title>Test Paper</title>
    <author><name>Author</name></author>
    <summary>Abstract.</summary>
    <published>2023-01-01T00:00:00Z</published>
  </entry>
</feed>"""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = xml

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch.object(provider, "_get_client", new=AsyncMock(return_value=mock_client)):
            results = await provider.search("test", limit=5)

        assert len(results) == 1
        assert results[0].title == "Test Paper"

    async def test_search_http_error(self, provider):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=mock_response,
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch.object(provider, "_get_client", new=AsyncMock(return_value=mock_client)):
            results = await provider.search("test", limit=5)

        assert results == []


class TestAcademicSearchService:
    def _make_paper(
        self,
        title: str,
        doi: str | None = None,
        year: int | None = 2024,
        citation_count: int = 10,
        source: str = "test",
        authors: list[str] | None = None,
        abstract: str = "",
        pdf_url: str | None = None,
        keywords: list[str] | None = None,
    ) -> PaperMetadata:
        return PaperMetadata(
            title=title,
            authors=authors or ["Author"],
            abstract=abstract,
            doi=doi,
            year=year,
            venue="Venue",
            citation_count=citation_count,
            pdf_url=pdf_url,
            landing_page=f"https://example.com/{title.lower().replace(' ', '-')}",
            source=source,
            keywords=keywords or [],
        )

    async def test_dedup_by_doi(self):
        p1 = self._make_paper("Paper A", doi="10.1234/a")
        p2 = self._make_paper("Paper A Dupe", doi="10.1234/a")

        svc = AcademicSearchService(providers=[])
        merged = svc._deduplicate([p1, p2])
        assert len(merged) == 1
        assert merged[0].doi == "10.1234/a"

    async def test_dedup_by_doi_case_insensitive(self):
        p1 = self._make_paper("Paper A", doi="10.1234/ABC")
        p2 = self._make_paper("Paper A Dupe", doi="10.1234/abc")

        svc = AcademicSearchService(providers=[])
        merged = svc._deduplicate([p1, p2])
        assert len(merged) == 1

    async def test_dedup_by_normalized_title(self):
        p1 = self._make_paper("Attention Is All You Need")
        p2 = self._make_paper("Attention Is All You Need!")

        svc = AcademicSearchService(providers=[])
        merged = svc._deduplicate([p1, p2])
        assert len(merged) == 1

    async def test_dedup_keeps_better_paper_on_title_match(self):
        p1 = self._make_paper("Test Paper", doi=None, citation_count=5, abstract="")
        p2 = self._make_paper(
            "Test Paper!", doi="10.1234/test",
            citation_count=100, abstract="Full abstract",
        )

        svc = AcademicSearchService(providers=[])
        merged = svc._deduplicate([p1, p2])
        assert len(merged) == 1
        assert merged[0].doi == "10.1234/test"
        assert merged[0].citation_count == 100

    async def test_dedup_by_similar_title(self):
        p1 = self._make_paper("Attention Is All You Need")
        p2 = self._make_paper("Attention is all you need")

        svc = AcademicSearchService(providers=[])
        merged = svc._deduplicate([p1, p2])
        assert len(merged) == 1

    async def test_dedup_by_jaccard_similarity(self):
        p1 = self._make_paper("Attention Is All You Need")
        p2 = self._make_paper("Attention Is All You Need Extended Version")

        svc = AcademicSearchService(providers=[])
        merged = svc._deduplicate([p1, p2])
        assert len(merged) == 1

    async def test_no_false_positive_jaccard(self):
        p1 = self._make_paper("Paper A")
        p2 = self._make_paper("Paper B")

        svc = AcademicSearchService(providers=[])
        merged = svc._deduplicate([p1, p2])
        assert len(merged) == 2

    async def test_distinct_titles_not_deduped(self):
        p1 = self._make_paper("Paper One", doi="10.1234/1")
        p2 = self._make_paper("Paper Two", doi="10.1234/2")

        svc = AcademicSearchService(providers=[])
        merged = svc._deduplicate([p1, p2])
        assert len(merged) == 2

    async def test_merge_multiple_sources(self):
        class MockProvider:
            def __init__(self, papers):
                self._papers = papers
            async def search(self, query, limit=20):
                return self._papers[:limit]

        provider_a = MockProvider([
            self._make_paper("Paper A", doi="10.1/a", source="ss"),
            self._make_paper("Paper B", doi="10.1/b", source="ss"),
        ])
        provider_b = MockProvider([
            self._make_paper("Paper A", doi="10.1/a", source="oa"),
            self._make_paper("Paper C", doi="10.1/c", source="oa"),
        ])

        svc = AcademicSearchService(providers=[provider_a, provider_b])
        results = await svc.search("test", limit=10)
        assert len(results) == 3

        assert any(r.doi == "10.1/a" for r in results)
        assert any(r.doi == "10.1/b" for r in results)
        assert any(r.doi == "10.1/c" for r in results)

    async def test_partial_provider_failure(self):
        mock_provider_a = AsyncMock()
        mock_provider_a.search = AsyncMock(return_value=[
            self._make_paper("Paper A", doi="10.1/a"),
        ])
        mock_provider_b = AsyncMock()
        mock_provider_b.search = AsyncMock(side_effect=Exception("API down"))

        svc = AcademicSearchService(providers=[mock_provider_a, mock_provider_b])
        results = await svc.search("test", limit=10)
        assert len(results) == 1
        assert results[0].doi == "10.1/a"

    async def test_all_providers_fail(self):
        mock_provider_a = AsyncMock()
        mock_provider_a.search = AsyncMock(side_effect=Exception("fail"))
        mock_provider_b = AsyncMock()
        mock_provider_b.search = AsyncMock(side_effect=Exception("fail"))

        svc = AcademicSearchService(providers=[mock_provider_a, mock_provider_b])
        results = await svc.search("test", limit=10)
        assert results == []

    async def test_empty_results(self):
        mock_provider = AsyncMock()
        mock_provider.search = AsyncMock(return_value=[])

        svc = AcademicSearchService(providers=[mock_provider])
        results = await svc.search("test", limit=10)
        assert results == []

    async def test_rank_by_relevance(self):
        p_old_low = self._make_paper(
            "Old Low", doi="10.1/a", year=2000,
            citation_count=0, abstract="",
        )
        p_new_high = self._make_paper(
            "New High", doi="10.1/b", year=2025,
            citation_count=500, abstract="Full abstract.",
        )
        p_mid = self._make_paper(
            "Mid", doi="10.1/c", year=2023,
            citation_count=50, abstract="Some abstract.",
        )

        svc = AcademicSearchService(providers=[])
        ranked = svc._rank([p_old_low, p_new_high, p_mid])
        assert ranked[0].doi == "10.1/b"
        assert ranked[1].doi == "10.1/c"

    async def test_limit_respected(self):
        class MockProvider:
            def __init__(self, papers):
                self._papers = papers
            async def search(self, query, limit=20):
                return self._papers[:limit]

        papers = [
            self._make_paper(f"Distinct Paper Title {i}", doi=f"10.1/{i}")
            for i in range(50)
        ]
        provider = MockProvider(papers)
        svc = AcademicSearchService(providers=[provider])
        results = await svc.search("test", limit=10)
        assert len(results) == 10

    async def test_normalize_title(self):
        svc = AcademicSearchService(providers=[])
        assert svc._normalize_title("  Hello World!  ") == "hello world"
        assert svc._normalize_title("Attention Is All You Need") == "attention is all you need"
        assert svc._normalize_title("A.I. & The Future") == "ai the future"

    async def test_should_replace(self):
        svc = AcademicSearchService(providers=[])
        existing = self._make_paper(
            "Test", citation_count=5, abstract="", doi=None, pdf_url=None,
        )
        better = self._make_paper(
            "Test", citation_count=100,
            abstract="Has abstract", doi="10.1/x", pdf_url="http://pdf",
        )
        worse = self._make_paper("Test", citation_count=1, abstract="", doi=None, pdf_url=None)

        assert svc._should_replace(existing, better) is True
        assert svc._should_replace(existing, worse) is False

    async def test_dedup_key_doi(self):
        svc = AcademicSearchService(providers=[])
        p = self._make_paper("Test", doi="10.1234/ABC")
        assert svc._dedup_key(p) == "doi:10.1234/abc"

    async def test_dedup_key_title(self):
        svc = AcademicSearchService(providers=[])
        p = self._make_paper("Hello World!")
        assert "title:" in svc._dedup_key(p)
        assert "hello world" in svc._dedup_key(p)
