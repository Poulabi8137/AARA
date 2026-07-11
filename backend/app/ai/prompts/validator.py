from __future__ import annotations

from dataclasses import dataclass, field

from app.ai.prompts.templates import PromptTemplate


@dataclass
class ValidationResult:
    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class PromptValidator:
    MAX_TEMPLATE_LENGTH = 100_000
    MAX_VARIABLE_LENGTH = 10_000

    def validate(self, template: PromptTemplate) -> ValidationResult:
        result = ValidationResult()
        content = template.content

        if not content:
            result.is_valid = False
            result.errors.append("Template content is empty")
            return result

        if len(content) > self.MAX_TEMPLATE_LENGTH:
            result.is_valid = False
            result.errors.append(f"Template exceeds {self.MAX_TEMPLATE_LENGTH} characters")

        open_count = content.count("{{")
        close_count = content.count("}}")
        if open_count != close_count:
            result.is_valid = False
            result.errors.append("Mismatched template delimiters {{ }}")

        if template.versions:
            for version in template.versions:
                if not version.content:
                    result.warnings.append(f"Version {version.version} has empty content")

        return result

    def validate_rendered(self, text: str) -> ValidationResult:
        result = ValidationResult()

        if len(text) > self.MAX_TEMPLATE_LENGTH:
            result.is_valid = False
            result.errors.append(f"Rendered text exceeds {self.MAX_TEMPLATE_LENGTH} characters")

        unresolved = self._find_unresolved_variables(text)
        if unresolved:
            result.warnings.append(f"Unresolved variables: {unresolved}")

        return result

    def _find_unresolved_variables(self, text: str) -> list[str]:
        import re
        return re.findall(r"\{\{(\w+)\}\}", text)
