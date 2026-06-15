from __future__ import annotations

import os
from pathlib import Path

from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger("vectorstore.chroma")

_CHROMA_INSTANCE: Any = None


def _persist_dir() -> Path:
    path = Path(settings.vectorstore_persist_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


async def get_chroma_client() -> Any:
    """Return a singleton ChromaDB client.

    For production use the Chroma server container (port 8001).
    Falls back to ephemeral in-memory when the server is unreachable.
    """
    global _CHROMA_INSTANCE
    if _CHROMA_INSTANCE is not None:
        return _CHROMA_INSTANCE

    host = os.getenv("CHROMA_HOST", "localhost")
    port = int(os.getenv("CHROMA_PORT", "8001"))

    try:
        _CHROMA_INSTANCE = await chromadb.AsyncHttpClient(
            host=host,
            port=port,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=False,
            ),
        )
        await _CHROMA_INSTANCE.heartbeat()
        logger.info("connected to ChromaDB server", extra={"host": host, "port": port})
    except Exception:
        logger.warning(
            "ChromaDB server unreachable, falling back to ephemeral client",
            extra={"host": host, "port": port},
        )
        _CHROMA_INSTANCE = chromadb.EphemeralClient(
            settings=ChromaSettings(
                anonymized_telemetry=False,
            ),
        )
    return _CHROMA_INSTANCE


async def reset_chroma_client() -> None:
    """Force client re-creation — useful for tests."""
    global _CHROMA_INSTANCE
    if _CHROMA_INSTANCE is not None:
        try:
            await _CHROMA_INSTANCE.reset()
        except Exception:
            pass
        _CHROMA_INSTANCE = None
