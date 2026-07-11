from __future__ import annotations

import os
from dataclasses import dataclass
from uuid import uuid4

import httpx


@dataclass
class DownloadResult:
    success: bool
    file_path: str = ""
    content_type: str = ""
    file_size: int = 0
    source_url: str = ""
    error_message: str = ""


DOWNLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "storage", "downloads",
)


class PdfDownloader:
    def __init__(
        self,
        timeout: float = 60.0,
        max_retries: int = 3,
        max_file_size_mb: int = 50,
        download_dir: str = "",
    ) -> None:
        self._timeout = timeout
        self._max_retries = max_retries
        self._max_file_size = max_file_size_mb * 1024 * 1024
        self._download_dir = download_dir or DOWNLOAD_DIR
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                follow_redirects=True,
                headers={"User-Agent": "AARA/1.0"},
            )
        return self._client

    async def download(self, url: str) -> DownloadResult:
        if not url:
            return DownloadResult(
                success=False, error_message="Empty URL",
            )

        client = await self._get_client()

        for attempt in range(self._max_retries):
            try:
                async with client.stream("GET", url) as response:
                    if response.status_code == 429:
                        import asyncio
                        wait = 2 ** (attempt + 1)
                        await asyncio.sleep(wait)
                        continue
                    if response.status_code != 200:
                        continue

                    content_type = response.headers.get("content-type", "").lower()
                    if not self._is_valid_pdf_content_type(content_type):
                        return DownloadResult(
                            success=False,
                            source_url=url,
                            error_message=f"Invalid content type: {content_type}",
                        )

                    content_length = response.headers.get("content-length")
                    if content_length and int(content_length) > self._max_file_size:
                        return DownloadResult(
                            success=False,
                            source_url=url,
                            error_message=f"File too large: {content_length} bytes",
                        )

                    os.makedirs(self._download_dir, exist_ok=True)
                    file_path = os.path.join(
                        self._download_dir, f"{uuid4().hex}.pdf",
                    )

                    file_size = 0
                    with open(file_path, "wb") as f:
                        async for chunk in response.aiter_bytes():
                            file_size += len(chunk)
                            if file_size > self._max_file_size:
                                f.close()
                                os.remove(file_path)
                                return DownloadResult(
                                    success=False,
                                    source_url=url,
                                    error_message="Stream exceeded max size",
                                )
                            f.write(chunk)

                    if file_size == 0:
                        os.remove(file_path)
                        return DownloadResult(
                            success=False,
                            source_url=url,
                            error_message="Empty file downloaded",
                        )

                    if not self._is_valid_pdf(file_path):
                        os.remove(file_path)
                        return DownloadResult(
                            success=False,
                            source_url=url,
                            error_message="Not a valid PDF",
                        )

                    return DownloadResult(
                        success=True,
                        file_path=file_path,
                        content_type=content_type,
                        file_size=file_size,
                        source_url=url,
                    )

            except httpx.TimeoutException:
                if attempt < self._max_retries - 1:
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                    continue
                return DownloadResult(
                    success=False, source_url=url,
                    error_message="Download timed out",
                )
            except httpx.HTTPError as e:
                if attempt < self._max_retries - 1:
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                    continue
                return DownloadResult(
                    success=False, source_url=url,
                    error_message=f"HTTP error: {e}",
                )
            except OSError as e:
                return DownloadResult(
                    success=False, source_url=url,
                    error_message=f"File system error: {e}",
                )

        return DownloadResult(
            success=False, source_url=url,
            error_message="All retries exhausted",
        )

    def _is_valid_pdf_content_type(self, content_type: str) -> bool:
        valid = [
            "application/pdf",
            "application/x-pdf",
            "application/octet-stream",
        ]
        return any(v in content_type for v in valid)

    def _is_valid_pdf(self, file_path: str) -> bool:
        try:
            with open(file_path, "rb") as f:
                header = f.read(5)
            return header == b"%PDF-"
        except OSError:
            return False

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
