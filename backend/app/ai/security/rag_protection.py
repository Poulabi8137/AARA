from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


@dataclass
class ContentWarning:
    category: str = ""
    snippet: str = ""
    position: int = 0


@dataclass
class SanitizedContent:
    cleaned: str = ""
    factual_part: str = ""
    removed_imperative: str = ""
    warnings: list[ContentWarning] = field(default_factory=list)
    suspicion_score: float = 0.0
    requires_review: bool = False


class RAGProtectionLayer:
    CONTROL_PATTERNS = [
        (r"(?i)ignore\s+(all\s+)?(previous|above|prior)\s+instructions", "instruction_override"),
        (r"(?i)disregard\s+(all\s+)?(previous|above|prior|system)", "instruction_override"),
        (r"(?i)you\s+are\s+(not|now)\s+(a\s+)?(system|assistant|ai)", "role_override"),
        (r"(?i)new\s+instructions?\s*:", "instruction_override"),
        (r"(?i)role\s*:\s*(system|assistant|user)", "role_spoofing"),
        (r"<\|im_start\|>|<\|im_end\|>", "chat_marker"),
        (r"<\|system\|>|<\|user\|>|<\|assistant\|>", "chat_marker"),
        (r"\{\{.*?\{\{", "template_injection"),
    ]

    async def sanitize(self, retrieved_text: str, source: str = "") -> SanitizedContent:
        text = retrieved_text
        warnings = []

        invisible = re.compile(r"[\u200B-\u200D\uFEFF\u00AD\u2060-\u2064]")
        text = invisible.sub("", text)

        text = unicodedata.normalize("NFKC", text)

        for pattern, category in self.CONTROL_PATTERNS:
            matches = list(re.finditer(pattern, text))
            for match in matches:
                warnings.append(ContentWarning(
                    category=category,
                    snippet=text[max(0, match.start() - 20):match.end() + 20],
                    position=match.start(),
                ))
            text = re.sub(pattern, "[REDACTED]", text)

        suspicion_score = self._assess_suspicion(text)
        factual, imperative = self._split_factual_vs_imperative(text)

        return SanitizedContent(
            cleaned=text,
            factual_part=factual,
            removed_imperative=imperative,
            warnings=warnings,
            suspicion_score=suspicion_score,
            requires_review=suspicion_score > 0.7,
        )

    def _assess_suspicion(self, text: str) -> float:
        score = 0.0

        imperative_count = len(re.findall(
            r"(?i)^\s*(ignore|forget|disregard|you\s+must|you\s+will|do\s+not|always|never)\b",
            text, re.MULTILINE,
        ))
        total_sentences = max(1, len(re.findall(r"[.!?]\s+", text)) + 1)
        imperative_ratio = imperative_count / total_sentences
        score += imperative_ratio * 0.5

        if re.search(r"(?i)(system|assistant)\s*(prompt|message|instruction)", text):
            score += 0.3

        if text.count("```") >= 2:
            score += 0.2

        return min(score, 1.0)

    def _split_factual_vs_imperative(self, text: str) -> tuple[str, str]:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        factual: list[str] = []
        imperative: list[str] = []
        for s in sentences:
            if re.match(
                r"(?i)^\s*(ignore|forget|disregard|you\s+(must|will|should|shall|need|have\s+to)|do\s+not|never|always)\b",
                s.strip(),
            ):
                imperative.append(s)
            else:
                factual.append(s)
        return " ".join(factual), " ".join(imperative)
