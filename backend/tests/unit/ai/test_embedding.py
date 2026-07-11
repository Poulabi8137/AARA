from __future__ import annotations

import hashlib
from abc import ABC

import pytest

from app.ai.embedding.cache import EmbeddingCache
from app.ai.embedding.interface import (
    BaseEmbedder,
    EmbeddingConfig,
    EmbeddingResult,
)
from app.ai.embedding.validation import (
    DimensionValidationResult,
    DimensionValidator,
)


class TestEmbeddingResult:
    def test_default_values(self):
        r = EmbeddingResult(vector=[1.0, 2.0])
        assert r.vector == [1.0, 2.0]
        assert r.model == ""
        assert r.dimension == 0

    def test_custom_values(self):
        r = EmbeddingResult(
            vector=[0.1, 0.2, 0.3],
            model="text-embedding-3-small",
            dimension=3,
        )
        assert r.dimension == 3
        assert r.model == "text-embedding-3-small"
        assert len(r.vector) == 3

    def test_vector_mutation(self):
        r = EmbeddingResult(vector=[1.0])
        r.vector.append(2.0)
        assert r.vector == [1.0, 2.0]

    def test_empty_vector(self):
        r = EmbeddingResult(vector=[])
        assert r.vector == []

    def test_dimension_property(self):
        r = EmbeddingResult(vector=[0.5] * 768, dimension=768)
        assert r.dimension == 768

    def test_large_vector(self):
        vec = [0.1] * 1536
        r = EmbeddingResult(vector=vec, model="large", dimension=1536)
        assert len(r.vector) == 1536

    def test_result_equality_by_identity(self):
        r1 = EmbeddingResult(vector=[1.0])
        r2 = EmbeddingResult(vector=[1.0])
        assert r1 is not r2
        assert r1 == r2

    def test_model_empty_string_default(self):
        r = EmbeddingResult(vector=[])
        assert r.model == ""


class TestEmbeddingConfig:
    def test_default_values(self):
        cfg = EmbeddingConfig()
        assert cfg.model == "text-embedding-3-small"
        assert cfg.dimension == 1536
        assert cfg.max_input_tokens == 8192
        assert cfg.batch_size == 32
        assert cfg.api_key is None
        assert cfg.base_url is None

    def test_custom_model(self):
        cfg = EmbeddingConfig(model="custom-model")
        assert cfg.model == "custom-model"

    def test_custom_dimension(self):
        cfg = EmbeddingConfig(dimension=768)
        assert cfg.dimension == 768

    def test_custom_batch_size(self):
        cfg = EmbeddingConfig(batch_size=64)
        assert cfg.batch_size == 64

    def test_custom_max_input_tokens(self):
        cfg = EmbeddingConfig(max_input_tokens=4096)
        assert cfg.max_input_tokens == 4096

    def test_api_key_and_base_url(self):
        cfg = EmbeddingConfig(
            api_key="sk-test", base_url="https://custom.example.com"
        )
        assert cfg.api_key == "sk-test"
        assert cfg.base_url == "https://custom.example.com"

    def test_api_key_none_by_default(self):
        cfg = EmbeddingConfig()
        assert cfg.api_key is None

    def test_base_url_none_by_default(self):
        cfg = EmbeddingConfig()
        assert cfg.base_url is None

    def test_all_custom_values(self):
        cfg = EmbeddingConfig(
            model="test-model",
            dimension=256,
            max_input_tokens=512,
            batch_size=8,
            api_key="test-key",
            base_url="http://localhost:8080",
        )
        assert cfg.model == "test-model"
        assert cfg.dimension == 256
        assert cfg.max_input_tokens == 512
        assert cfg.batch_size == 8
        assert cfg.api_key == "test-key"
        assert cfg.base_url == "http://localhost:8080"

    def test_config_mutable(self):
        cfg = EmbeddingConfig(dimension=768)
        cfg.dimension = 512
        assert cfg.dimension == 512


class TestBaseEmbedder:
    def test_is_abstract(self):
        assert issubclass(BaseEmbedder, ABC)

    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            BaseEmbedder()

    def test_embed_is_abstract(self):
        assert BaseEmbedder.embed.__isabstractmethod__

    def test_embed_query_is_abstract(self):
        assert BaseEmbedder.embed_query.__isabstractmethod__

    def test_concrete_implementation(self):
        class FakeEmbedder(BaseEmbedder):
            async def embed(self, text: str) -> EmbeddingResult:
                return EmbeddingResult(
                    vector=[0.1, 0.2], model="fake", dimension=2,
                )

            async def embed_query(self, query: str) -> EmbeddingResult:
                return EmbeddingResult(
                    vector=[0.3, 0.4], model="fake", dimension=2,
                )

        impl = FakeEmbedder()
        assert impl.provider_id == ""
        assert impl.is_local is False
        assert impl.config is not None
        assert isinstance(impl.config, EmbeddingConfig)

    async def test_embed_batch(self):
        class FakeEmbedder(BaseEmbedder):
            async def embed(self, text: str) -> EmbeddingResult:
                return EmbeddingResult(
                    vector=[float(len(text))], model="t", dimension=1,
                )

            async def embed_query(self, query: str) -> EmbeddingResult:
                return EmbeddingResult(vector=[0.0], model="t", dimension=1)

        impl = FakeEmbedder()
        results = await impl.embed_batch(["a", "bb", "ccc"])
        assert len(results) == 3
        assert results[0].vector == [1.0]
        assert results[1].vector == [2.0]
        assert results[2].vector == [3.0]

    async def test_embed_batch_empty(self):
        class FakeEmbedder(BaseEmbedder):
            async def embed(self, text: str) -> EmbeddingResult:
                return EmbeddingResult(vector=[0.0], model="t", dimension=1)

            async def embed_query(self, query: str) -> EmbeddingResult:
                return EmbeddingResult(vector=[0.0], model="t", dimension=1)

        impl = FakeEmbedder()
        results = await impl.embed_batch([])
        assert results == []

    async def test_embed_batch_single(self):
        class FakeEmbedder(BaseEmbedder):
            async def embed(self, text: str) -> EmbeddingResult:
                return EmbeddingResult(vector=[1.0], model="t", dimension=1)

            async def embed_query(self, query: str) -> EmbeddingResult:
                return EmbeddingResult(vector=[0.0], model="t", dimension=1)

        impl = FakeEmbedder()
        results = await impl.embed_batch(["only"])
        assert len(results) == 1

    async def test_count_tokens(self):
        class FakeEmbedder(BaseEmbedder):
            async def embed(self, text): ...
            async def embed_query(self, query): ...

        impl = FakeEmbedder()
        result = await impl.count_tokens("hello")
        assert result == 1

    async def test_count_tokens_long(self):
        class FakeEmbedder(BaseEmbedder):
            async def embed(self, text): ...
            async def embed_query(self, query): ...

        impl = FakeEmbedder()
        result = await impl.count_tokens("a" * 100)
        assert result == 25

    async def test_count_tokens_empty(self):
        class FakeEmbedder(BaseEmbedder):
            async def embed(self, text): ...
            async def embed_query(self, query): ...

        impl = FakeEmbedder()
        result = await impl.count_tokens("")
        assert result == 0

    async def test_count_tokens_rounds_down(self):
        class FakeEmbedder(BaseEmbedder):
            async def embed(self, text): ...
            async def embed_query(self, query): ...

        impl = FakeEmbedder()
        result = await impl.count_tokens("abc")
        assert result == 0

    def test_default_config(self):
        class FakeEmbedder(BaseEmbedder):
            async def embed(self, text): ...
            async def embed_query(self, query): ...

        impl = FakeEmbedder()
        assert impl.config.dimension == 1536

    def test_custom_config(self):
        class FakeEmbedder(BaseEmbedder):
            async def embed(self, text): ...
            async def embed_query(self, query): ...

        cfg = EmbeddingConfig(dimension=512)
        impl = FakeEmbedder(config=cfg)
        assert impl.config.dimension == 512

    def test_provider_id_empty_default(self):
        class FakeEmbedder(BaseEmbedder):
            async def embed(self, text): ...
            async def embed_query(self, query): ...

        impl = FakeEmbedder()
        assert impl.provider_id == ""

    def test_model_empty_default(self):
        class FakeEmbedder(BaseEmbedder):
            async def embed(self, text): ...
            async def embed_query(self, query): ...

        impl = FakeEmbedder()
        assert impl.model == ""

    def test_config_is_not_none_when_default(self):
        class FakeEmbedder(BaseEmbedder):
            async def embed(self, text): ...
            async def embed_query(self, query): ...

        impl = FakeEmbedder()
        assert impl.config is not None


class TestEmbeddingCache:
    def test_default_max_size(self):
        cache = EmbeddingCache()
        assert cache._max_size == 10000

    def test_custom_max_size(self):
        cache = EmbeddingCache(max_size=5)
        assert cache._max_size == 5

    def test_set_and_get(self):
        cache = EmbeddingCache()
        result = EmbeddingResult(vector=[1.0], model="m", dimension=1)
        cache.set("hello", "m", result)
        cached = cache.get("hello", "m")
        assert cached is result

    def test_get_cache_miss_returns_none(self):
        cache = EmbeddingCache()
        assert cache.get("unknown", "m") is None

    def test_get_different_model_miss(self):
        cache = EmbeddingCache()
        result = EmbeddingResult(vector=[1.0], model="m1", dimension=1)
        cache.set("text", "m1", result)
        assert cache.get("text", "m2") is None

    def test_get_different_text_miss(self):
        cache = EmbeddingCache()
        result = EmbeddingResult(vector=[1.0], model="m", dimension=1)
        cache.set("text1", "m", result)
        assert cache.get("text2", "m") is None

    def test_key_is_sha256(self):
        cache = EmbeddingCache()
        result = EmbeddingResult(vector=[0.0], model="m", dimension=1)
        cache.set("data", "m", result)
        expected_key = hashlib.sha256(b"m:data").hexdigest()
        assert expected_key in cache._cache

    def test_key_uses_both_text_and_model(self):
        cache = EmbeddingCache()
        cache.set("text", "m1", EmbeddingResult(vector=[0.0]))
        cache.set("text", "m2", EmbeddingResult(vector=[1.0]))
        assert cache.size() == 2

    def test_overwrite_existing(self):
        cache = EmbeddingCache()
        r1 = EmbeddingResult(vector=[1.0], model="m", dimension=1)
        r2 = EmbeddingResult(vector=[2.0], model="m", dimension=1)
        cache.set("same", "m", r1)
        cache.set("same", "m", r2)
        assert cache.get("same", "m") is r2
        assert cache.size() == 1

    def test_size_empty(self):
        cache = EmbeddingCache(max_size=100)
        assert cache.size() == 0

    def test_size_after_inserts(self):
        cache = EmbeddingCache(max_size=100)
        for i in range(10):
            cache.set(f"text{i}", "m", EmbeddingResult(vector=[0.0]))
        assert cache.size() == 10

    def test_clear(self):
        cache = EmbeddingCache(max_size=100)
        for i in range(5):
            cache.set(f"t{i}", "m", EmbeddingResult(vector=[0.0]))
        cache.clear()
        assert cache.size() == 0

    def test_clear_empty(self):
        cache = EmbeddingCache()
        cache.clear()
        assert cache.size() == 0

    def test_eviction_on_full_cache_removes_oldest(self):
        cache = EmbeddingCache(max_size=4)
        for i in range(4):
            r = EmbeddingResult(vector=[float(i)], model="m")
            cache.set(f"text{i}", "m", r)

        cache.set("overflow", "m", EmbeddingResult(vector=[9.0]))
        assert cache.size() == 4

        oldest_key = hashlib.sha256(b"m:text0").hexdigest()
        assert oldest_key not in cache._cache

        new_key = hashlib.sha256(b"m:overflow").hexdigest()
        assert new_key in cache._cache

    def test_evict_removes_25_percent_oldest(self):
        cache = EmbeddingCache(max_size=8)
        for i in range(8):
            cache.set(f"k{i}", "m", EmbeddingResult(vector=[float(i)]))

        cache.set("new", "m", EmbeddingResult(vector=[99.0]))
        assert cache.size() == 7
        for i in range(2):
            key = hashlib.sha256(f"m:k{i}".encode()).hexdigest()
            assert key not in cache._cache

    def test_eviction_preserves_recent_entries(self):
        cache = EmbeddingCache(max_size=4)
        for i in range(4):
            cache.set(f"text{i}", "m", EmbeddingResult(vector=[float(i)]))

        cache.set("text4", "m", EmbeddingResult(vector=[4.0]))
        for i in range(2, 5):
            key = hashlib.sha256(f"m:text{i}".encode()).hexdigest()
            assert key in cache._cache

    def test_no_eviction_below_max_size(self):
        cache = EmbeddingCache(max_size=10)
        for i in range(9):
            cache.set(f"t{i}", "m", EmbeddingResult(vector=[0.0]))
        assert cache.size() == 9

    def test_eviction_on_exact_boundary(self):
        cache = EmbeddingCache(max_size=1)
        cache.set("a", "m", EmbeddingResult(vector=[0.0]))
        cache.set("b", "m", EmbeddingResult(vector=[1.0]))
        assert cache.size() == 2

    def test_get_batch(self):
        cache = EmbeddingCache(max_size=100)
        r0 = EmbeddingResult(vector=[0.0], model="m")
        r2 = EmbeddingResult(vector=[2.0], model="m")
        cache.set("text0", "m", r0)
        cache.set("text2", "m", r2)

        texts = ["text0", "text1", "text2", "text3"]
        batch = cache.get_batch(texts, "m")
        assert len(batch) == 2
        assert batch[0] is r0
        assert batch[2] is r2

    def test_get_batch_empty(self):
        cache = EmbeddingCache()
        assert cache.get_batch([], "m") == {}

    def test_get_batch_none_cached(self):
        cache = EmbeddingCache()
        texts = ["a", "b"]
        assert cache.get_batch(texts, "m") == {}

    def test_get_batch_all_cached(self):
        cache = EmbeddingCache(max_size=100)
        r0 = EmbeddingResult(vector=[0.0], model="m")
        r1 = EmbeddingResult(vector=[1.0], model="m")
        cache.set("a", "m", r0)
        cache.set("b", "m", r1)
        batch = cache.get_batch(["a", "b"], "m")
        assert len(batch) == 2
        assert batch[0] is r0
        assert batch[1] is r1

    def test_get_batch_partial_overlap(self):
        cache = EmbeddingCache(max_size=100)
        r = EmbeddingResult(vector=[0.0], model="m")
        cache.set("x", "m", r)
        batch = cache.get_batch(["x", "y", "z"], "m")
        assert len(batch) == 1
        assert batch[0] is r

    def test_get_after_clear_returns_none(self):
        cache = EmbeddingCache()
        cache.set("text", "m", EmbeddingResult(vector=[0.0]))
        cache.clear()
        assert cache.get("text", "m") is None


class TestDimensionValidator:
    def test_valid_dimension_match(self):
        validator = DimensionValidator()
        result = validator.validate([1.0, 2.0, 3.0], expected_dimension=3)
        assert result.is_valid
        assert result.expected == 3
        assert result.actual == 3
        assert result.errors == []

    def test_invalid_dimension_mismatch(self):
        validator = DimensionValidator()
        result = validator.validate([1.0, 2.0], expected_dimension=3)
        assert not result.is_valid
        assert result.expected == 3
        assert result.actual == 2
        assert len(result.errors) == 1
        assert "Expected dimension 3, got 2" in result.errors[0]

    def test_empty_vector_zero_dimension(self):
        validator = DimensionValidator()
        result = validator.validate([], expected_dimension=0)
        assert result.is_valid
        assert result.expected == 0
        assert result.actual == 0

    def test_empty_vector_nonzero_expected(self):
        validator = DimensionValidator()
        result = validator.validate([], expected_dimension=3)
        assert not result.is_valid
        assert "Expected dimension 3, got 0" in result.errors[0]

    def test_large_vector_valid(self):
        validator = DimensionValidator()
        vec = [0.5] * 1536
        result = validator.validate(vec, expected_dimension=1536)
        assert result.is_valid

    def test_large_vector_invalid(self):
        validator = DimensionValidator()
        vec = [0.5] * 100
        result = validator.validate(vec, expected_dimension=1536)
        assert not result.is_valid
        assert "Expected dimension 1536, got 100" in result.errors[0]

    def test_single_element_vector(self):
        validator = DimensionValidator()
        result = validator.validate([1.0], expected_dimension=1)
        assert result.is_valid

    def test_validate_batch_all_valid(self):
        validator = DimensionValidator()
        vectors = [[1.0, 2.0], [3.0, 4.0]]
        results = validator.validate_batch(vectors, expected_dimension=2)
        assert len(results) == 2
        assert all(r.is_valid for r in results)

    def test_validate_batch_mixed(self):
        validator = DimensionValidator()
        vectors = [[1.0, 2.0], [1.0, 2.0, 3.0]]
        results = validator.validate_batch(vectors, expected_dimension=2)
        assert len(results) == 2
        assert results[0].is_valid
        assert not results[1].is_valid

    def test_validate_batch_empty(self):
        validator = DimensionValidator()
        results = validator.validate_batch([], expected_dimension=3)
        assert results == []

    def test_validate_batch_single(self):
        validator = DimensionValidator()
        results = validator.validate_batch([[1.0]], expected_dimension=1)
        assert len(results) == 1
        assert results[0].is_valid

    def test_validate_batch_all_invalid(self):
        validator = DimensionValidator()
        vectors = [[1.0], [2.0, 3.0]]
        results = validator.validate_batch(vectors, expected_dimension=1)
        assert len(results) == 2
        assert results[0].is_valid
        assert not results[1].is_valid

    def test_dimension_validation_result_defaults(self):
        r = DimensionValidationResult()
        assert r.is_valid
        assert r.expected == 0
        assert r.actual == 0
        assert r.errors == []

    def test_dimension_validation_result_custom(self):
        r = DimensionValidationResult(
            is_valid=False, expected=5, actual=3, errors=["mismatch"],
        )
        assert not r.is_valid
        assert r.expected == 5
        assert r.actual == 3
        assert r.errors == ["mismatch"]

    def test_dimension_validation_result_mutable(self):
        r = DimensionValidationResult()
        r.is_valid = False
        r.errors.append("new error")
        assert not r.is_valid
        assert r.errors == ["new error"]

    def test_dimension_validation_result_multiple_errors(self):
        r = DimensionValidationResult(
            is_valid=False,
            expected=10,
            actual=5,
            errors=["error a", "error b"],
        )
        assert len(r.errors) == 2
