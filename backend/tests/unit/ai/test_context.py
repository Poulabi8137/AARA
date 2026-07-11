from __future__ import annotations

from app.ai.context.assembler import ContextAssembler, ContextSection
from app.ai.context.budgeting import TokenBudget
from app.ai.context.compression import ContextCompressor
from app.ai.context.deduplication import SourceDeduplicator
from app.ai.context.validation import ContextValidator


class TestContextSection:
    def test_default_values(self):
        section = ContextSection(name="test", content="hello")
        assert section.source == ""
        assert section.priority == 0
        assert section.token_count == 0
        assert section.metadata == {}

    def test_with_all_fields(self):
        section = ContextSection(
            name="test",
            content="hello",
            source="doc1",
            priority=10,
            token_count=5,
            metadata={"key": "val"},
        )
        assert section.source == "doc1"
        assert section.priority == 10
        assert section.token_count == 5
        assert section.metadata == {"key": "val"}


class TestContextAssembler:
    async def test_assemble_prioritizes_by_priority_desc(self):
        assembler = ContextAssembler(max_tokens=10000)
        sections = [
            ContextSection(name="low", content="low priority", priority=1),
            ContextSection(name="high", content="high priority", priority=10),
            ContextSection(name="mid", content="mid priority", priority=5),
        ]
        result = await assembler.assemble(sections)
        high_pos = result.index("high priority")
        mid_pos = result.index("mid priority")
        low_pos = result.index("low priority")
        assert high_pos < mid_pos < low_pos

    async def test_assemble_with_source_labels(self):
        assembler = ContextAssembler(max_tokens=10000)
        sections = [
            ContextSection(name="s1", content="content1", source="src1", priority=1),
            ContextSection(name="s2", content="content2", priority=2),
        ]
        result = await assembler.assemble(sections)
        assert "[Source: src1]" in result
        assert "content1" in result
        assert "content2" in result

    async def test_assemble_empty_items(self):
        assembler = ContextAssembler(max_tokens=10000)
        result = await assembler.assemble([])
        assert result == ""

    async def test_assemble_single_item(self):
        assembler = ContextAssembler(max_tokens=10000)
        sections = [ContextSection(name="s1", content="only one")]
        result = await assembler.assemble(sections)
        assert result == "only one"

    async def test_assemble_respects_max_tokens(self):
        assembler = ContextAssembler(max_tokens=40)
        long_content = "A" * 200
        short_content = "B" * 10
        sections = [
            ContextSection(name="long", content=long_content, priority=1),
            ContextSection(name="short", content=short_content, priority=2),
        ]
        result = await assembler.assemble(sections)
        assert len(result) < len(long_content) + len(short_content)

    async def test_assemble_deduplicates(self):
        assembler = ContextAssembler(max_tokens=10000)
        sections = [
            ContextSection(name="a", content="duplicate content", source="src1", priority=1),
            ContextSection(name="b", content="duplicate content", source="src1", priority=2),
        ]
        result = await assembler.assemble(sections)
        assert result.count("duplicate content") == 1

    async def test_assemble_preserves_unique_content(self):
        assembler = ContextAssembler(max_tokens=10000)
        sections = [
            ContextSection(name="a", content="unique a", source="src1", priority=1),
            ContextSection(name="b", content="unique b", source="src2", priority=2),
        ]
        result = await assembler.assemble(sections)
        assert "unique a" in result
        assert "unique b" in result

    async def test_assemble_with_citations(self):
        assembler = ContextAssembler(max_tokens=10000)
        sections = [ContextSection(name="s1", content="body", priority=1)]
        citations = [{"id": "cit1", "title": "Source Document"}]
        result = await assembler.assemble_with_citations(sections, citations)
        assert "[@cit1] Source Document" in result
        assert "References:" in result

    async def test_assemble_with_citations_empty(self):
        assembler = ContextAssembler(max_tokens=10000)
        sections = [ContextSection(name="s1", content="body", priority=1)]
        result = await assembler.assemble_with_citations(sections, [])
        assert "References:" not in result

    async def test_estimate_tokens(self):
        assembler = ContextAssembler(max_tokens=10000)
        assert assembler._estimate_tokens("hello world") == 2
        assert assembler._estimate_tokens("") == 0
        assert assembler._estimate_tokens("A" * 40) == 10


class TestTokenBudget:
    def test_default_max_tokens(self):
        budget = TokenBudget()
        assert budget.max_tokens == 8000

    def test_reserve_output_reduces_budget(self):
        budget = TokenBudget(max_tokens=8000, reserve_output=2048)
        assert budget._budget == 5952

    def test_no_reserve(self):
        budget = TokenBudget(max_tokens=8000, reserve_output=0)
        assert budget._budget == 8000

    def test_allocate_all_fit(self):
        budget = TokenBudget(max_tokens=100, reserve_output=0)
        sections = [
            ContextSection(name="a", content="A" * 40, priority=1),
            ContextSection(name="b", content="B" * 40, priority=2),
        ]
        for s in sections:
            s.token_count = len(s.content) // 4
        result = budget.allocate(sections)
        assert len(result.allocated) == 2
        assert result.truncated is False
        assert result.remaining >= 0

    def test_allocate_truncates_when_over_budget(self):
        budget = TokenBudget(max_tokens=30, reserve_output=0)
        sections = [
            ContextSection(name="a", content="A" * 100, priority=1),
            ContextSection(name="b", content="B" * 100, priority=2),
        ]
        for s in sections:
            s.token_count = len(s.content) // 4
        result = budget.allocate(sections)
        assert result.truncated is True
        assert len(result.allocated) <= 2

    def test_allocate_remaining_correct(self):
        budget = TokenBudget(max_tokens=100, reserve_output=0)
        sections = [
            ContextSection(name="a", content="A" * 80, priority=1),
        ]
        for s in sections:
            s.token_count = len(s.content) // 4
        result = budget.allocate(sections)
        assert result.total_tokens == 20
        assert result.remaining == 80

    def test_allocate_truncates_partial_section(self):
        budget = TokenBudget(max_tokens=200, reserve_output=0)
        sections = [
            ContextSection(name="a", content="A" * 400, token_count=100, priority=1),
            ContextSection(name="b", content="B" * 800, token_count=200, priority=2),
        ]
        result = budget.allocate(sections)
        assert result.truncated is True
        assert result.total_tokens == 200
        assert len(result.allocated) == 2

    def test_can_fit_within_budget(self):
        budget = TokenBudget(max_tokens=100, reserve_output=0)
        assert budget.can_fit("hello", current_used=10) is True

    def test_cannot_fit_exceeds_budget(self):
        budget = TokenBudget(max_tokens=100, reserve_output=0)
        assert budget.can_fit("A" * 500, current_used=90) is False

    def test_allocate_empty_list(self):
        budget = TokenBudget(max_tokens=100, reserve_output=0)
        result = budget.allocate([])
        assert result.allocated == []
        assert result.truncated is False

    def test_allocate_uses_token_count_when_provided(self):
        budget = TokenBudget(max_tokens=100, reserve_output=0)
        section = ContextSection(name="a", content="A" * 200, token_count=5, priority=1)
        result = budget.allocate([section])
        assert result.total_tokens == 5

    def test_allocate_small_remaining_skips_truncation(self):
        budget = TokenBudget(max_tokens=14, reserve_output=0)
        section = ContextSection(name="a", content="A" * 80, token_count=20, priority=1)
        result = budget.allocate([section])
        assert result.total_tokens == 0
        assert result.remaining == 14


class TestSourceDeduplicator:
    def test_dedup_removes_duplicates_by_source_and_content(self):
        dedup = SourceDeduplicator()
        sections = [
            ContextSection(name="a", content="same content", source="src1", priority=1),
            ContextSection(name="b", content="same content", source="src1", priority=2),
        ]
        result = dedup.dedup(sections)
        assert len(result) == 1

    def test_dedup_preserves_different_sources(self):
        dedup = SourceDeduplicator()
        sections = [
            ContextSection(name="a", content="same content", source="src1", priority=1),
            ContextSection(name="b", content="same content", source="src2", priority=2),
        ]
        result = dedup.dedup(sections)
        assert len(result) == 2

    def test_dedup_preserves_different_content(self):
        dedup = SourceDeduplicator()
        sections = [
            ContextSection(name="a", content="content a", source="src1", priority=1),
            ContextSection(name="b", content="content b", source="src1", priority=2),
        ]
        result = dedup.dedup(sections)
        assert len(result) == 2

    def test_dedup_empty_list(self):
        dedup = SourceDeduplicator()
        result = dedup.dedup([])
        assert result == []

    def test_dedup_single_item(self):
        dedup = SourceDeduplicator()
        sections = [ContextSection(name="a", content="only", source="src1", priority=1)]
        result = dedup.dedup(sections)
        assert len(result) == 1

    def test_dedup_preserves_first_occurrence(self):
        dedup = SourceDeduplicator()
        sections = [
            ContextSection(name="first", content="dup", source="src1", priority=10),
            ContextSection(name="second", content="dup", source="src1", priority=20),
        ]
        result = dedup.dedup(sections)
        assert result[0].name == "first"

    def test_dedup_by_source(self):
        dedup = SourceDeduplicator()
        sections = [
            ContextSection(name="a", content="c1", source="src1", priority=1),
            ContextSection(name="b", content="c2", source="src1", priority=2),
            ContextSection(name="c", content="c3", source="src2", priority=3),
        ]
        by_source = dedup.dedup_by_source(sections)
        assert len(by_source["src1"]) == 2
        assert len(by_source["src2"]) == 1

    def test_dedup_by_source_empty(self):
        dedup = SourceDeduplicator()
        assert dedup.dedup_by_source([]) == {}

    def test_make_key_consistency(self):
        dedup = SourceDeduplicator()
        s1 = ContextSection(name="a", content="hello", source="src", priority=1)
        s2 = ContextSection(name="b", content="hello", source="src", priority=2)
        k1 = dedup._make_key(s1)
        k2 = dedup._make_key(s2)
        assert k1 == k2


class TestContextCompressor:
    async def test_compress_empty_list(self):
        compressor = ContextCompressor()
        result = await compressor.compress([])
        assert result == []

    async def test_compress_empty_string(self):
        compressor = ContextCompressor()
        result = await compressor.compress([""])
        assert result == [""]

    async def test_compress_short_text_unchanged(self):
        compressor = ContextCompressor()
        text = "Short text."
        result = await compressor.compress([text])
        assert result[0] == text

    async def test_compress_long_text(self):
        compressor = ContextCompressor()
        sentences = ". ".join(["Sentence " + str(i) for i in range(20)])
        result = await compressor.compress([sentences], target_ratio=0.5)
        assert len(result[0]) < len(sentences)

    async def test_compress_multiple_texts(self):
        compressor = ContextCompressor()
        texts = [
            "Short.",
            "A bit longer text here for testing purposes.",
            "Long. " * 50,
        ]
        result = await compressor.compress(texts)
        assert len(result) == 3

    async def test_compress_target_ratio_one(self):
        compressor = ContextCompressor()
        text = "Hello world. This is a test. Multiple sentences here."
        result = await compressor.compress([text], target_ratio=1.0)
        assert result[0] == text

    async def test_compress_minimum_target_length(self):
        compressor = ContextCompressor()
        text = "A" * 500
        result = await compressor.compress([text], target_ratio=0.0)
        assert len(result[0]) >= 100

    async def test_compress_text_sentence_boundary(self):
        compressor = ContextCompressor()
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        result = await compressor.compress([text], target_ratio=0.5)
        assert "First sentence" in result[0]
        assert result[0].endswith(".")

    async def test_summarize_to_tokens_short_text(self):
        compressor = ContextCompressor()
        text = "Hello world"
        result = await compressor.summarize_to_tokens(text, max_tokens=100)
        assert result == text

    async def test_summarize_to_tokens_long_text(self):
        compressor = ContextCompressor()
        text = "A" * 200
        result = await compressor.summarize_to_tokens(text, max_tokens=10)
        assert len(result) == 40

    async def test_compress_handles_empty_sentences(self):
        compressor = ContextCompressor()
        text = ". ".join([""] * 5)
        result = await compressor.compress([text])
        assert result[0] != ""

    async def test_compress_preserves_end_period(self):
        compressor = ContextCompressor()
        text = "First. Second. Third."
        result = await compressor.compress([text], target_ratio=0.5)
        assert result[0].endswith(".")

    async def test_compress_question_exclamation_handling(self):
        compressor = ContextCompressor()
        text = "First! Second? Third. Fourth."
        result = await compressor.compress([text], target_ratio=0.5)
        assert "First" in result[0]


class TestContextValidator:
    def test_validate_valid_section(self):
        validator = ContextValidator()
        section = ContextSection(name="test", content="valid content", priority=1)
        result = validator.validate_section(section)
        assert result.is_valid is True
        assert result.errors == []

    def test_validate_empty_content(self):
        validator = ContextValidator()
        section = ContextSection(name="empty", content="", priority=1)
        result = validator.validate_section(section)
        assert result.is_valid is False
        assert any("empty content" in e for e in result.errors)

    def test_validate_oversized_section(self):
        validator = ContextValidator()
        section = ContextSection(
            name="big", content="X" * 200_000, priority=1
        )
        result = validator.validate_section(section)
        assert result.is_valid is False
        assert any("exceeds max size" in e for e in result.errors)

    def test_validate_token_count_warning(self):
        validator = ContextValidator()
        section = ContextSection(
            name="mismatch",
            content="short content",
            token_count=1000,
            priority=1,
        )
        result = validator.validate_section(section)
        assert result.is_valid is True
        assert any("token count may be inaccurate" in w for w in result.warnings)

    def test_validate_token_count_accurate_no_warning(self):
        validator = ContextValidator()
        content = "Hello world, this is a test."
        section = ContextSection(
            name="acc",
            content=content,
            token_count=len(content) // 4,
            priority=1,
        )
        result = validator.validate_section(section)
        assert result.is_valid is True
        assert not any("inaccurate" in w for w in result.warnings)

    def test_validate_context_multiple_sections(self):
        validator = ContextValidator()
        sections = [
            ContextSection(name="good", content="valid", priority=1),
            ContextSection(name="empty", content="", priority=2),
        ]
        result = validator.validate_context(sections)
        assert result.is_valid is False
        assert any("empty content" in e for e in result.errors)

    def test_validate_context_total_size_warning(self):
        validator = ContextValidator()
        sections = [
            ContextSection(name="big1", content="X" * 600_000, priority=1),
            ContextSection(name="big2", content="Y" * 600_000, priority=2),
        ]
        result = validator.validate_context(sections)
        assert any("exceeds recommended limit" in w for w in result.warnings)

    def test_validate_context_empty(self):
        validator = ContextValidator()
        result = validator.validate_context([])
        assert result.is_valid is True
        assert result.errors == []

    def test_validate_context_single_section(self):
        validator = ContextValidator()
        sections = [ContextSection(name="only", content="just one", priority=1)]
        result = validator.validate_context(sections)
        assert result.is_valid is True
