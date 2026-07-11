from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ChunkingStrategy(Enum):
    FIXED_SIZE = "fixed_size"
    PARAGRAPH = "paragraph"
    SEMANTIC = "semantic"
    RECURSIVE = "recursive"


@dataclass
class ChunkResult:
    chunks: list[str]
    strategy: str = "fixed_size"
    chunk_size: int = 512
    overlap: int = 64
    metadata: list[dict[str, str]] = field(default_factory=list)


class TextChunker:
    def chunk(
        self,
        text: str,
        strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE,
        chunk_size: int = 512,
        overlap: int = 64,
    ) -> ChunkResult:
        if strategy == ChunkingStrategy.FIXED_SIZE:
            return self._chunk_fixed(text, chunk_size, overlap)
        elif strategy == ChunkingStrategy.PARAGRAPH:
            return self._chunk_paragraph(text, chunk_size, overlap)
        elif strategy == ChunkingStrategy.RECURSIVE or strategy == ChunkingStrategy.SEMANTIC:
            return self._chunk_recursive(text, chunk_size, overlap)
        return self._chunk_fixed(text, chunk_size, overlap)

    def _chunk_fixed(self, text: str, size: int, overlap: int) -> ChunkResult:
        chunks = []
        metadata = []
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            chunks.append(text[start:end])
            metadata.append({"start": str(start), "end": str(end)})
            start += size - overlap
            if start >= len(text):
                break
        return ChunkResult(
            chunks=chunks, strategy="fixed_size", chunk_size=size,
            overlap=overlap, metadata=metadata,
        )

    def _chunk_paragraph(self, text: str, size: int, overlap: int) -> ChunkResult:
        paragraphs = [p for p in text.split("\n\n") if p.strip()]
        chunks = []
        metadata = []
        current = ""
        for p in paragraphs:
            if len(current) + len(p) < size:
                current += p + "\n\n"
            else:
                if current:
                    chunks.append(current.strip())
                    metadata.append({"source": "paragraph"})
                current = p + "\n\n"
        if current:
            chunks.append(current.strip())
            metadata.append({"source": "paragraph"})
        return ChunkResult(
            chunks=chunks, strategy="paragraph", chunk_size=size,
            overlap=overlap, metadata=metadata,
        )

    def _chunk_recursive(self, text: str, size: int, overlap: int) -> ChunkResult:
        separators = ["\n\n", "\n", ". ", " ", ""]
        chunks = []
        metadata = []

        def _split(text: str, sep_idx: int) -> None:
            if len(text) <= size:
                chunks.append(text)
                metadata.append({"separator": separators[sep_idx - 1] if sep_idx > 0 else "char"})
                return
            sep = separators[sep_idx] if sep_idx < len(separators) else ""
            if not sep:
                idx = size
                chunks.append(text[:idx])
                metadata.append({"separator": "char"})
                _split(text[idx - overlap:], sep_idx)
                return
            idx = text.rfind(sep, 0, size)
            if idx < size // 2:
                _split(text, sep_idx + 1)
                return
            chunk = text[:idx]
            chunks.append(chunk)
            metadata.append({"separator": sep})
            _split(text[idx - overlap:], sep_idx)

        _split(text, 0)
        return ChunkResult(
            chunks=chunks, strategy="recursive", chunk_size=size,
            overlap=overlap, metadata=metadata,
        )
