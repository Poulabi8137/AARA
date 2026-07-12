from __future__ import annotations

import re
import time

from app.core.logging import get_logger
from app.methodology.config import get_methodology_settings
from app.methodology.models import DatasetRecommendation
from app.rag.llm import RAGLLMProvider
from app.analysis.models import AnalysisResult

logger = get_logger("methodology.dataset_recommender")
settings = get_methodology_settings()

_DATASET_SYSTEM: str = (
    "You are a dataset recommendation assistant. "
    "Based on the research analysis, recommend suitable datasets.\n\n"
    "For each dataset provide:\n"
    "- Dataset name\n"
    "- Domain relevance (0.0-1.0)\n"
    "- Size category (small|medium|large|very_large)\n"
    "- Quality (0.0-1.0)\n"
    "- Licensing (open|restricted|commercial|unknown)\n"
    "- Availability (public|upon_request|restricted|unknown)\n"
    "- Maturity (emerging|established|classic)\n"
    "- Confidence (0.0-1.0)\n"
    "- Rationale\n\n"
    "Format:\n"
    "Dataset: <name>\n"
    "Domain Relevance: 0.X\n"
    "Size: <category>\n"
    "Quality: 0.X\n"
    "Licensing: <type>\n"
    "Availability: <type>\n"
    "Maturity: <type>\n"
    "Confidence: 0.X\n"
    "Rationale: <explanation>"
)

_DATASET_USER: str = (
    "Research Query: {query}\n"
    "Analysis Summary:\n{analysis_summary}\n\n"
    "Recommend up to {max_datasets} suitable datasets."
)


class DatasetRecommender:
    def __init__(self, llm: RAGLLMProvider | None = None):
        self._llm = llm

    async def recommend(
        self,
        query: str,
        analysis_result: AnalysisResult,
    ) -> list[DatasetRecommendation]:
        start = time.monotonic()
        rule_based = self._rule_based(analysis_result)

        llm_recs: list[DatasetRecommendation] = []
        if self._llm and settings.enable_llm:
            llm_recs = await self._llm_assisted(query, analysis_result)

        seen: set[str] = set()
        merged: list[DatasetRecommendation] = []
        for r in rule_based + llm_recs:
            key = r.dataset_name.lower().strip()
            if key and key not in seen:
                seen.add(key)
                merged.append(r)

        logger.info(
            "dataset recommendation complete",
            extra={
                "rule_based": len(rule_based),
                "llm_assisted": len(llm_recs),
                "merged": len(merged),
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )
        return merged[: settings.max_datasets]

    def _rule_based(self, ar: AnalysisResult) -> list[DatasetRecommendation]:
        datasets: list[DatasetRecommendation] = []
        seen_names: set[str] = set()

        for section in ar.sections:
            matches = re.findall(
                r"\b([A-Z][A-Za-z0-9-]+(?:-[A-Za-z0-9]+)?(?:Dataset|Bench|Set|Collection))\b",
                section.content,
            )
            for name in matches:
                if name not in seen_names:
                    seen_names.add(name)
                    datasets.append(
                        DatasetRecommendation(
                            dataset_name=name,
                            confidence=0.4,
                            rationale="Mentioned in analysis",
                        )
                    )

        for consensus in ar.consensus:
            for src in consensus.supporting_sources:
                if "dataset" in src.lower() or "data" in src.lower():
                    name = src.replace("[", "").replace("]", "").strip()
                    if name and name not in seen_names:
                        seen_names.add(name)
                        datasets.append(
                            DatasetRecommendation(
                                dataset_name=name,
                                confidence=0.5,
                                rationale="Referenced in consensus findings",
                            )
                        )

        return datasets

    async def _llm_assisted(
        self, query: str, ar: AnalysisResult
    ) -> list[DatasetRecommendation]:
        try:
            summary = self._summarize_analysis(ar)
            content = await self._llm.generate(
                prompt=_DATASET_USER.format(
                    query=query,
                    analysis_summary=summary,
                    max_datasets=settings.max_datasets,
                ),
                system_prompt=_DATASET_SYSTEM,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
            )
            return self._parse_datasets(content)
        except Exception as exc:
            logger.warning(
                "LLM dataset recommendation failed", extra={"error": str(exc)}
            )
            return []

    def _summarize_analysis(self, ar: AnalysisResult) -> str:
        parts = [
            f"Consensus: {len(ar.consensus)} findings",
            f"Contradictions: {len(ar.contradictions)}",
            f"Trends: {len(ar.trends)}",
            f"Limitations: {len(ar.limitations)}",
            f"Confidence: {ar.confidence.overall:.2f}"
            if hasattr(ar.confidence, "overall")
            else "",
        ]
        return "\n".join(p for p in parts if p)

    def _parse_datasets(self, content: str) -> list[DatasetRecommendation]:
        results: list[DatasetRecommendation] = []
        blocks = re.split(r"\n\s*\n", content)
        current: dict = {}
        for block in blocks:
            block = block.strip()
            low = block.lower()
            if low.startswith("dataset:"):
                if current.get("dataset"):
                    results.append(self._build_dataset(current))
                current = {"dataset": block.split(":", 1)[1].strip()}
            elif low.startswith("domain relevance:"):
                current["relevance"] = self._parse_float(block)
            elif low.startswith("size:"):
                current["size"] = block.split(":", 1)[1].strip().lower()
            elif low.startswith("quality:"):
                current["quality"] = self._parse_float(block)
            elif low.startswith("licensing:"):
                current["licensing"] = block.split(":", 1)[1].strip().lower()
            elif low.startswith("availability:"):
                current["availability"] = block.split(":", 1)[1].strip().lower()
            elif low.startswith("maturity:"):
                current["maturity"] = block.split(":", 1)[1].strip().lower()
            elif low.startswith("confidence:"):
                current["confidence"] = self._parse_float(block)
            elif low.startswith("rationale:"):
                current["rationale"] = block.split(":", 1)[1].strip()
        if current.get("dataset"):
            results.append(self._build_dataset(current))
        return results

    def _parse_float(self, block: str) -> float:
        try:
            return float(block.split(":", 1)[1].strip())
        except (ValueError, IndexError, TypeError):
            return 0.5

    def _build_dataset(self, data: dict) -> DatasetRecommendation:
        return DatasetRecommendation(
            dataset_name=data.get("dataset", ""),
            domain_relevance=data.get("relevance", 0.5),
            size_category=data.get("size", "medium"),
            quality=data.get("quality", 0.5),
            licensing=data.get("licensing", "unknown"),
            availability=data.get("availability", "unknown"),
            maturity=data.get("maturity", "established"),
            confidence=data.get("confidence", 0.5),
            rationale=data.get("rationale", ""),
        )
