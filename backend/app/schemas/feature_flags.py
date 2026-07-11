from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class FeatureFlagUpdate(BaseModel):
    enabled: bool
    config: dict[str, Any] | None = None


class FeatureFlagsResponse(BaseModel):
    flags: dict[str, bool]
