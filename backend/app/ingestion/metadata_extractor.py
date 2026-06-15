from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def extract_default_metadata(
    project_id: str | None = None,
    source: str | None = None,
    filename: str | None = None,
    author: str | None = None,
    page_number: int | None = None,
    chunk_index: int | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Build a standardised metadata dict for every chunk stored in ChromaDB.

    This creates a consistent metadata shape that all LangGraph agents
    (Planner, Retriever, Summarizer, GapDetector) can rely on.
    """
    metadata: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if project_id is not None:
        metadata["project_id"] = str(project_id)
    if source is not None:
        metadata["source"] = source
    if filename is not None:
        metadata["filename"] = filename
    if author is not None:
        metadata["author"] = author
    if page_number is not None:
        metadata["page_number"] = page_number
    if chunk_index is not None:
        metadata["chunk_index"] = chunk_index

    metadata.update(extra)
    return metadata
