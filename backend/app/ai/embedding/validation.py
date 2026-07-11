from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DimensionValidationResult:
    is_valid: bool = True
    expected: int = 0
    actual: int = 0
    errors: list[str] = field(default_factory=list)


class DimensionValidator:
    def validate(
        self, vector: list[float], expected_dimension: int
    ) -> DimensionValidationResult:
        result = DimensionValidationResult(
            expected=expected_dimension,
            actual=len(vector),
        )
        if len(vector) != expected_dimension:
            result.is_valid = False
            result.errors.append(
                f"Expected dimension {expected_dimension}, got {len(vector)}"
            )
        return result

    def validate_batch(
        self, vectors: list[list[float]], expected_dimension: int
    ) -> list[DimensionValidationResult]:
        return [self.validate(v, expected_dimension) for v in vectors]
