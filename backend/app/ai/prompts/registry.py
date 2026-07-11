from __future__ import annotations

from app.ai.prompts.templates import PromptRole, PromptTemplate, PromptVersion


class PromptRegistry:
    def __init__(self) -> None:
        self._templates: dict[str, PromptTemplate] = {}
        self._active_versions: dict[str, str] = {}

    def register(self, template: PromptTemplate) -> None:
        self._templates[template.name] = template
        if template.name not in self._active_versions:
            self._active_versions[template.name] = "v1"

    def get(self, name: str) -> PromptTemplate | None:
        return self._templates.get(name)

    def get_rendered(
        self, name: str, version: str | None = None, **variables: str
    ) -> str | None:
        template = self._templates.get(name)
        if not template:
            return None
        ver = version or self._active_versions.get(name, "v1")
        version_obj = template.get_version(ver)
        if version_obj:
            result = version_obj.content
            for key, value in variables.items():
                result = result.replace(f"{{{{{key}}}}}", str(value))
            return result
        return template.render(**variables)

    def set_active_version(self, name: str, version: str) -> None:
        self._active_versions[name] = version

    def list_templates(self) -> list[str]:
        return list(self._templates.keys())

    def delete(self, name: str) -> None:
        self._templates.pop(name, None)
        self._active_versions.pop(name, None)

    def register_from_dict(
        self, name: str, content: str, role: PromptRole = PromptRole.SYSTEM
    ) -> None:
        template = PromptTemplate(name=name, role=role, content=content)
        template.add_version(PromptVersion(version="v1", content=content))
        self.register(template)
