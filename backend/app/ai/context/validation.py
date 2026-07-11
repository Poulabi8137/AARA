from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.ai.context.assembler import ContextSection


@dataclass
class ContextValidationResult:
    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ContextValidator:
    MAX_SECTION_SIZE = 100_000
    MAX_TOTAL_SIZE = 1_000_000

    def validate_section(self, section: ContextSection) -> ContextValidationResult:
        result = ContextValidationResult()

        if not section.content:
            result.errors.append(f"Section '{section.name}' has empty content")
            result.is_valid = False

        if len(section.content) > self.MAX_SECTION_SIZE:
            result.errors.append(f"Section '{section.name}' exceeds max size")
            result.is_valid = False

        if section.token_count > 0:
            estimated = len(section.content) // 4
            if abs(estimated - section.token_count) > section.token_count * 0.5:
                result.warnings.append(
                    f"Section '{section.name}' token count may be inaccurate"
                )

        return result

    def validate_context(self, sections: list[ContextSection]) -> ContextValidationResult:
        result = ContextValidationResult()
        total_size = 0

        for section in sections:
            section_result = self.validate_section(section)
            if not section_result.is_valid:
                result.is_valid = False
                result.errors.extend(section_result.errors)
            result.warnings.extend(section_result.warnings)
            total_size += len(section.content)

        if total_size > self.MAX_TOTAL_SIZE:
            result.warnings.append(f"Total context size {total_size} exceeds recommended limit")

        return result
