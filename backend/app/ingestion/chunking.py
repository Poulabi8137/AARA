from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger

logger = get_logger("ingestion.chunking")

DEFAULT_CHUNK_SIZE: int = 1000
DEFAULT_CHUNK_OVERLAP: int = 200


@dataclass
class Chunk:
    content: str
    index: int
    start_char: int
    end_char: int
    metadata: dict[str, Any] = field(default_factory=dict)


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    metadata: dict[str, Any] | None = None,
) -> list[Chunk]:
    """Recursively split text into overlapping chunks.

    Splits on paragraph breaks first, then newlines, then sentences,
    then falls back to character-level splits to respect chunk_size.
    """
    if not text.strip():
        return []

    separators = ["\n\n", "\n", ". ", "! ", "? ", " "]
    chunks = _recursive_split(text, separators, chunk_size, chunk_overlap)

    result: list[Chunk] = []
    for i, chunk_text_content in enumerate(chunks):
        start = text.find(chunk_text_content[:50])
        end = start + len(chunk_text_content) if start >= 0 else 0
        result.append(
            Chunk(
                content=chunk_text_content,
                index=i,
                start_char=max(start, 0),
                end_char=end,
                metadata=dict(metadata or {}),
            )
        )

    logger.debug(
        "chunked text",
        extra={
            "total_chunks": len(result),
            "chunk_size": chunk_size,
            "overlap": chunk_overlap,
        },
    )
    return result


def _recursive_split(
    text: str,
    separators: list[str],
    chunk_size: int,
    chunk_overlap: int,
) -> list[str]:
    """Recursive splitter that respects chunk_size boundaries."""
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    chunks: list[str] = []
    for sep in separators:
        if sep in text:
            segments = text.split(sep)
            current_chunk: list[str] = []
            current_len = 0

            for seg in segments:
                seg_with_sep = seg + sep
                seg_len = len(seg_with_sep)

                if current_len + seg_len <= chunk_size:
                    current_chunk.append(seg_with_sep)
                    current_len += seg_len
                else:
                    if current_chunk:
                        chunks.append("".join(current_chunk).strip())
                    overlap_text = _get_overlap_text(
                        "".join(current_chunk), chunk_overlap
                    )
                    current_chunk = [overlap_text, seg_with_sep]
                    current_len = len(overlap_text) + seg_len

            if current_chunk:
                chunks.append("".join(current_chunk).strip())

            if all(len(c) <= chunk_size for c in chunks):
                return [c for c in chunks if c.strip()]
            else:
                result: list[str] = []
                for c in chunks:
                    if len(c) <= chunk_size:
                        if c.strip():
                            result.append(c)
                    else:
                        result.extend(
                            _recursive_split(
                                c,
                                separators[separators.index(sep) + 1 :],
                                chunk_size,
                                chunk_overlap,
                            )
                        )
                return [r for r in result if r.strip()]

    for i in range(0, len(text), chunk_size - chunk_overlap):
        chunk = text[i : i + chunk_size]
        if chunk.strip():
            chunks.append(chunk)

    return chunks


def _get_overlap_text(chunk: str, overlap: int) -> str:
    if len(chunk) <= overlap:
        return chunk
    return chunk[-overlap:]
