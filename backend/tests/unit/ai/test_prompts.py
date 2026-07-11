from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.ai.prompts.registry import PromptRegistry
from app.ai.prompts.renderer import PromptRenderer
from app.ai.prompts.templates import PromptRole, PromptTemplate, PromptVersion
from app.ai.prompts.validator import PromptValidator, ValidationResult


class TestPromptRole:
    def test_enum_values(self):
        assert PromptRole.SYSTEM.value == "system"
        assert PromptRole.DEVELOPER.value == "developer"
        assert PromptRole.USER.value == "user"
        assert PromptRole.AGENT.value == "agent"

    def test_enum_membership(self):
        assert PromptRole.SYSTEM in PromptRole
        assert PromptRole.DEVELOPER in PromptRole
        assert PromptRole.USER in PromptRole
        assert PromptRole.AGENT in PromptRole

    def test_enum_from_value(self):
        assert PromptRole("system") is PromptRole.SYSTEM
        assert PromptRole("developer") is PromptRole.DEVELOPER
        assert PromptRole("user") is PromptRole.USER
        assert PromptRole("agent") is PromptRole.AGENT

    def test_enum_invalid_value_raises(self):
        with pytest.raises(ValueError):
            PromptRole("assistant")

    def test_enum_inequality(self):
        assert PromptRole.SYSTEM != PromptRole.USER

    def test_enum_str_repr(self):
        assert str(PromptRole.SYSTEM) == "PromptRole.SYSTEM"

    def test_enum_hashable(self):
        roles = {PromptRole.SYSTEM, PromptRole.USER}
        assert len(roles) == 2


class TestPromptVersion:
    def test_default_values(self):
        v = PromptVersion()
        assert v.version == "v1"
        assert v.content == ""
        assert v.created_at == ""
        assert v.description == ""

    def test_custom_values(self):
        now = datetime.now(UTC).isoformat()
        v = PromptVersion(
            version="v2",
            content="You are a helpful assistant.",
            created_at=now,
            description="Added helpful tone.",
        )
        assert v.version == "v2"
        assert v.content == "You are a helpful assistant."
        assert v.created_at == now
        assert v.description == "Added helpful tone."

    def test_mutable_fields(self):
        v = PromptVersion(version="v3", content="Be concise.")
        v.content = "Be extremely concise."
        v.description = "More specific"
        assert v.content == "Be extremely concise."
        assert v.description == "More specific"

    def test_empty_version(self):
        v = PromptVersion(version="")
        assert v.version == ""
        assert v.content == ""

    def test_version_ordering_independent(self):
        v1 = PromptVersion(version="v1")
        v2 = PromptVersion(version="v10")
        assert v1.version < v2.version  # string comparison


class TestPromptTemplate:
    def test_minimal_creation(self):
        t = PromptTemplate(name="greeting")
        assert t.name == "greeting"
        assert t.role is PromptRole.SYSTEM
        assert t.content == ""
        assert t.variables == []
        assert t.versions == []
        assert t.metadata == {}

    def test_full_creation(self):
        t = PromptTemplate(
            name="qa",
            role=PromptRole.USER,
            content="Answer {{question}}",
            variables=["question"],
            metadata={"author": "test"},
        )
        assert t.role is PromptRole.USER
        assert t.content == "Answer {{question}}"
        assert t.variables == ["question"]
        assert t.metadata == {"author": "test"}

    def test_name_is_readonly_property(self):
        t = PromptTemplate(name="test-prompt")
        assert t.name == "test-prompt"

    def test_non_system_role(self):
        t = PromptTemplate(name="t", role=PromptRole.AGENT)
        assert t.role is PromptRole.AGENT

    def test_content_empty_string(self):
        t = PromptTemplate(name="t", content="")
        assert t.content == ""

    def test_add_version(self):
        t = PromptTemplate(name="multi")
        v1 = PromptVersion(version="v1", content="first")
        v2 = PromptVersion(version="v2", content="second")
        t.add_version(v1)
        t.add_version(v2)
        assert len(t.versions) == 2
        assert t.versions[0] is v1
        assert t.versions[1] is v2

    def test_get_version_found(self):
        t = PromptTemplate(name="t")
        v = PromptVersion(version="v2", content="updated")
        t.add_version(v)
        assert t.get_version("v2") is v

    def test_get_version_not_found(self):
        t = PromptTemplate(name="t")
        t.add_version(PromptVersion(version="v5", content="data"))
        assert t.get_version("v999") is None

    def test_get_version_no_versions(self):
        t = PromptTemplate(name="t")
        assert t.get_version("v1") is None

    def test_get_version_exact_match(self):
        t = PromptTemplate(name="t")
        v = PromptVersion(version="v2", content="v2")
        t.add_version(v)
        assert t.get_version("v2") is v
        assert t.get_version("V2") is None

    def test_render_single_variable(self):
        t = PromptTemplate(name="greet", content="Hello {{name}}!")
        result = t.render(name="World")
        assert result == "Hello World!"

    def test_render_multiple_variables(self):
        t = PromptTemplate(
            name="intro", content="{{greeting}}, {{name}}! You are {{age}}."
        )
        result = t.render(greeting="Hi", name="Alice", age="30")
        assert result == "Hi, Alice! You are 30."

    def test_render_missing_variable_leaves_placeholder(self):
        t = PromptTemplate(name="t", content="Hello {{name}} {{title}}")
        result = t.render(name="Bob")
        assert result == "Hello Bob {{title}}"

    def test_render_no_variables(self):
        t = PromptTemplate(name="static", content="Static text")
        result = t.render()
        assert result == "Static text"

    def test_render_with_numeric_value(self):
        t = PromptTemplate(name="t", content="Count: {{n}}")
        result = t.render(n=42)
        assert result == "Count: 42"

    def test_render_repeated_variable(self):
        t = PromptTemplate(name="t", content="{{x}} {{x}} {{x}}")
        result = t.render(x="same")
        assert result == "same same same"

    def test_get_variable_names(self):
        t = PromptTemplate(name="t", content="{{a}} {{b}} {{a}} {{c}}")
        names = t.get_variable_names()
        assert names == ["a", "b", "a", "c"]

    def test_get_variable_names_none(self):
        t = PromptTemplate(name="t", content="No placeholders here")
        assert t.get_variable_names() == []

    def test_get_variable_names_empty_content(self):
        t = PromptTemplate(name="t")
        assert t.get_variable_names() == []

    def test_get_variable_names_duplicates(self):
        t = PromptTemplate(name="t", content="{{x}} {{x}} {{y}}")
        names = t.get_variable_names()
        assert names == ["x", "x", "y"]

    def test_prompt_role_property(self):
        t = PromptTemplate(name="t", role=PromptRole.USER)
        assert t.role is PromptRole.USER

    def test_content_with_special_chars(self):
        t = PromptTemplate(name="t", content="Price: ${{amount}}")
        assert t.render(amount="100") == "Price: $100"


class TestPromptRegistry:
    def test_register_and_get(self):
        registry = PromptRegistry()
        t = PromptTemplate(name="welcome", content="Welcome!")
        registry.register(t)
        assert registry.get("welcome") is t

    def test_get_nonexistent_returns_none(self):
        registry = PromptRegistry()
        assert registry.get("nonexistent") is None

    def test_register_overwrites(self):
        registry = PromptRegistry()
        t1 = PromptTemplate(name="dup", content="first")
        t2 = PromptTemplate(name="dup", content="second")
        registry.register(t1)
        registry.register(t2)
        assert registry.get("dup") is t2

    def test_list_templates(self):
        registry = PromptRegistry()
        registry.register(PromptTemplate(name="a"))
        registry.register(PromptTemplate(name="b"))
        assert sorted(registry.list_templates()) == ["a", "b"]

    def test_list_templates_empty(self):
        registry = PromptRegistry()
        assert registry.list_templates() == []

    def test_list_templates_after_delete(self):
        registry = PromptRegistry()
        registry.register(PromptTemplate(name="a"))
        registry.register(PromptTemplate(name="b"))
        registry.delete("a")
        assert registry.list_templates() == ["b"]

    def test_register_from_dict(self):
        registry = PromptRegistry()
        registry.register_from_dict(
            name="dict_template",
            content="Hello {{user}}",
            role=PromptRole.USER,
        )
        t = registry.get("dict_template")
        assert t is not None
        assert t.name == "dict_template"
        assert t.content == "Hello {{user}}"
        assert t.role is PromptRole.USER
        assert len(t.versions) == 1
        assert t.versions[0].version == "v1"

    def test_register_from_dict_default_role(self):
        registry = PromptRegistry()
        registry.register_from_dict(name="default_role", content="Hi")
        t = registry.get("default_role")
        assert t is not None
        assert t.role is PromptRole.SYSTEM

    def test_register_from_dict_empty_content(self):
        registry = PromptRegistry()
        registry.register_from_dict(name="empty", content="")
        t = registry.get("empty")
        assert t is not None
        assert t.content == ""

    def test_get_rendered_base_template(self):
        registry = PromptRegistry()
        registry.register_from_dict(name="t", content="Hello {{user}}")
        result = registry.get_rendered("t", user="World")
        assert result == "Hello World"

    def test_get_rendered_versioned(self):
        registry = PromptRegistry()
        registry.register_from_dict(name="t", content="v0")
        t = registry.get("t")
        t.add_version(PromptVersion(version="v2", content="Hello {{user}}"))
        result = registry.get_rendered("t", version="v2", user="Alice")
        assert result == "Hello Alice"

    def test_get_rendered_nonexistent(self):
        registry = PromptRegistry()
        assert registry.get_rendered("unknown") is None

    def test_get_rendered_fallback_to_template(self):
        registry = PromptRegistry()
        registry.register_from_dict(name="t", content="Hi {{user}}")
        result = registry.get_rendered("t", version="non_existent", user="Bob")
        assert result == "Hi Bob"

    def test_get_rendered_with_no_variables(self):
        registry = PromptRegistry()
        registry.register_from_dict(name="t", content="Static text")
        result = registry.get_rendered("t")
        assert result == "Static text"

    def test_get_rendered_with_version_without_variables(self):
        registry = PromptRegistry()
        registry.register_from_dict(name="t", content="base")
        t = registry.get("t")
        t.add_version(PromptVersion(version="v2", content="version two"))
        result = registry.get_rendered("t", version="v2")
        assert result == "version two"

    def test_set_active_version(self):
        registry = PromptRegistry()
        registry.register_from_dict(name="t", content="v1 content")
        t = registry.get("t")
        t.add_version(PromptVersion(version="v2", content="v2 content"))
        registry.set_active_version("t", "v2")
        result = registry.get_rendered("t")
        assert result == "v2 content"

    def test_set_active_version_then_render_with_variables(self):
        registry = PromptRegistry()
        registry.register_from_dict(name="t", content="original")
        t = registry.get("t")
        t.add_version(PromptVersion(version="v2", content="version 2: {{x}}"))
        registry.set_active_version("t", "v2")
        result = registry.get_rendered("t", x="hello")
        assert result == "version 2: hello"

    def test_active_version_initialized_on_register(self):
        registry = PromptRegistry()
        t = PromptTemplate(name="new_template", content="hi")
        registry.register(t)
        result = registry.get_rendered("new_template")
        assert result == "hi"

    def test_delete_removes_template(self):
        registry = PromptRegistry()
        registry.register_from_dict(name="t", content="data")
        assert registry.get("t") is not None
        registry.delete("t")
        assert registry.get("t") is None

    def test_delete_removes_active_version(self):
        registry = PromptRegistry()
        registry.register_from_dict(name="t", content="data")
        registry.set_active_version("t", "v2")
        registry.delete("t")
        registry.register_from_dict(name="t", content="fresh")
        assert registry.get("t") is not None

    def test_delete_nonexistent(self):
        registry = PromptRegistry()
        registry.delete("never_registered")

    def test_set_active_version_nonexistent_template(self):
        registry = PromptRegistry()
        registry.set_active_version("unknown", "v2")

    def test_get_rendered_with_version_uses_version_content(self):
        registry = PromptRegistry()
        registry.register_from_dict(name="t", content="original")
        t = registry.get("t")
        t.add_version(PromptVersion(version="v2", content="v2 content"))
        result = registry.get_rendered("t", version="v2")
        assert result == "v2 content"

    def test_register_with_existing_name_updates(self):
        registry = PromptRegistry()
        t1 = PromptTemplate(name="t", content="first")
        t2 = PromptTemplate(name="t", content="second")
        registry.register(t1)
        registry.register(t2)
        assert registry.get("t") is t2


class TestPromptRenderer:
    def test_render_simple(self):
        renderer = PromptRenderer()
        t = PromptTemplate(name="t", content="Hello {{name}}")
        result = renderer.render(t, name="World")
        assert result == "Hello World"

    def test_render_no_substitutions(self):
        renderer = PromptRenderer()
        t = PromptTemplate(name="t", content="Static")
        result = renderer.render(t)
        assert result == "Static"

    def test_render_string(self):
        renderer = PromptRenderer()
        result = renderer.render_string("{{a}} and {{b}}", a="X", b="Y")
        assert result == "X and Y"

    def test_render_string_no_variables(self):
        renderer = PromptRenderer()
        result = renderer.render_string("Plain text")
        assert result == "Plain text"

    def test_missing_variable_left_untouched(self):
        renderer = PromptRenderer()
        result = renderer.render_string("Hello {{name}}")
        assert result == "Hello {{name}}"

    def test_render_with_extra_variables(self):
        renderer = PromptRenderer()
        t = PromptTemplate(name="t", content="{{a}}")
        result = renderer.render(t, a="1", b="2")
        assert result == "1"

    def test_get_missing_variables(self):
        renderer = PromptRenderer()
        t = PromptTemplate(
            name="t",
            content="Hello {{name}}, you are {{age}}",
            variables=["name"],
        )
        missing = renderer.get_missing_variables(t)
        assert missing == ["age"]

    def test_get_missing_variables_none(self):
        renderer = PromptRenderer()
        t = PromptTemplate(
            name="t",
            content="Hello {{name}}",
            variables=["name"],
        )
        assert renderer.get_missing_variables(t) == []

    def test_get_missing_variables_empty_declared(self):
        renderer = PromptRenderer()
        t = PromptTemplate(
            name="t",
            content="Hello {{name}}",
            variables=[],
        )
        missing = renderer.get_missing_variables(t)
        assert missing == ["name"]

    def test_get_missing_variables_extra_declared(self):
        renderer = PromptRenderer()
        t = PromptTemplate(
            name="t",
            content="Hello {{name}}",
            variables=["name", "extra"],
        )
        assert renderer.get_missing_variables(t) == []

    def test_extract_variables(self):
        renderer = PromptRenderer()
        result = renderer.extract_variables("{{a}} {{b}} {{a}}")
        assert result == ["a", "b", "a"]

    def test_extract_variables_none(self):
        renderer = PromptRenderer()
        assert renderer.extract_variables("no braces") == []

    def test_extract_variables_empty_string(self):
        renderer = PromptRenderer()
        assert renderer.extract_variables("") == []

    def test_render_with_nested_braces_in_value(self):
        renderer = PromptRenderer()
        t = PromptTemplate(name="t", content="Data: {{data}}")
        result = renderer.render(t, data="{nested}")
        assert result == "Data: {nested}"

    def test_render_with_special_characters(self):
        renderer = PromptRenderer()
        result = renderer.render_string("{{x}}", x="foo $%^ bar")
        assert result == "foo $%^ bar"

    def test_render_multiple_occurrences(self):
        renderer = PromptRenderer()
        result = renderer.render_string("{{x}} {{x}} {{x}}", x="same")
        assert result == "same same same"

    def test_render_string_with_unicode(self):
        renderer = PromptRenderer()
        result = renderer.render_string("{{g}}", g="\u2713")
        assert result == "\u2713"

    def test_extract_variables_with_underscores(self):
        renderer = PromptRenderer()
        result = renderer.extract_variables("{{my_var}} and {{_private}}")
        assert result == ["my_var", "_private"]


class TestPromptValidator:
    def test_valid_template(self):
        validator = PromptValidator()
        t = PromptTemplate(name="t", content="Hello {{name}}")
        result = validator.validate(t)
        assert result.is_valid
        assert result.errors == []
        assert result.warnings == []

    def test_empty_content_invalid(self):
        validator = PromptValidator()
        t = PromptTemplate(name="t", content="")
        result = validator.validate(t)
        assert not result.is_valid
        assert "Template content is empty" in result.errors

    def test_exceeds_max_length(self):
        validator = PromptValidator()
        t = PromptTemplate(name="t", content="x" * 100_001)
        result = validator.validate(t)
        assert not result.is_valid
        assert any("exceeds" in e.lower() for e in result.errors)

    def test_exactly_max_length_valid(self):
        validator = PromptValidator()
        t = PromptTemplate(name="t", content="x" * 100_000)
        result = validator.validate(t)
        assert result.is_valid

    def test_mismatched_delimiters_open_only(self):
        validator = PromptValidator()
        t = PromptTemplate(name="t", content="Hello {{name")
        result = validator.validate(t)
        assert not result.is_valid
        assert "Mismatched template delimiters {{ }}" in result.errors

    def test_mismatched_delimiters_close_only(self):
        validator = PromptValidator()
        t = PromptTemplate(name="t", content="Hello name}}")
        result = validator.validate(t)
        assert not result.is_valid
        assert "Mismatched template delimiters {{ }}" in result.errors

    def test_balanced_delimiters(self):
        validator = PromptValidator()
        t = PromptTemplate(name="t", content="{{a}} {{b}}")
        result = validator.validate(t)
        assert result.is_valid

    def test_empty_version_warning(self):
        validator = PromptValidator()
        t = PromptTemplate(name="t", content="Hello")
        t.add_version(PromptVersion(version="v1", content=""))
        result = validator.validate(t)
        assert result.is_valid
        assert any("empty content" in w.lower() for w in result.warnings)

    def test_multiple_versions_all_valid(self):
        validator = PromptValidator()
        t = PromptTemplate(name="t", content="Hello")
        t.add_version(PromptVersion(version="v1", content="Hi"))
        t.add_version(PromptVersion(version="v2", content="Hey"))
        result = validator.validate(t)
        assert result.is_valid

    def test_multiple_versions_with_empty_warnings(self):
        validator = PromptValidator()
        t = PromptTemplate(name="t", content="Hello")
        t.add_version(PromptVersion(version="v1", content="Hi"))
        t.add_version(PromptVersion(version="v2", content=""))
        t.add_version(PromptVersion(version="v3", content=""))
        result = validator.validate(t)
        assert result.is_valid
        assert len(result.warnings) == 2

    def test_mixed_errors_and_warnings(self):
        validator = PromptValidator()
        t = PromptTemplate(name="t", content="Hello {{")
        t.add_version(PromptVersion(version="v1", content=""))
        result = validator.validate(t)
        assert not result.is_valid
        assert len(result.errors) >= 1
        assert any("delimiter" in e.lower() for e in result.errors)
        assert any("empty content" in w.lower() for w in result.warnings)

    def test_validate_rendered_too_long(self):
        validator = PromptValidator()
        result = validator.validate_rendered("x" * 100_001)
        assert not result.is_valid
        assert any("exceeds" in e.lower() for e in result.errors)

    def test_validate_rendered_unresolved_variables(self):
        validator = PromptValidator()
        result = validator.validate_rendered("Hello {{name}}")
        assert result.is_valid
        assert any("Unresolved" in w for w in result.warnings)

    def test_validate_rendered_clean(self):
        validator = PromptValidator()
        result = validator.validate_rendered("Hello World")
        assert result.is_valid
        assert result.warnings == []

    def test_validate_rendered_empty(self):
        validator = PromptValidator()
        result = validator.validate_rendered("")
        assert result.is_valid

    def test_validate_rendered_exactly_max_length(self):
        validator = PromptValidator()
        result = validator.validate_rendered("x" * 100_000)
        assert result.is_valid

    def test_validation_result_defaults(self):
        r = ValidationResult()
        assert r.is_valid
        assert r.errors == []
        assert r.warnings == []

    def test_validation_result_custom(self):
        r = ValidationResult(
            is_valid=False,
            errors=["error1"],
            warnings=["warning1"],
        )
        assert not r.is_valid
        assert r.errors == ["error1"]
        assert r.warnings == ["warning1"]

    def test_validation_result_mutable(self):
        r = ValidationResult()
        r.is_valid = False
        r.errors.append("new error")
        assert not r.is_valid
        assert "new error" in r.errors

    def test_max_length_constant(self):
        assert PromptValidator.MAX_TEMPLATE_LENGTH == 100_000
        assert PromptValidator.MAX_VARIABLE_LENGTH == 10_000
