from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CitationVerificationResult:
    verified: bool = False
    doi: str = ""
    title: str = ""
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    error: str = ""


class CitationVerificationHook:
    def __init__(self) -> None:
        self._cache: dict[str, CitationVerificationResult] = {}

    async def verify(self, doi: str) -> CitationVerificationResult:
        if doi in self._cache:
            return self._cache[doi]

        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.crossref.org/works/{doi}",
                    timeout=10.0,
                )
                if response.is_success:
                    data = response.json()
                    message = data.get("message", {})
                    authors = []
                    for author in message.get("author", []):
                        given = author.get("given", "")
                        family = author.get("family", "")
                        authors.append(f"{given} {family}".strip())

                    result = CitationVerificationResult(
                        verified=True,
                        doi=doi,
                        title=message.get("title", [""])[0],
                        authors=authors,
                        year=message.get("published", {}).get("date-parts", [[None]])[0][0],
                    )
                else:
                    result = CitationVerificationResult(
                        verified=False, doi=doi, error=f"HTTP {response.status_code}"
                    )
        except Exception as e:
            result = CitationVerificationResult(
                verified=False, doi=doi, error=str(e)
            )

        self._cache[doi] = result
        return result

    async def verify_batch(self, dois: list[str]) -> list[CitationVerificationResult]:
        return [await self.verify(doi) for doi in dois]

    def clear_cache(self) -> None:
        self._cache.clear()
