from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.exceptions import RegistryError


@dataclass
class ToolMetadata:
    tool_id: str
    description: str = ""
    requires_auth: bool = False
    rate_limit: int = 0


class BaseTool:
    tool_id: str = ""
    description: str = ""
    requires_auth: bool = False
    rate_limit: int = 0


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, type[BaseTool]] = {}
        self._metadata: dict[str, ToolMetadata] = {}

    def register(self, tool_id: str | None = None) -> Any:
        def decorator(cls: type[BaseTool]) -> type[BaseTool]:
            tid = tool_id or getattr(cls, "tool_id", None)
            if not tid:
                msg = f"Tool class {cls.__name__} must define tool_id"
                raise RegistryError(msg)
            if tid in self._tools:
                raise RegistryError(f"Tool '{tid}' already registered")
            self._tools[tid] = cls
            self._metadata[tid] = ToolMetadata(
                tool_id=tid,
                description=getattr(cls, "description", ""),
                requires_auth=getattr(cls, "requires_auth", False),
                rate_limit=getattr(cls, "rate_limit", 0),
            )
            return cls
        return decorator

    def get_tool(self, tool_id: str) -> type[BaseTool]:
        tool = self._tools.get(tool_id)
        if not tool:
            raise RegistryError(f"Tool '{tool_id}' not registered")
        return tool

    def list_tools(self) -> list[ToolMetadata]:
        return list(self._metadata.values())

    def get_metadata(self, tool_id: str) -> ToolMetadata:
        meta = self._metadata.get(tool_id)
        if not meta:
            raise RegistryError(f"Tool '{tool_id}' not found")
        return meta

    def contains(self, tool_id: str) -> bool:
        return tool_id in self._tools
