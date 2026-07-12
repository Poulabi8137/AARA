from __future__ import annotations

import re
import uuid

from app.core.logging import get_logger
from app.planner.models import ResearchGoal, TaskComplexity
from app.rag.models import SearchIntent
from app.rag.query_processor import QueryProcessor

logger = get_logger("planner.goal_analyzer")

_COMPLEXITY_PATTERNS: dict[TaskComplexity, list[re.Pattern]] = {
    TaskComplexity.SIMPLE: [
        re.compile(r"\b(what|who|when|where)\b", re.IGNORECASE),
        re.compile(r"^\w{3,30}\?$", re.IGNORECASE),
    ],
    TaskComplexity.MODERATE: [
        re.compile(
            r"\b(compare|contrast|difference|similarity|explain|describe|analyze)\b",
            re.IGNORECASE,
        ),
        re.compile(r"\b(how does|how is|why does)\b", re.IGNORECASE),
        re.compile(r"\bimpact|effect|influence|relationship\b", re.IGNORECASE),
    ],
    TaskComplexity.COMPLEX: [
        re.compile(
            r"\b(design|implement|develop|create|build|experiment|investigate)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(framework|methodology|pipeline|system|architecture)\b", re.IGNORECASE
        ),
        re.compile(
            r"\b(multi-step|multistep|end-to-end|comprehensive)\b", re.IGNORECASE
        ),
    ],
}

_AMBIGUITY_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(something|thing|stuff|some|any|various)\b", re.IGNORECASE),
    re.compile(r"\b(good|better|best|effective|efficient)\b", re.IGNORECASE),
    re.compile(r"\b(maybe|perhaps|possibly|might|could)\b", re.IGNORECASE),
    re.compile(r"\b(recent|latest|new|modern|current)\b", re.IGNORECASE),
]

_OUTPUT_PATTERNS: dict[str, re.Pattern] = {
    "summary": re.compile(
        r"\b(summarize|summary|overview|brief|abstract)\b", re.IGNORECASE
    ),
    "comparison": re.compile(
        r"\b(compare|contrast|difference|similarity|vs\.?|versus)\b", re.IGNORECASE
    ),
    "analysis": re.compile(
        r"\b(analyze|analysis|examine|evaluate|assess)\b", re.IGNORECASE
    ),
    "recommendation": re.compile(
        r"\b(recommend|suggest|propose|advise)\b", re.IGNORECASE
    ),
    "explanation": re.compile(
        r"\b(explain|describe|elaborate|clarify)\b", re.IGNORECASE
    ),
    "methodology": re.compile(
        r"\b(method|approach|technique|procedure|protocol)\b", re.IGNORECASE
    ),
    "literature_review": re.compile(
        r"\b(literature|survey|review|related work|state of the art)\b", re.IGNORECASE
    ),
}


class GoalAnalyzer:
    def __init__(self, query_processor: QueryProcessor | None = None):
        self._qp = query_processor or QueryProcessor()

    def analyze(
        self,
        query: str,
        user_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
    ) -> tuple[ResearchGoal, SearchIntent]:
        pq = self._qp.process(
            query=query,
            user_id=user_id,
            project_id=project_id,
        )

        complexity = self._detect_complexity(pq.normalized, pq.intent)
        ambiguity = self._detect_ambiguity(pq.normalized)
        outputs = self._detect_outputs(pq.normalized)
        difficulty = self._estimate_difficulty(complexity, ambiguity, outputs)
        missing = self._detect_missing_info(pq.normalized, pq.keywords)

        goal = ResearchGoal(
            objective=pq.rewritten or pq.normalized,
            intent=pq.intent,
            complexity=complexity,
            required_outputs=outputs,
            estimated_difficulty=difficulty,
            ambiguity_score=ambiguity,
            missing_information=missing,
        )

        logger.info(
            "goal analysis complete",
            extra={
                "intent": pq.intent.value,
                "complexity": complexity.value,
                "ambiguity": round(ambiguity, 2),
                "difficulty": round(difficulty, 2),
                "outputs": outputs,
            },
        )

        return goal, pq.intent

    def _detect_complexity(
        self, normalized: str, intent: SearchIntent
    ) -> TaskComplexity:
        if intent in (SearchIntent.COMPARATIVE, SearchIntent.METHODOLOGICAL):
            return TaskComplexity.MODERATE
        if intent == SearchIntent.CRITICAL:
            return TaskComplexity.MODERATE
        if intent == SearchIntent.SUMMARIZATION:
            return TaskComplexity.SIMPLE

        for complexity, patterns in _COMPLEXITY_PATTERNS.items():
            for pattern in patterns:
                if pattern.search(normalized):
                    return complexity

        word_count = len(normalized.split())
        if word_count > 30:
            return TaskComplexity.COMPLEX
        if word_count > 15:
            return TaskComplexity.MODERATE
        return TaskComplexity.SIMPLE

    def _detect_ambiguity(self, normalized: str) -> float:
        matches = sum(1 for p in _AMBIGUITY_PATTERNS if p.search(normalized))
        return min(1.0, matches * 0.15)

    def _detect_outputs(self, normalized: str) -> list[str]:
        outputs: list[str] = []
        seen: set[str] = set()
        for name, pattern in _OUTPUT_PATTERNS.items():
            if pattern.search(normalized) and name not in seen:
                seen.add(name)
                outputs.append(name)
        if not outputs:
            outputs.append("summary")
        return outputs

    def _estimate_difficulty(
        self,
        complexity: TaskComplexity,
        ambiguity: float,
        outputs: list[str],
    ) -> float:
        base = {
            TaskComplexity.SIMPLE: 0.2,
            TaskComplexity.MODERATE: 0.5,
            TaskComplexity.COMPLEX: 0.8,
        }[complexity]
        return round(min(1.0, base + ambiguity * 0.2 + len(outputs) * 0.05), 2)

    def _detect_missing_info(self, normalized: str, keywords: list[str]) -> list[str]:
        missing: list[str] = []
        if not keywords:
            missing.append("No specific research terms found")
        date_range = re.search(r"\b(19|20)\d{2}\b", normalized)
        if not date_range:
            date_clues = re.search(r"\b(recent|latest|new|current)\b", normalized)
            if date_clues:
                missing.append("Date range not specified; using default")
        return missing
