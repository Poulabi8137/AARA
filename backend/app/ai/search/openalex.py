from __future__ import annotations

import asyncio
import time

import httpx

from app.ai.search.models import PaperMetadata

BASE_URL = "https://api.openalex.org"
WORKS_URL = f"{BASE_URL}/works"


class OpenAlexProvider:
    provider_id = "openalex"

    def __init__(
        self,
        email: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self._email = email
        self._timeout = timeout
        self._max_retries = max_retries
        self._client: httpx.AsyncClient | None = None
        self._last_request_time = 0.0

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            ua = "mailto:aara@research.app"
            if self._email:
                ua = f"mailto:{self._email}"
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                headers={"User-Agent": ua},
            )
        return self._client

    async def search(self, query: str, limit: int = 20) -> list[PaperMetadata]:
        client = await self._get_client()
        all_papers: list[PaperMetadata] = []
        per_page = min(limit, 200)
        page = 1

        while len(all_papers) < limit:
            await self._rate_limit()
            params = {
                "search": query,
                "per-page": per_page,
                "page": page,
                "sort": "relevance_score:desc",
            }

            data = await self._request_with_retry(client, params)
            if data is None:
                break

            results = data.get("results", [])
            if not results:
                break

            for r in results:
                paper = self._parse_paper(r)
                all_papers.append(paper)

            page += 1

            total = data.get("meta", {}).get("count", 0)
            if len(results) < per_page or len(all_papers) >= total:
                break

        return all_papers[:limit]

    async def _rate_limit(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < 0.1:
            await asyncio.sleep(0.1 - elapsed)
        self._last_request_time = time.monotonic()

    async def _request_with_retry(
        self,
        client: httpx.AsyncClient,
        params: dict,
    ) -> dict | None:
        for attempt in range(self._max_retries):
            try:
                response = await client.get(WORKS_URL, params=params)
                if response.status_code == 429:
                    wait = 2 ** (attempt + 1)
                    await asyncio.sleep(wait)
                    continue
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < self._max_retries - 1:
                    wait = 2 ** (attempt + 1)
                    await asyncio.sleep(wait)
                    continue
                return None
            except httpx.TimeoutException:
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return None
            except Exception:
                return None
        return None

    def _parse_paper(self, data: dict) -> PaperMetadata:
        authors = []
        for a in data.get("authorships", []):
            author_data = a.get("author")
            name = author_data.get("display_name") if author_data else None
            if name:
                authors.append(name)

        doi = None
        if doi_url := data.get("doi"):
            doi = doi_url.replace("https://doi.org/", "")

        year = data.get("publication_year")

        venue = ""
        loc = data.get("primary_location")
        source = loc.get("source") if loc else None
        if source:
            venue = source.get("display_name", "") or ""

        pdf_url = None
        if oa := data.get("open_access"):
            pdf_url = oa.get("oa_url")

        keywords = [
            kw.get("display_name", "")
            for kw in data.get("keywords", [])
            if kw.get("display_name")
        ]

        abstract = self._parse_abstract(data.get("abstract_inverted_index"))

        return PaperMetadata(
            title=data.get("title", "") or "",
            authors=authors,
            abstract=abstract,
            doi=doi,
            year=year,
            venue=venue,
            citation_count=data.get("cited_by_count", 0) or 0,
            pdf_url=pdf_url,
            landing_page=data.get("id"),
            source=self.provider_id,
            keywords=keywords,
        )

    def _parse_abstract(self, inverted_index: dict | None) -> str:
        if not inverted_index:
            return ""
        word_positions: list[tuple[str, list[int]]] = [
            (word, positions) for word, positions in inverted_index.items()
        ]
        max_pos = max(
            (pos for _, positions in word_positions for pos in positions),
            default=-1,
        )
        if max_pos < 0:
            return ""
        words: list[str] = [""] * (max_pos + 1)
        for word, positions in word_positions:
            for pos in positions:
                if 0 <= pos < len(words):
                    words[pos] = word
        return " ".join(words)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
