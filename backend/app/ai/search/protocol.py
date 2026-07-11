from __future__ import annotations

from typing import Protocol

from app.ai.search.models import PaperMetadata


class AcademicSearchProvider(Protocol):
    async def search(
        self,
        query: str,
        limit: int = 20,
    ) -> list[PaperMetadata]:
        ...
