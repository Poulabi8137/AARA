from __future__ import annotations

import asyncio
import time

import httpx

from app.ai.search.models import PaperMetadata

BASE_URL = "https://api.semanticscholar.org/graph/v1"
SEARCH_URL = f"{BASE_URL}/paper/search"
PAPER_FIELDS = (
    "title,authors,abstract,externalIds,year,venue,"
    "citationCount,openAccessPdf,url,fieldsOfStudy"
)


class SemanticScholarProvider:
    provider_id = "semantic_scholar"

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self._api_key = api_key
        self._timeout = timeout
        self._max_retries = max_retries
        self._client: httpx.AsyncClient | None = None
        self._last_request_time = 0.0

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {"User-Agent": "AARA/1.0"}
            if self._api_key:
                headers["x-api-key"] = self._api_key
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                headers=headers,
            )
        return self._client

    async def search(self, query: str, limit: int = 20) -> list[PaperMetadata]:
        client = await self._get_client()
        all_papers: list[PaperMetadata] = []
        batch_size = min(limit, 100)
        offset = 0

        while len(all_papers) < limit:
            await self._rate_limit()
            params = {
                "query": query,
                "limit": min(batch_size, limit - len(all_papers)),
                "fields": PAPER_FIELDS,
                "offset": offset,
            }

            data = await self._request_with_retry(client, params)
            if data is None:
                break

            papers_data = data.get("data", [])
            if not papers_data:
                break

            for p in papers_data:
                paper = self._parse_paper(p)
                all_papers.append(paper)

            offset += len(papers_data)

            if len(papers_data) < batch_size:
                break

        return all_papers[:limit]

    async def _rate_limit(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < 3.0:
            await asyncio.sleep(3.0 - elapsed)
        self._last_request_time = time.monotonic()

    async def _request_with_retry(
        self,
        client: httpx.AsyncClient,
        params: dict,
    ) -> dict | None:
        for attempt in range(self._max_retries):
            try:
                response = await client.get(SEARCH_URL, params=params)
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
        for a in data.get("authors", []):
            if name := a.get("name"):
                authors.append(name)

        doi = None
        if ext_ids := data.get("externalIds"):
            doi = ext_ids.get("DOI")

        pdf_url = None
        if oa_pdf := data.get("openAccessPdf"):
            pdf_url = oa_pdf.get("url")

        keywords = [fos for fos in data.get("fieldsOfStudy", []) if fos]

        return PaperMetadata(
            title=data.get("title", ""),
            authors=authors,
            abstract=data.get("abstract", "") or "",
            doi=doi,
            year=data.get("year"),
            venue=data.get("venue", "") or "",
            citation_count=data.get("citationCount", 0) or 0,
            pdf_url=pdf_url,
            landing_page=data.get("url"),
            source=self.provider_id,
            keywords=keywords,
        )

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
