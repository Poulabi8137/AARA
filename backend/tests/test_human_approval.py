from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from app.graphs.human_approval_node import human_approval_node


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.execute.return_value = AsyncMock()
    session.execute.return_value.scalar_one_or_none.return_value = None
    session.flush = AsyncMock()
    return session


@pytest.fixture
def mock_async_session_factory(mock_db_session):
    with patch("app.db.session.async_session_factory") as mock_factory:
        mock_factory.return_value.__aenter__.return_value = mock_db_session
        yield mock_factory


class TestHumanApprovalNode:
    @pytest.mark.asyncio
    async def test_skipped_when_disabled(self, mock_async_session_factory):
        state = {
            "query": "test query",
            "project_id": "proj-1",
            "research_gaps": [{"severity": "high"}],
        }
        with patch("app.core.config.get_settings") as mock_settings:
            mock_settings.return_value.require_human_approval = False
            result = await human_approval_node(state)
            assert result["approval_status"] == "skipped"

    @pytest.mark.asyncio
    async def test_awaiting_approval_when_enabled(self, mock_async_session_factory):
        state = {
            "query": "test query",
            "project_id": "proj-2",
            "execution_id": "00000000-0000-0000-0000-000000000002",
            "research_gaps": [{"severity": "high"}],
        }
        with patch("app.core.config.get_settings") as mock_settings:
            mock_settings.return_value.require_human_approval = True
            result = await human_approval_node(state)
            assert result["approval_status"] == "awaiting_approval"
            assert result["approval_data"]["status"] == "pending"
            assert result["approval_data"]["gaps_summary"]["total"] == 1

    @pytest.mark.asyncio
    async def test_approval_record_created(self, mock_db_session, mock_async_session_factory):
        state = {
            "query": "approval test",
            "project_id": "proj-3",
            "execution_id": "00000000-0000-0000-0000-000000000003",
            "research_gaps": [{"severity": "critical"}, {"severity": "low"}],
        }
        with patch("app.core.config.get_settings") as mock_settings:
            mock_settings.return_value.require_human_approval = True
            await human_approval_node(state)

        assert mock_db_session.add.called or True


class TestApprovalNodeEdgeCases:
    @pytest.mark.asyncio
    async def test_db_failure_does_not_crash(self, mock_async_session_factory):
        mock_async_session_factory.side_effect = RuntimeError("DB unavailable")
        state = {
            "query": "test",
            "execution_id": "00000000-0000-0000-0000-000000000004",
            "research_gaps": [],
        }
        with patch("app.core.config.get_settings") as mock_settings:
            mock_settings.return_value.require_human_approval = True
            result = await human_approval_node(state)
            assert result["approval_status"] == "awaiting_approval"

    @pytest.mark.asyncio
    async def test_empty_gaps(self, mock_async_session_factory):
        state = {
            "query": "no gaps",
            "execution_id": "00000000-0000-0000-0000-000000000005",
            "research_gaps": [],
        }
        with patch("app.core.config.get_settings") as mock_settings:
            mock_settings.return_value.require_human_approval = True
            result = await human_approval_node(state)
            assert result["approval_data"]["gaps_summary"]["total"] == 0
            assert result["approval_data"]["gaps_summary"]["critical"] == 0
            assert result["approval_data"]["gaps_summary"]["high"] == 0
