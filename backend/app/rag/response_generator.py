from __future__ import annotations

import time
import uuid

from app.core.logging import get_logger
from app.rag.config import get_rag_settings
from app.rag.context_builder import ContextBuilder
from app.rag.llm import RAGLLMProvider
from app.rag.models import (
    RAGContext,
    RAGResponse,
    SearchIntent,
)
from app.rag.prompt_builder import PromptBuilder
from app.rag.query_processor import QueryProcessor
from app.rag.retrieval_engine import RetrievalEngine
from app.rag.retrieval_pipeline import RetrievalOutput, RetrievalPipeline

logger = get_logger("rag.response_generator")
settings = get_rag_settings()


class ResponseGenerator:
    def __init__(
        self,
        retrieval_engine: RetrievalEngine,
        llm_provider: RAGLLMProvider | None = None,
        query_processor: QueryProcessor | None = None,
        retrieval_pipeline: RetrievalPipeline | None = None,
        context_builder: ContextBuilder | None = None,
        prompt_builder: PromptBuilder | None = None,
    ):
        self._query_processor = query_processor or QueryProcessor()
        self._retrieval_pipeline = retrieval_pipeline or RetrievalPipeline(
            retrieval_engine
        )
        self._context_builder = context_builder or ContextBuilder()
        self._prompt_builder = prompt_builder or PromptBuilder()
        self._llm = llm_provider or RAGLLMProvider()

    async def answer(
        self,
        query: str,
        user_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        intent_override: SearchIntent | None = None,
        top_k: int | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        extra_instructions: str | None = None,
    ) -> RAGResponse:
        start = time.monotonic()
        processed = self._query_processor.process(
            query=query,
            user_id=user_id,
            project_id=project_id,
            top_k=top_k,
            intent_override=intent_override,
        )

        retrieval_output = await self._retrieval_pipeline.execute(processed)

        context = self._context_builder.build(
            evidence=retrieval_output.evidence,
            budget_tokens=max_tokens or settings.context_max_tokens,
        )

        system_prompt = self._prompt_builder.build_system_prompt(
            intent=processed.intent,
            extra_instructions=extra_instructions,
        )
        user_prompt = self._prompt_builder.build_user_prompt(
            query=processed.raw,
            context=context,
        )

        inference_start = time.monotonic()
        answer_text = await self._llm.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=temperature or settings.response_temperature,
            max_tokens=max_tokens or settings.response_max_tokens,
        )
        inference_duration = time.monotonic() - inference_start

        confidence = self._compute_overall_confidence(retrieval_output, context)
        total_duration = time.monotonic() - start

        logger.info(
            "response generated",
            extra={
                "query": query[:80],
                "intent": processed.intent.value,
                "evidence_count": len(retrieval_output.evidence),
                "context_tokens": context.total_tokens,
                "answer_length": len(answer_text),
                "confidence": round(confidence, 3),
                "total_duration": round(total_duration, 3),
            },
        )

        return RAGResponse(
            answer=answer_text,
            context=context,
            evidence=retrieval_output.evidence,
            confidence=confidence,
            model=settings.provider_model,
            query=processed,
            retrieval_stats={
                "total_candidates": retrieval_output.total_candidates,
                "semantic_results": retrieval_output.semantic_results,
                "keyword_results": retrieval_output.keyword_results,
                "duplicates_removed": retrieval_output.duplicates_removed,
                "retrieval_confidence": retrieval_output.confidence,
                "retrieval_duration": round(retrieval_output.duration_seconds, 3),
            },
            processing_metadata={
                "total_duration": round(total_duration, 3),
                "inference_duration": round(inference_duration, 3),
                "context_tokens": context.total_tokens,
                "context_truncated": context.truncated,
            },
        )

    def _compute_overall_confidence(
        self,
        retrieval_output: RetrievalOutput,
        context: RAGContext,
    ) -> float:
        if not retrieval_output.evidence:
            return 0.0
        retrieval_conf = retrieval_output.confidence
        coverage = min(
            1.0, len(context.chunks) / max(1, retrieval_output.total_candidates)
        )
        return round(0.7 * retrieval_conf + 0.3 * coverage, 4)
