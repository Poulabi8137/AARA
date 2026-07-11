from __future__ import annotations

from datetime import datetime

from app.utils.helpers import (
    deep_merge,
    format_timestamp,
    generate_uuid,
    safe_get,
    slugify,
    truncate,
    utc_now,
)


class TestGenerateUUID:
    def test_returns_string(self):
        result = generate_uuid()
        assert isinstance(result, str)
        assert len(result) == 36

    def test_unique(self):
        assert generate_uuid() != generate_uuid()


class TestUtcNow:
    def test_returns_datetime(self):
        assert isinstance(utc_now(), datetime)

    def test_has_tzinfo(self):
        assert utc_now().tzinfo is not None


class TestSlugify:
    def test_basic(self):
        assert slugify("Hello World") == "hello-world"

    def test_special_chars(self):
        assert slugify("Research & Development!") == "research-development"

    def test_multiple_spaces(self):
        assert slugify("hello   world") == "hello-world"


class TestTruncate:
    def test_short_string(self):
        assert truncate("hello", 10) == "hello"

    def test_long_string(self):
        result = truncate("hello world this is long", 10)
        assert len(result) == 10
        assert result.endswith("...")

    def test_custom_suffix(self):
        result = truncate("hello world this is long", 10, suffix="..")
        assert result.endswith("..")


class TestDeepMerge:
    def test_simple_override(self):
        result = deep_merge({"a": 1, "b": 2}, {"b": 3})
        assert result == {"a": 1, "b": 3}

    def test_nested_merge(self):
        result = deep_merge({"a": {"x": 1}}, {"a": {"y": 2}})
        assert result == {"a": {"x": 1, "y": 2}}

    def test_new_keys(self):
        result = deep_merge({"a": 1}, {"b": 2})
        assert result == {"a": 1, "b": 2}


class TestSafeGet:
    def test_simple_key(self):
        assert safe_get({"a": 1}, "a") == 1

    def test_nested_path(self):
        assert safe_get({"a": {"b": {"c": 42}}}, "a.b.c") == 42

    def test_missing_key_returns_default(self):
        assert safe_get({"a": 1}, "b") is None
        assert safe_get({"a": 1}, "b", default=0) == 0

    def test_none_intermediate(self):
        assert safe_get({"a": None}, "a.b") is None


class TestFormatTimestamp:
    def test_none(self):
        assert format_timestamp(None) is None

    def test_formats_datetime(self):
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = format_timestamp(dt)
        assert result == "2024-01-15T10:30:00Z"
