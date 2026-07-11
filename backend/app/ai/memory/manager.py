from __future__ import annotations

from typing import Any

from app.ai.memory.global_memory import GlobalMemory
from app.ai.memory.session import SessionMemory
from app.ai.memory.workspace import WorkspaceMemory


class MemoryManager:
    def __init__(
        self,
        user_id: str,
        workspace_id: str | None = None,
        session_id: str | None = None,
    ) -> None:
        self.user_id = user_id
        self.workspace_id = workspace_id
        self.session_id = session_id
        self._session: SessionMemory | None = None
        self._workspace: WorkspaceMemory | None = None
        self._global: GlobalMemory | None = None

    async def get_session(self) -> SessionMemory:
        if self._session is None:
            self._session = SessionMemory(session_id=self.session_id or "default")
        return self._session

    async def get_workspace(self) -> WorkspaceMemory:
        if self._workspace is None:
            self._workspace = WorkspaceMemory(
                workspace_id=self.workspace_id or "default"
            )
        return self._workspace

    async def get_global(self) -> GlobalMemory:
        if self._global is None:
            self._global = GlobalMemory(user_id=self.user_id)
        return self._global

    async def clear_all(self) -> None:
        if self._session:
            await self._session.clear()
        if self._workspace:
            await self._workspace.clear()
        if self._global:
            await self._global.clear()

    async def snapshot_all(self) -> dict[str, Any]:
        return {
            "session": await (await self.get_session()).snapshot() if self._session else {},
            "workspace": await (await self.get_workspace()).snapshot() if self._workspace else {},
            "global": {},  # global memory excluded from snapshots
        }
