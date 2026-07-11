from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


@dataclass
class StorageFile:
    path: str
    content: bytes
    content_type: str = "application/octet-stream"
    size: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class StorageResult:
    success: bool
    path: str
    url: str | None = None
    error: str | None = None
    metadata: dict[str, Any] | None = None


class BaseStorageProvider(Protocol):
    async def upload(
        self, bucket: str, path: str, content: bytes, content_type: str = "application/octet-stream"
    ) -> StorageResult: ...

    async def download(self, bucket: str, path: str) -> StorageFile | None: ...

    async def delete(self, bucket: str, path: str) -> bool: ...

    async def list_files(self, bucket: str, prefix: str = "") -> list[StorageFile]: ...

    async def get_signed_url(
        self, bucket: str, path: str, expires_in: int = 3600
    ) -> str | None: ...

    async def create_bucket(self, name: str, is_public: bool = False) -> bool: ...

    async def delete_bucket(self, name: str) -> bool: ...

    async def bucket_exists(self, name: str) -> bool: ...
