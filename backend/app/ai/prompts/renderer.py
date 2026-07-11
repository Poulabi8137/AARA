from __future__ import annotations

import re
from typing import Any

from app.ai.prompts.templates import PromptTemplate


class PromptRenderer:
    def render(self, template: PromptTemplate, **variables: Any) -> str:
        result = template.content
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value))
        return result

    def render_string(self, text: str, **variables: Any) -> str:
        result = text
        for key, value in variables.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result

    def get_missing_variables(self, template: PromptTemplate) -> list[str]:
        declared = set(template.variables)
        found = set(re.findall(r"\{\{(\w+)\}\}", template.content))
        missing = found - declared
        return list(missing)

    def extract_variables(self, text: str) -> list[str]:
        return re.findall(r"\{\{(\w+)\}\}", text)
