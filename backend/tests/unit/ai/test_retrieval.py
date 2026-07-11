from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.retrieval.chunking import ChunkingStrategy, ChunkResult, TextChunker
from app.ai.retrieval.citation import Citation, CitationPreserver
from app.ai.retrieval.hybrid import HybridRetriever
from app.ai.retrieval.reranking import ReRanker, ReRankerResult
from app.ai.retrieval.retriever import BaseRetriever, RetrieverResult


class TestChunkResult:
    def test_defaults(self):
        cr = ChunkResult(chunks=["a", "b"])
        assert cr.chunks == ["a", "b"]
        assert cr.strategy == "fixed_size"
        assert cr.chunk_size == 512
        assert cr.overlap == 64
        assert cr.metadata == []

    def test_custom(self):
        cr = ChunkResult(
            chunks=["x"], strategy="recursive", chunk_size=256,
            overlap=32, metadata=[{"idx": "0"}],
        )
        assert cr.strategy == "recursive"
        assert cr.chunk_size == 256


class TestTextChunker:
    @pytest.fixture
    def chunker(self):
        return TextChunker()

    def test_fixed_size_basic(self, chunker):
        text = "Hello world! This is a test of the fixed size chunking strategy."
        result = chunker.chunk(text, strategy=ChunkingStrategy.FIXED_SIZE, chunk_size=20, overlap=5)
        assert len(result.chunks) > 1
        assert result.strategy == "fixed_size"
        assert result.chunk_size == 20
        assert isinstance(result.metadata, list)
        assert len(result.metadata) == len(result.chunks)

    def test_fixed_size_with_overlap(self, chunker):
        text = "abcdefghijklmnopqrstuvwxyz"
        result = chunker.chunk(text, strategy=ChunkingStrategy.FIXED_SIZE, chunk_size=10, overlap=3)
        assert result.chunks[0] == "abcdefghij"
        assert result.chunks[1] == "hijklmnopq"
        assert "hij" in result.chunks[1][:3]

    def test_fixed_size_single_chunk(self, chunker):
        text = "short text"
        result = chunker.chunk(text, strategy=ChunkingStrategy.FIXED_SIZE, chunk_size=100, overlap=10)
        assert result.chunks == ["short text"]
        assert len(result.metadata) == 1

    def test_fixed_size_empty_text(self, chunker):
        result = chunker.chunk("", strategy=ChunkingStrategy.FIXED_SIZE, chunk_size=100, overlap=10)
        assert result.chunks == []

    def test_fixed_size_single_word(self, chunker):
        result = chunker.chunk("hello", strategy=ChunkingStrategy.FIXED_SIZE, chunk_size=5, overlap=0)
        assert result.chunks == ["hello"]

    def test_fixed_size_text_shorter_than_chunk(self, chunker):
        result = chunker.chunk("small", strategy=ChunkingStrategy.FIXED_SIZE, chunk_size=1000, overlap=10)
        assert result.chunks == ["small"]

    def test_paragraph_basic(self, chunker):
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        result = chunker.chunk(text, strategy=ChunkingStrategy.PARAGRAPH, chunk_size=20, overlap=2)
        assert len(result.chunks) >= 3
        assert result.strategy == "paragraph"

    def test_paragraph_no_double_newline(self, chunker):
        text = "Single paragraph without separators."
        result = chunker.chunk(text, strategy=ChunkingStrategy.PARAGRAPH, chunk_size=100, overlap=10)
        assert result.chunks == ["Single paragraph without separators."]

    def test_paragraph_empty_text(self, chunker):
        result = chunker.chunk("", strategy=ChunkingStrategy.PARAGRAPH, chunk_size=100, overlap=10)
        assert result.chunks == []

    def test_paragraph_only_whitespace(self, chunker):
        result = chunker.chunk("  \n\n  \n\n", strategy=ChunkingStrategy.PARAGRAPH, chunk_size=100, overlap=10)
        assert result.chunks == []

    def test_recursive_basic(self, chunker):
        text = "First sentence. Second sentence. Third sentence."
        result = chunker.chunk(text, strategy=ChunkingStrategy.RECURSIVE, chunk_size=30, overlap=5)
        assert len(result.chunks) >= 1
        assert result.strategy == "recursive"
        assert result.overlap == 5

    def test_recursive_with_overlap(self, chunker):
        text = ". ".join(["sentence number " + str(i) for i in range(20)])
        result = chunker.chunk(text, strategy=ChunkingStrategy.RECURSIVE, chunk_size=50, overlap=10)
        assert len(result.chunks) >= 2

    def test_recursive_single_chunk(self, chunker):
        text = "Short text."
        result = chunker.chunk(text, strategy=ChunkingStrategy.RECURSIVE, chunk_size=500, overlap=10)
        assert result.chunks == ["Short text."]

    def test_recursive_empty_text(self, chunker):
        result = chunker.chunk("", strategy=ChunkingStrategy.RECURSIVE, chunk_size=100, overlap=10)
        assert result.chunks == [] or result.chunks == [""]

    def test_recursive_char_fallback(self, chunker):
        text = "a" * 200
        result = chunker.chunk(text, strategy=ChunkingStrategy.RECURSIVE, chunk_size=50, overlap=5)
        assert len(result.chunks) > 1
        first = result.chunks[0]
        second = result.chunks[1]
        assert first == "a" * 50
        assert second.startswith("a" * 5)

    def test_recursive_text_shorter_than_chunk(self, chunker):
        result = chunker.chunk("tiny", strategy=ChunkingStrategy.RECURSIVE, chunk_size=1000, overlap=10)
        assert result.chunks == ["tiny"]

    def test_semantic_uses_recursive(self, chunker):
        text = "Paragraph A.\n\nParagraph B."
        result = chunker.chunk(text, strategy=ChunkingStrategy.SEMANTIC, chunk_size=50, overlap=10)
        assert result.strategy == "recursive"

    def test_default_strategy(self, chunker):
        text = "Default strategy test."
        result = chunker.chunk(text)
        assert result.strategy == "recursive"


class TestBaseRetriever:
    def test_abstract_cannot_instantiate(self):
        with pytest.raises(TypeError):
            BaseRetriever()  # type: ignore[abstract]

    def test_concrete_implementation(self):
        class FakeRetriever(BaseRetriever):
            async def retrieve(self, query, limit=10, **kwargs):
                return [RetrieverResult(content="result", score=1.0, source="fake")]

        r = FakeRetriever()
        import asyncio
        results = asyncio.run(r.retrieve("test"))
        assert len(results) == 1
        assert results[0].content == "result"

    def test_retriever_result_defaults(self):
        r = RetrieverResult(content="c", score=0.5, source="s")
        assert r.metadata == {}

    def test_retriever_result_full(self):
        r = RetrieverResult(
            content="content", score=0.9, source="src",
            metadata={"id": "42", "type": "paper"},
        )
        assert r.metadata["id"] == "42"


class TestHybridRetriever:
    @pytest.fixture
    def retriever_a(self):
        m = AsyncMock(spec_set=BaseRetriever)
        m.retrieve = AsyncMock(
            return_value=[
                RetrieverResult(content="doc1", score=0.9, source="a", metadata={"id": "1"}),
                RetrieverResult(content="doc2", score=0.7, source="a", metadata={"id": "2"}),
            ]
        )
        return m

    @pytest.fixture
    def retriever_b(self):
        m = AsyncMock(spec_set=BaseRetriever)
        m.retrieve = AsyncMock(
            return_value=[
                RetrieverResult(content="doc3", score=0.8, source="b", metadata={"id": "3"}),
                RetrieverResult(content="doc4", score=0.6, source="b", metadata={"id": "4"}),
            ]
        )
        return m

    async def test_equal_weights(self, retriever_a, retriever_b):
        hybrid = HybridRetriever([(retriever_a, 1.0), (retriever_b, 1.0)])
        results = await hybrid.retrieve("query", limit=5)
        assert len(results) == 4
        assert results[0].content == "doc1"
        assert results[0].score == 0.9
        assert results[1].content == "doc3"
        assert results[1].score == 0.8

    async def test_weighted(self, retriever_a, retriever_b):
        hybrid = HybridRetriever([(retriever_a, 0.5), (retriever_b, 2.0)])
        results = await hybrid.retrieve("query", limit=5)
        assert len(results) == 4
        a_result = next(r for r in results if r.source == "a")
        b_result = next(r for r in results if r.source == "b")
        assert a_result.score == 0.45
        assert b_result.score == 1.6

    async def test_duplicate_across_retrievers(self):
        a = AsyncMock(spec_set=BaseRetriever)
        a.retrieve = AsyncMock(
            return_value=[
                RetrieverResult(content="same doc", score=0.9, source="src", metadata={"id": "dup"}),
            ]
        )
        b = AsyncMock(spec_set=BaseRetriever)
        b.retrieve = AsyncMock(
            return_value=[
                RetrieverResult(content="same doc", score=0.8, source="src", metadata={"id": "dup"}),
            ]
        )
        hybrid = HybridRetriever([(a, 1.0), (b, 1.0)])
        results = await hybrid.retrieve("query", limit=5)
        assert len(results) == 1

    async def test_empty_results(self):
        a = AsyncMock(spec_set=BaseRetriever)
        a.retrieve = AsyncMock(return_value=[])
        b = AsyncMock(spec_set=BaseRetriever)
        b.retrieve = AsyncMock(return_value=[])
        hybrid = HybridRetriever([(a, 1.0), (b, 1.0)])
        results = await hybrid.retrieve("query")
        assert results == []

    async def test_limit_respected(self, retriever_a, retriever_b):
        hybrid = HybridRetriever([(retriever_a, 1.0), (retriever_b, 1.0)])
        results = await hybrid.retrieve("query", limit=2)
        assert len(results) == 2

    async def test_retrieve_with_scores(self, retriever_a, retriever_b):
        hybrid = HybridRetriever([(retriever_a, 1.0), (retriever_b, 1.0)])
        results = await hybrid.retrieve_with_scores("query", limit=5)
        assert len(results) == 4
        item, scores = results[0]
        assert isinstance(item, RetrieverResult)
        assert isinstance(scores, list)
        assert len(scores[0]) == 2

    async def test_kwargs_passthrough(self):
        a = AsyncMock(spec_set=BaseRetriever)
        a.retrieve = AsyncMock(return_value=[])
        hybrid = HybridRetriever([(a, 1.0)])
        await hybrid.retrieve("query", limit=10, custom_param="val")
        a.retrieve.assert_awaited_once_with("query", limit=20, custom_param="val")


class TestReRanker:
    @pytest.fixture
    def results(self):
        return [
            RetrieverResult(content="doc C", score=0.3, source="s", metadata={"id": "3"}),
            RetrieverResult(content="doc A", score=0.9, source="s", metadata={"id": "1"}),
            RetrieverResult(content="doc B", score=0.6, source="s", metadata={"id": "2"}),
        ]

    @pytest.fixture
    def reranker(self):
        return ReRanker()

    async def test_empty_results(self, reranker):
        result = await reranker.re_rank("query", [])
        assert result.results == []
        assert result.scores == []

    async def test_fewer_results_than_top_k(self, reranker, results):
        result = await reranker.re_rank("query", results, top_k=10)
        assert len(result.results) == 3
        assert result.results[0].metadata["id"] == "3"
        assert result.results[1].metadata["id"] == "1"
        assert result.results[2].metadata["id"] == "2"

    async def test_truncation(self, reranker):
        many = [
            RetrieverResult(content=f"doc {i}", score=float(100 - i), source="s")
            for i in range(10)
        ]
        result = await reranker.re_rank("query", many, top_k=3)
        assert len(result.results) == 3
        assert result.results[0].score == 100.0

    async def test_uniform_scores(self, reranker):
        uniform = [
            RetrieverResult(content="a", score=0.5, source="s"),
            RetrieverResult(content="b", score=0.5, source="s"),
            RetrieverResult(content="c", score=0.5, source="s"),
        ]
        result = await reranker.re_rank("query", uniform, top_k=2)
        assert len(result.results) == 2
        assert result.scores == [0.5, 0.5]

    async def test_re_ranker_result_dataclass(self, reranker, results):
        result = await reranker.re_rank("query", results, top_k=2)
        assert isinstance(result, ReRankerResult)
        assert result.scores == [0.9, 0.6]

    async def test_score_pairs_default(self, reranker):
        pairs = [("q1", "d1"), ("q2", "d2")]
        scores = await reranker.score_pairs(pairs)
        assert scores == [0.0, 0.0]

    async def test_score_pairs_with_model(self):
        reranker = ReRanker()
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.95, 0.87]
        reranker._model = mock_model
        pairs = [("query", "doc1"), ("query", "doc2")]
        scores = await reranker.score_pairs(pairs)
        assert scores == [0.95, 0.87]
        mock_model.predict.assert_called_once()

    async def test_re_rank_with_model(self):
        reranker = ReRanker()
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.1, 0.9, 0.5]
        reranker._model = mock_model
        results = [
            RetrieverResult(content="bad", score=0.5, source="s"),
            RetrieverResult(content="good", score=0.5, source="s"),
            RetrieverResult(content="mid", score=0.5, source="s"),
        ]
        result = await reranker.re_rank("query", results, top_k=2)
        assert result.results[0].content == "good"
        assert result.results[1].content == "mid"
        assert result.scores == [0.9, 0.5]

    async def test_re_rank_model_exception_falls_back(self, reranker, results):
        mock_model = MagicMock()
        mock_model.predict.side_effect = ValueError("model error")
        reranker._model = mock_model
        result = await reranker.re_rank("query", results, top_k=2)
        assert len(result.results) == 2
        assert result.results[0].metadata["id"] == "1"


class TestCitationPreserver:
    @pytest.fixture
    def preserver(self):
        return CitationPreserver()

    def test_extract_citations_basic(self, preserver):
        text = "According to [@Smith2024], the results show..."
        citations = preserver.extract_citations(text)
        assert len(citations) == 1
        assert citations[0].source_id == "Smith2024"
        assert citations[0].text == "[@Smith2024]"
        assert citations[0].start_pos == 13
        assert citations[0].end_pos == 25

    def test_extract_citations_multiple(self, preserver):
        text = "[@One] and [@Two] and [@Three] are citations."
        citations = preserver.extract_citations(text)
        assert len(citations) == 3
        assert [c.source_id for c in citations] == ["One", "Two", "Three"]

    def test_extract_citations_empty_text(self, preserver):
        citations = preserver.extract_citations("")
        assert citations == []

    def test_extract_citations_no_citations(self, preserver):
        citations = preserver.extract_citations("Plain text without any citations.")
        assert citations == []

    def test_extract_citations_invalid_format(self, preserver):
        text = "Not a citation [invalid] and [@]"
        citations = preserver.extract_citations(text)
        assert len(citations) == 0

    def test_extract_citations_with_underscores(self, preserver):
        text = "See [@Author_2024]."
        citations = preserver.extract_citations(text)
        assert len(citations) == 1
        assert citations[0].source_id == "Author_2024"

    def test_preserve_citations_adds_missing(self, preserver):
        text = "This is some text."
        cit = Citation(source_id="NewRef", source_title="Title", text="[@NewRef]")
        result = preserver.preserve_citations(text, [cit])
        assert "[@NewRef]" in result
        assert result.startswith("This is some")

    def test_preserve_citations_existing_not_duplicated(self, preserver):
        text = "See [@Existing] for details."
        cit = Citation(source_id="Existing", source_title="", text="[@Existing]")
        result = preserver.preserve_citations(text, [cit])
        assert result == text

    def test_preserve_citations_multiple(self, preserver):
        text = "Content."
        cits = [
            Citation(source_id="A", source_title="", text="[@A]"),
            Citation(source_id="B", source_title="", text="[@B]"),
        ]
        result = preserver.preserve_citations(text, cits)
        assert "[@A]" in result
        assert "[@B]" in result

    def test_verify_citation_format_valid(self, preserver):
        valid = "[@ValidRef]"
        cits = preserver.extract_citations(valid)
        assert len(cits) == 1
        assert cits[0].source_id == "ValidRef"

    def test_verify_citation_format_missing_bracket(self, preserver):
        invalid = "[@NoClose"
        cits = preserver.extract_citations(invalid)
        assert len(cits) == 0

    def test_verify_citation_format_wrong_prefix(self, preserver):
        invalid = "[#NotAt]"
        cits = preserver.extract_citations(invalid)
        assert len(cits) == 0

    def test_add_and_get_citation_context(self, preserver):
        cit = Citation(
            source_id="Ref1", source_title="Paper Title",
            text="[@Ref1]", start_pos=10, end_pos=17,
        )
        preserver.add_citation(cit)
        text = "Prefix [@Ref1] suffix"
        contexts = preserver.get_citation_context(text, max_context=5)
        assert len(contexts) == 1
        assert contexts[0]["citation_id"] == "Ref1"
        assert contexts[0]["source"] == "Paper Title"
        assert "Ref1" in contexts[0]["context"]

    def test_clear_citations(self, preserver):
        preserver.add_citation(Citation(source_id="X", source_title="", text=""))
        assert len(preserver._citations) == 1
        preserver.clear()
        assert preserver._citations == []

    def test_citation_dataclass_defaults(self):
        c = Citation(source_id="s1", source_title="t1", text="[@s1]")
        assert c.start_pos == 0
        assert c.end_pos == 0
        assert c.metadata == {}
