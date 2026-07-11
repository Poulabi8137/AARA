from __future__ import annotations

from pathlib import Path

from app.observability.logging import get_logger


class PluginLoader:
    PLUGIN_ENTRY_POINT = "aara.plugins"

    def __init__(self) -> None:
        self._loaded: list[str] = []

    def load_plugins(self) -> list[str]:
        try:
            import importlib.metadata
            plugins = importlib.metadata.entry_points(group=self.PLUGIN_ENTRY_POINT)
            for plugin in plugins:
                try:
                    plugin.load()
                    self._loaded.append(plugin.name)
                    logger = get_logger("aara.plugins")
                    logger.info("loaded_plugin", name=plugin.name)
                except Exception as exc:
                    logger = get_logger("aara.plugins")
                    logger.error("failed_to_load_plugin", name=plugin.name, error=str(exc))
        except Exception as exc:
            logger = get_logger("aara.plugins")
            logger.warning("plugin_discovery_unavailable", error=str(exc))
        return self._loaded

    def discover_local_plugins(self, plugin_dir: str = "plugins") -> list[str]:
        plugin_path = Path(plugin_dir)
        if not plugin_path.exists():
            return []

        import importlib.util

        discovered: list[str] = []
        for pyfile in sorted(plugin_path.glob("*.py")):
            try:
                spec = importlib.util.spec_from_file_location(pyfile.stem, pyfile)
                if spec and spec.loader:
                    spec.loader.exec_module(importlib.util.module_from_spec(spec))
                    discovered.append(pyfile.stem)
            except Exception as exc:
                logger = get_logger("aara.plugins")
                logger.error("failed_to_load_local_plugin", file=str(pyfile), error=str(exc))
        return discovered

    def get_loaded(self) -> list[str]:
        return list(self._loaded)
