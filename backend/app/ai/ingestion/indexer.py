from __future__ import annotations

from dataclasses import dataclass, field

from app.ai.ingestion.cleaner import DocumentCleaner
from app.ai.ingestion.pdf_downloader import DownloadResult, PdfDownloader
from app.ai.ingestion.pdf_parser import ParsedSection, PdfParser
from app.ai.retrieval.chunking import ChunkingStrategy, ChunkResult, TextChunker
from app.ai.search.models import PaperMetadata


@dataclass
class IndexedPaper:
    metadata: PaperMetadata
    parsed_text: str = ""
    sections: list[ParsedSection] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    chunks: ChunkResult | None = None
    download: DownloadResult | None = None
    pdf_path: str = ""
    extraction_method: str = ""


class PaperIndexer:
    def __init__(
        self,
        downloader: PdfDownloader | None = None,
        parser: PdfParser | None = None,
        cleaner: DocumentCleaner | None = None,
        chunker: TextChunker | None = None,
    ) -> None:
        self._downloader = downloader or PdfDownloader()
        self._parser = parser or PdfParser()
        self._cleaner = cleaner or DocumentCleaner()
        self._chunker = chunker or TextChunker()

    async def index(
        self,
        paper: PaperMetadata,
        chunk_strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
    ) -> IndexedPaper:
        if not paper.pdf_url:
            return IndexedPaper(metadata=paper)

        download = await self._downloader.download(paper.pdf_url)
        if not download.success:
            return IndexedPaper(
                metadata=paper, download=download,
            )

        parsed = self._parser.parse(download.file_path)
        if parsed.extraction_method == "failed":
            return IndexedPaper(
                metadata=paper, download=download,
                pdf_path=download.file_path,
                extraction_method="failed",
            )

        cleaned = self._cleaner.clean(parsed)

        text_to_chunk = cleaned.body or cleaned.abstract or cleaned.title
        chunks = self._chunker.chunk(
            text_to_chunk,
            strategy=chunk_strategy,
            chunk_size=chunk_size,
            overlap=chunk_overlap,
        )

        return IndexedPaper(
            metadata=paper,
            parsed_text=cleaned.body,
            sections=cleaned.sections,
            references=cleaned.references,
            chunks=chunks,
            download=download,
            pdf_path=download.file_path,
            extraction_method=cleaned.extraction_method,
        )
