from __future__ import annotations


class ContextCompressor:
    async def compress(self, texts: list[str], target_ratio: float = 0.5) -> list[str]:
        compressed = []
        for text in texts:
            if not text:
                compressed.append("")
                continue
            target_len = max(100, int(len(text) * target_ratio))
            if len(text) <= target_len:
                compressed.append(text)
            else:
                compressed.append(self._compress_text(text, target_len))
        return compressed

    def _compress_text(self, text: str, target_len: int) -> str:
        if len(text) <= target_len:
            return text

        sentences = text.replace("! ", ". ").replace("? ", ". ").split(". ")
        compressed = []
        current_len = 0

        for sentence in sentences:
            sentence_len = len(sentence) + 2
            if current_len + sentence_len <= target_len:
                compressed.append(sentence)
                current_len += sentence_len
            else:
                remaining = target_len - current_len
                if remaining > 20:
                    compressed.append(sentence[:remaining])
                break

        result = ". ".join(compressed)
        if result and not result.endswith("."):
            result += "."
        return result

    async def summarize_to_tokens(self, text: str, max_tokens: int) -> str:
        max_chars = max_tokens * 4
        if len(text) <= max_chars:
            return text
        return text[:max_chars]
