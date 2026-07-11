from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PaperMetadata:
    title: str
    authors: list[str] = field(default_factory=list)
    abstract: str = ""
    doi: str | None = None
    year: int | None = None
    venue: str = ""
    citation_count: int = 0
    pdf_url: str | None = None
    landing_page: str | None = None
    source: str = ""
    keywords: list[str] = field(default_factory=list)


@dataclass
class ProviderResult:
    provider: str
    status: str
    latency: float
    paper_count: int
    error_message: str = ""
