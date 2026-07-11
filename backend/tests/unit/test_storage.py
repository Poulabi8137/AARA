from __future__ import annotations

import pytest

from app.core.exceptions import AuthenticationError, AuthorizationError
from app.providers.storage.base import BaseStorageProvider, StorageFile, StorageResult


class TestStorageTypes:
    def test_storage_file_defaults(self):
        f = StorageFile(path="test.txt", content=b"hello")
        assert f.content_type == "application/octet-stream"
        assert f.size == 0

    def test_storage_result_success(self):
        r = StorageResult(success=True, path="test.txt", url="https://example.com")
        assert r.url == "https://example.com"

    def test_storage_result_error(self):
        r = StorageResult(success=False, path="test.txt", error="not found")
        assert r.error == "not found"


class TestStorageProvider:
    @pytest.fixture
    def provider(self):
        class MockStorage(BaseStorageProvider):
            async def upload(self, bucket, path, content, content_type="application/octet-stream"):
                return StorageResult(success=True, path=path, url=f"https://storage/{path}")

            async def download(self, bucket, path):
                return StorageFile(path=path, content=b"data")

            async def delete(self, bucket, path):
                return True

            async def list_files(self, bucket, prefix=""):
                return [StorageFile(path="f.txt", content=b"")]

            async def get_signed_url(self, bucket, path, expires_in=3600):
                return f"https://signed/{path}"

            async def create_bucket(self, name, is_public=False):
                return True

            async def delete_bucket(self, name):
                return True

            async def bucket_exists(self, name):
                return True

        return MockStorage()

    async def test_upload(self, provider):
        result = await provider.upload("bucket", "path", b"data")
        assert result.success is True
        assert result.path == "path"

    async def test_download(self, provider):
        file = await provider.download("bucket", "path")
        assert file is not None
        assert file.content == b"data"

    async def test_delete(self, provider):
        assert await provider.delete("bucket", "path") is True

    async def test_list_files(self, provider):
        files = await provider.list_files("bucket")
        assert len(files) == 1

    async def test_signed_url(self, provider):
        url = await provider.get_signed_url("bucket", "path")
        assert url is not None

    async def test_bucket_ops(self, provider):
        assert await provider.create_bucket("test") is True
        assert await provider.bucket_exists("test") is True
        assert await provider.delete_bucket("test") is True


class TestNewExceptions:
    def test_authorization_error(self):
        e = AuthorizationError("Not allowed")
        assert e.error_code.code == "AUTHORIZATION_ERROR"
        assert e.error_code.http_status == 403

    def test_authorization_error_message(self):
        e = AuthorizationError("custom message")
        assert "custom message" in str(e)

    def test_authentication_error_default(self):
        e = AuthenticationError()
        assert e.error_code.http_status == 401
        assert e.error_code.message == "Authentication failed"

    def test_authentication_error_custom(self):
        e = AuthenticationError("custom auth message")
        assert "custom auth message" in str(e)
