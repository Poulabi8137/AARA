from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from app.core.config import GlobalConfig
from app.core.database import DatabaseManager, init_db_manager
from app.core.exceptions import ConfigurationError
from app.observability.logging import configure_logging, get_logger


class ConfigSource:
    async def get(self, key: str) -> Any:
        raise NotImplementedError


class EnvConfigSource(ConfigSource):
    def __init__(self, prefix: str = "AARA_") -> None:
        self._prefix = prefix

    async def get(self, key: str) -> Any:
        return os.environ.get(f"{self._prefix}{key}")


class ConfigResolver:
    def __init__(self) -> None:
        self._sources: list[tuple[int, ConfigSource]] = []

    def add_source(self, source: ConfigSource, priority: int) -> None:
        self._sources.append((priority, source))
        self._sources.sort(key=lambda x: x[0], reverse=True)

    async def get(self, key: str, default: Any = None) -> Any:
        for _, source in self._sources:
            value = await source.get(key)
            if value is not None:
                return value
        return default


class ApplicationContext:
    def __init__(
        self,
        config: GlobalConfig,
        config_resolver: ConfigResolver,
    ) -> None:
        self.config = config
        self.config_resolver = config_resolver
        self._started = False
        self._shutdown = False
        self.db_manager: DatabaseManager | None = None

    @property
    def is_running(self) -> bool:
        return self._started and not self._shutdown


class ApplicationInitializer:
    def __init__(self, env_file: str | Path | None = None) -> None:
        self._env_file = env_file

    async def initialize(self) -> ApplicationContext:
        if self._env_file and os.path.exists(str(self._env_file)):
            load_dotenv(str(self._env_file))

        config = GlobalConfig()

        configure_logging(
            log_level=config.log_level,
            environment=config.environment,
        )
        logger = get_logger("aara.init")
        logger.info("configuration_loaded", environment=config.environment)

        if config.encryption_key == "insecure-dev-key" and config.is_production:
            raise ConfigurationError(
                "ENCRYPTION_KEY must be set in production",
                key="encryption_key",
            )

        if config.jwt_secret.startswith("insecure-") and config.is_production:
            raise ConfigurationError(
                "JWT_SECRET must be set to a secure value in production",
                key="jwt_secret",
            )

        config_resolver = ConfigResolver()
        config_resolver.add_source(EnvConfigSource(), priority=4)

        db_manager = init_db_manager(
            database_url=config.database_url,
            pool_size=config.database_pool_size,
            max_overflow=config.database_max_overflow,
        )

        context = ApplicationContext(
            config=config,
            config_resolver=config_resolver,
        )
        context.db_manager = db_manager

        await db_manager.init_db()
        context._started = True

        logger.info(
            "application_initialized",
            app_name=config.app_name,
            version=config.app_version,
        )

        return context

    async def shutdown(self, context: ApplicationContext) -> None:
        logger = get_logger("aara.shutdown")
        context._shutdown = True
        if context.db_manager:
            await context.db_manager.close_db()
        logger.info("application_shutdown")
