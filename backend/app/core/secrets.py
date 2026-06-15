from __future__ import annotations

import os
import json

from app.core.logging import get_logger

logger = get_logger("core.secrets")


class SecretManager:
    """Multi-backend secret manager supporting AWS, Azure, GCP, and env vars."""

    def __init__(self, backend: str = "env"):
        self.backend = backend
        self._initialized = False
        self._secrets: dict[str, str] = {}

    async def initialize(self) -> None:
        """Load secrets from configured backend."""
        if self._initialized:
            return

        backend = os.environ.get("SECRETS_BACKEND", self.backend)

        if backend == "aws":
            await self._load_aws_secrets()
        elif backend == "azure":
            await self._load_azure_secrets()
        elif backend == "gcp":
            await self._load_gcp_secrets()
        else:
            self._load_env_secrets()

        self._initialized = True
        logger.info("secret manager initialized", extra={"backend": backend})

    def _load_env_secrets(self) -> None:
        """Load secrets from environment variables."""
        secret_keys = [
            "SECRET_KEY", "DATABASE_URL", "OPENAI_API_KEY", "GEMINI_API_KEY",
            "REDIS_URL", "SENTRY_DSN", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY",
            "AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET",
        ]
        for key in secret_keys:
            val = os.environ.get(key)
            if val:
                self._secrets[key.lower()] = val

    async def _load_aws_secrets(self) -> None:
        """Load secrets from AWS Secrets Manager."""
        try:
            import boto3

            secret_name = os.environ.get("AWS_SECRET_NAME", "agentwatch/production")
            region = os.environ.get("AWS_REGION", "us-east-1")

            session = boto3.session.Session()
            client = session.client(service_name="secretsmanager", region_name=region)

            response = client.get_secret_value(SecretId=secret_name)
            secrets = json.loads(response["SecretString"])
            for key, val in secrets.items():
                self._secrets[key.lower()] = str(val)

            logger.info("loaded secrets from AWS Secrets Manager", extra={"secret_name": secret_name})
        except Exception as exc:
            logger.error("failed to load AWS secrets", extra={"error": str(exc)})
            raise

    async def _load_azure_secrets(self) -> None:
        """Load secrets from Azure Key Vault."""
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient

            vault_url = os.environ.get("AZURE_KEY_VAULT_URL", "")
            if not vault_url:
                raise ValueError("AZURE_KEY_VAULT_URL is required")

            credential = DefaultAzureCredential()
            client = SecretClient(vault_url=vault_url, credential=credential)

            secret_names = [
                "secret-key", "database-url", "openai-api-key", "gemini-api-key",
                "redis-url", "sentry-dsn",
            ]
            for name in secret_names:
                try:
                    secret = client.get_secret(name)
                    self._secrets[name.replace("-", "_")] = secret.value
                except Exception:
                    logger.warning("secret not found in Key Vault", extra={"secret_name": name})

            logger.info("loaded secrets from Azure Key Vault")
        except Exception as exc:
            logger.error("failed to load Azure secrets", extra={"error": str(exc)})
            raise

    async def _load_gcp_secrets(self) -> None:
        """Load secrets from GCP Secret Manager."""
        try:
            from google.cloud import secretmanager

            project_id = os.environ.get("GCP_PROJECT_ID", "")
            if not project_id:
                raise ValueError("GCP_PROJECT_ID is required")

            client = secretmanager.SecretManagerServiceClient()

            secret_names = [
                "secret-key", "database-url", "openai-api-key", "gemini-api-key",
                "redis-url", "sentry-dsn",
            ]
            for name in secret_names:
                try:
                    resource_name = f"projects/{project_id}/secrets/{name}/versions/latest"
                    response = client.access_secret_version(request={"name": resource_name})
                    self._secrets[name.replace("-", "_")] = response.payload.data.decode("UTF-8")
                except Exception:
                    logger.warning("secret not found in GCP", extra={"secret_name": name})

            logger.info("loaded secrets from GCP Secret Manager")
        except Exception as exc:
            logger.error("failed to load GCP secrets", extra={"error": str(exc)})
            raise

    def get(self, key: str, default: str | None = None) -> str | None:
        """Get a secret value."""
        return self._secrets.get(key.lower(), default)

    def require(self, key: str) -> str:
        """Get a required secret, raising an error if missing."""
        val = self.get(key)
        if val is None:
            raise RuntimeError(f"Required secret '{key}' is not configured")
        return val


_secret_manager = SecretManager()


async def initialize_secrets() -> None:
    """Initialize the global secret manager."""
    await _secret_manager.initialize()


def get_secret(key: str, default: str | None = None) -> str | None:
    return _secret_manager.get(key, default)


def require_secret(key: str) -> str:
    return _secret_manager.require(key)
