from __future__ import annotations

from datetime import datetime

import httpx

from app.core.exceptions import ConfigurationError
from app.providers.storage.base import BaseStorageProvider, StorageFile, StorageResult


class SupabaseStorage(BaseStorageProvider):
    def __init__(
        self,
        supabase_url: str | None = None,
        service_key: str | None = None,
    ) -> None:
        if not supabase_url or not service_key:
            raise ConfigurationError(
                "Supabase URL and service key required",
                key="supabase_storage",
            )
        self._base_url = f"{supabase_url}/storage/v1"
        self._headers = {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
        }
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers=self._headers,
                timeout=30.0,
            )
        return self._client

    async def upload(
        self,
        bucket: str,
        path: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> StorageResult:
        client = await self._get_client()
        try:
            response = await client.post(
                f"/object/{bucket}/{path}",
                content=content,
                headers={"Content-Type": content_type},
            )
            if response.is_success:
                url = f"{self._base_url}/object/public/{bucket}/{path}"
                return StorageResult(success=True, path=path, url=url)
            return StorageResult(
                success=False, path=path, error=response.text
            )
        except httpx.HTTPError as e:
            return StorageResult(success=False, path=path, error=str(e))

    async def download(self, bucket: str, path: str) -> StorageFile | None:
        client = await self._get_client()
        try:
            response = await client.get(f"/object/{bucket}/{path}")
            if response.is_success:
                return StorageFile(
                    path=path,
                    content=response.content,
                    content_type=response.headers.get("content-type", "application/octet-stream"),
                    size=len(response.content),
                )
            return None
        except httpx.HTTPError:
            return None

    async def delete(self, bucket: str, path: str) -> bool:
        client = await self._get_client()
        try:
            response = await client.delete(f"/object/{bucket}/{path}")
            return response.is_success
        except httpx.HTTPError:
            return False

    async def list_files(self, bucket: str, prefix: str = "") -> list[StorageFile]:
        client = await self._get_client()
        try:
            response = await client.post(
                f"/object/list/{bucket}",
                json={"prefix": prefix},
            )
            if response.is_success:
                files = []
                for item in response.json():
                    files.append(
                        StorageFile(
                            path=item.get("name", ""),
                            content=b"",
                            content_type=item.get("mimetype", "application/octet-stream"),
                            size=item.get("size", 0),
                            created_at=(
                                datetime.fromisoformat(item["created_at"])
                                if item.get("created_at") else None
                            ),
                            updated_at=(
                                datetime.fromisoformat(item["updated_at"])
                                if item.get("updated_at") else None
                            ),
                        )
                    )
                return files
            return []
        except httpx.HTTPError:
            return []

    async def get_signed_url(
        self, bucket: str, path: str, expires_in: int = 3600
    ) -> str | None:
        client = await self._get_client()
        try:
            response = await client.post(
                f"/object/sign/{bucket}/{path}",
                json={"expiresIn": expires_in},
            )
            if response.is_success:
                data = response.json()
                signed_path = data.get("signedURL") or data.get("url", "")
                return f"{self._base_url}{signed_path}"
            return None
        except httpx.HTTPError:
            return None

    async def create_bucket(self, name: str, is_public: bool = False) -> bool:
        client = await self._get_client()
        try:
            response = await client.post(
                "/bucket",
                json={"name": name, "public": is_public},
            )
            return response.is_success
        except httpx.HTTPError:
            return False

    async def delete_bucket(self, name: str) -> bool:
        client = await self._get_client()
        try:
            response = await client.delete(f"/bucket/{name}")
            return response.is_success
        except httpx.HTTPError:
            return False

    async def bucket_exists(self, name: str) -> bool:
        client = await self._get_client()
        try:
            response = await client.get(f"/bucket/{name}")
            return response.is_success
        except httpx.HTTPError:
            return False

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
