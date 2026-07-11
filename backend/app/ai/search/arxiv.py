from __future__ import annotations

import asyncio
import re
import time
import xml.etree.ElementTree as ET

import httpx

from app.ai.search.models import PaperMetadata

BASE_URL = "https://export.arxiv.org/api/query"
ATOM_NS = "http://www.w3.org/2005/Atom"
ARXIV_NS = "http://arxiv.org/schemas/atom"


class ArxivProvider:
    provider_id = "arxiv"

    def __init__(
        self,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self._timeout = timeout
        self._max_retries = max_retries
        self._client: httpx.AsyncClient | None = None
        self._last_request_time = 0.0

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                headers={"User-Agent": "AARA/1.0"},
            )
        return self._client

    async def search(self, query: str, limit: int = 20) -> list[PaperMetadata]:
        client = await self._get_client()
        all_papers: list[PaperMetadata] = []
        batch_size = min(limit, 100)
        start = 0

        while len(all_papers) < limit:
            await self._rate_limit()
            params = {
                "search_query": f"all:{query}",
                "start": str(start),
                "max_results": str(min(batch_size, limit - len(all_papers))),
            }

            data = await self._request_with_retry(client, params)
            if data is None:
                break

            papers = self._parse_response(data)
            if not papers:
                break

            all_papers.extend(papers)
            start += len(papers)

            if len(papers) < batch_size:
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
    ) -> str | None:
        for attempt in range(self._max_retries):
            try:
                response = await client.get(BASE_URL, params=params)
                if response.status_code == 429:
                    wait = 2 ** (attempt + 1)
                    await asyncio.sleep(wait)
                    continue
                response.raise_for_status()
                return response.text
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

    def _parse_response(self, xml_text: str) -> list[PaperMetadata]:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []

        papers: list[PaperMetadata] = []
        for entry in root.findall(f"{{{ATOM_NS}}}entry"):
            paper = self._parse_entry(entry)
            papers.append(paper)

        return papers

    def _parse_entry(self, entry: ET.Element) -> PaperMetadata:
        def _text(tag: str) -> str:
            el = entry.find(f"{{{ATOM_NS}}}{tag}")
            return el.text or "" if el is not None else ""

        title = self._clean_html(_text("title"))
        summary = self._clean_html(_text("summary"))

        authors = []
        for a in entry.findall(f"{{{ATOM_NS}}}author"):
            name_el = a.find(f"{{{ATOM_NS}}}name")
            if name_el is not None and name_el.text:
                authors.append(name_el.text)

        landing_page = _text("id")

        arxiv_id = ""
        if landing_page:
            m = re.search(r"(\d{4}\.\d{4,5})(v\d+)?$", landing_page)
            if m:
                arxiv_id = m.group(1)

        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else None

        published_str = _text("published")
        year = None
        if published_str:
            m = re.match(r"(\d{4})", published_str)
            if m:
                year = int(m.group(1))

        doi = None
        for link in entry.findall(f"{{{ATOM_NS}}}link"):
            link_title = link.get("title", "")
            if link_title == "doi":
                doi = link.get("href", "")
                if doi:
                    doi = doi.replace("https://doi.org/", "")

        categories = []
        for cat in entry.findall(f"{{{ARXIV_NS}}}primary_category"):
            term = cat.get("term", "")
            if term:
                categories.append(term)

        return PaperMetadata(
            title=title,
            authors=authors,
            abstract=summary,
            doi=doi,
            year=year,
            venue="arXiv",
            citation_count=0,
            pdf_url=pdf_url,
            landing_page=landing_page,
            source=self.provider_id,
            keywords=categories,
        )

    def _clean_html(self, text: str) -> str:
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
