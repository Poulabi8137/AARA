from __future__ import annotations

import asyncio

from app.ai.memory.eviction import MemoryEvictionPolicy, MemoryEvictionStrategy
from app.ai.memory.global_memory import GlobalMemory
from app.ai.memory.manager import MemoryManager
from app.ai.memory.session import SessionMemory
from app.ai.memory.summarization import MemorySummarizer
from app.ai.memory.workspace import WorkspaceMemory


class TestSessionMemory:
    async def test_set_and_get(self):
        mem = SessionMemory("sess-1")
        await mem.set("key1", "value1")
        assert await mem.get("key1") == "value1"

    async def test_get_missing_key(self):
        mem = SessionMemory("sess-1")
        assert await mem.get("nonexistent") is None

    async def test_delete_existing_key(self):
        mem = SessionMemory("sess-1")
        await mem.set("key1", "value1")
        assert await mem.delete("key1") is True
        assert await mem.get("key1") is None

    async def test_delete_missing_key(self):
        mem = SessionMemory("sess-1")
        assert await mem.delete("nonexistent") is False

    async def test_push_and_pop_context(self):
        mem = SessionMemory("sess-1")
        await mem.push_context({"role": "user", "text": "hello"})
        await mem.push_context({"role": "assistant", "text": "hi"})
        popped = await mem.pop_context()
        assert popped == {"role": "assistant", "text": "hi"}
        remaining = await mem.get_context()
        assert remaining == [{"role": "user", "text": "hello"}]

    async def test_pop_empty_context_returns_none(self):
        mem = SessionMemory("sess-1")
        assert await mem.pop_context() is None

    async def test_get_context_returns_copy(self):
        mem = SessionMemory("sess-1")
        await mem.push_context({"role": "user", "text": "hello"})
        ctx = await mem.get_context()
        ctx.append({"role": "assistant", "text": "hi"})
        assert len(await mem.get_context()) == 1

    async def test_clear(self):
        mem = SessionMemory("sess-1")
        await mem.set("a", 1)
        await mem.push_context({"role": "user", "text": "hello"})
        await mem.clear()
        assert await mem.get("a") is None
        assert await mem.get_context() == []

    async def test_snapshot_and_restore(self):
        mem = SessionMemory("sess-1")
        await mem.set("key1", "val1")
        await mem.push_context({"role": "user", "text": "hello"})
        snap = await mem.snapshot()
        assert snap["session_id"] == "sess-1"
        assert snap["store"] == {"key1": "val1"}
        assert snap["context_stack"] == [{"role": "user", "text": "hello"}]

        await mem.set("key2", "val2")
        await mem.restore(snap)
        assert await mem.get("key1") == "val1"
        assert await mem.get("key2") is None
        assert await mem.get_context() == [{"role": "user", "text": "hello"}]

    async def test_size(self):
        mem = SessionMemory("sess-1")
        await mem.set("a", "b")
        size = await mem.size()
        assert isinstance(size, int)
        assert size > 0

    async def test_keys(self):
        mem = SessionMemory("sess-1")
        await mem.set("x", 1)
        await mem.set("y", 2)
        assert sorted(await mem.keys()) == ["x", "y"]

    async def test_keys_empty(self):
        mem = SessionMemory("sess-1")
        assert await mem.keys() == []

    async def test_lock_is_asyncio_lock(self):
        mem = SessionMemory("sess-1")
        import asyncio
        assert isinstance(mem._lock, asyncio.Lock)

    async def test_concurrent_set_and_get(self):
        mem = SessionMemory("sess-1")

        async def writer(k, v):
            await mem.set(k, v)

        await asyncio.gather(writer("a", 1), writer("b", 2), writer("c", 3))
        assert await mem.get("a") == 1
        assert await mem.get("b") == 2
        assert await mem.get("c") == 3

    async def test_restore_with_partial_snapshot(self):
        mem = SessionMemory("sess-1")
        await mem.restore({"store": {"a": 1}})
        assert await mem.get("a") == 1
        assert await mem.get_context() == []


class TestWorkspaceMemory:
    async def test_store_and_retrieve(self):
        ws = WorkspaceMemory("ws-1")
        await ws.store("key1", {"data": "test"})
        assert await ws.retrieve("key1") == {"data": "test"}

    async def test_retrieve_missing(self):
        ws = WorkspaceMemory("ws-1")
        assert await ws.retrieve("missing") is None

    async def test_delete_existing(self):
        ws = WorkspaceMemory("ws-1")
        await ws.store("k", "v")
        assert await ws.delete("k") is True
        assert await ws.retrieve("k") is None

    async def test_delete_missing(self):
        ws = WorkspaceMemory("ws-1")
        assert await ws.delete("missing") is False

    async def test_add_and_get_papers(self):
        ws = WorkspaceMemory("ws-1")
        p1 = {"id": "p1", "title": "Paper 1"}
        p2 = {"id": "p2", "title": "Paper 2"}
        await ws.add_paper(p1)
        await ws.add_paper(p2)
        papers = await ws.get_papers()
        assert papers == [p1, p2]

    async def test_get_papers_with_limit_and_offset(self):
        ws = WorkspaceMemory("ws-1")
        for i in range(10):
            await ws.add_paper({"id": f"p{i}"})
        assert len(await ws.get_papers(limit=3)) == 3
        assert len(await ws.get_papers(limit=5, offset=5)) == 5
        assert await ws.get_papers(limit=3, offset=9) == [{"id": "p9"}]

    async def test_get_papers_empty(self):
        ws = WorkspaceMemory("ws-1")
        assert await ws.get_papers() == []

    async def test_add_and_get_analyses(self):
        ws = WorkspaceMemory("ws-1")
        a1 = {"id": "a1", "type": "summary", "content": "sum"}
        a2 = {"id": "a2", "type": "review", "content": "rev"}
        await ws.add_analysis(a1)
        await ws.add_analysis(a2)
        assert len(await ws.get_analyses()) == 2

    async def test_get_analyses_filter_by_type(self):
        ws = WorkspaceMemory("ws-1")
        await ws.add_analysis({"id": "a1", "type": "summary"})
        await ws.add_analysis({"id": "a2", "type": "review"})
        await ws.add_analysis({"id": "a3", "type": "summary"})
        results = await ws.get_analyses(analysis_type="summary")
        assert len(results) == 2
        assert all(a["type"] == "summary" for a in results)

    async def test_get_analyses_filter_no_match(self):
        ws = WorkspaceMemory("ws-1")
        await ws.add_analysis({"id": "a1", "type": "summary"})
        assert await ws.get_analyses(analysis_type="nonexistent") == []

    async def test_get_analyses_returns_copy(self):
        ws = WorkspaceMemory("ws-1")
        await ws.add_analysis({"id": "a1"})
        result = await ws.get_analyses()
        result.append({"id": "a2"})
        assert len(await ws.get_analyses()) == 1

    async def test_clear(self):
        ws = WorkspaceMemory("ws-1")
        await ws.store("k", "v")
        await ws.add_paper({"id": "p1"})
        await ws.add_analysis({"id": "a1"})
        await ws.clear()
        assert await ws.retrieve("k") is None
        assert await ws.get_papers() == []
        assert await ws.get_analyses() == []

    async def test_snapshot(self):
        ws = WorkspaceMemory("ws-1")
        await ws.store("k", "v")
        await ws.add_paper({"id": "p1"})
        snap = await ws.snapshot()
        assert snap["workspace_id"] == "ws-1"
        assert snap["store"] == {"k": "v"}
        assert snap["papers"] == [{"id": "p1"}]


class TestGlobalMemory:
    async def test_save_and_get_prompt_template(self):
        gm = GlobalMemory("user-1")
        await gm.save_prompt_template("greeting", "Hello {{name}}")
        assert await gm.get_prompt_template("greeting") == "Hello {{name}}"

    async def test_get_missing_prompt_template(self):
        gm = GlobalMemory("user-1")
        assert await gm.get_prompt_template("missing") is None

    async def test_delete_prompt_template_existing(self):
        gm = GlobalMemory("user-1")
        await gm.save_prompt_template("t1", "template1")
        assert await gm.delete_prompt_template("t1") is True
        assert await gm.get_prompt_template("t1") is None

    async def test_delete_prompt_template_missing(self):
        gm = GlobalMemory("user-1")
        assert await gm.delete_prompt_template("missing") is False

    async def test_record_and_get_execution_patterns(self):
        gm = GlobalMemory("user-1")
        await gm.record_execution_pattern("agent-1", {"action": "search"})
        await gm.record_execution_pattern("agent-1", {"action": "analyze"})
        patterns = await gm.get_execution_patterns()
        assert len(patterns) == 2

    async def test_get_execution_patterns_filter_by_agent(self):
        gm = GlobalMemory("user-1")
        await gm.record_execution_pattern("agent-1", {"action": "search"})
        await gm.record_execution_pattern("agent-2", {"action": "review"})
        await gm.record_execution_pattern("agent-1", {"action": "analyze"})
        results = await gm.get_execution_patterns(agent_id="agent-1")
        assert len(results) == 2
        assert all(p["agent_id"] == "agent-1" for p in results)

    async def test_get_execution_patterns_filter_no_match(self):
        gm = GlobalMemory("user-1")
        await gm.record_execution_pattern("agent-1", {"action": "search"})
        assert await gm.get_execution_patterns(agent_id="missing") == []

    async def test_store_and_retrieve(self):
        gm = GlobalMemory("user-1")
        await gm.store("config", {"model": "gpt-4"})
        assert await gm.retrieve("config") == {"model": "gpt-4"}

    async def test_retrieve_missing(self):
        gm = GlobalMemory("user-1")
        assert await gm.retrieve("missing") is None

    async def test_clear(self):
        gm = GlobalMemory("user-1")
        await gm.store("k", "v")
        await gm.save_prompt_template("t1", "tpl")
        await gm.record_execution_pattern("a1", {})
        await gm.clear()
        assert await gm.retrieve("k") is None
        assert await gm.get_prompt_template("t1") is None
        assert await gm.get_execution_patterns() == []


class TestMemoryManager:
    async def test_get_session_lazy_init(self):
        mgr = MemoryManager(user_id="u1", session_id="s1")
        session = await mgr.get_session()
        assert isinstance(session, SessionMemory)
        assert session.session_id == "s1"

    async def test_get_session_default_id(self):
        mgr = MemoryManager(user_id="u1")
        session = await mgr.get_session()
        assert session.session_id == "default"

    async def test_get_session_cached(self):
        mgr = MemoryManager(user_id="u1")
        s1 = await mgr.get_session()
        s2 = await mgr.get_session()
        assert s1 is s2

    async def test_get_workspace_lazy_init(self):
        mgr = MemoryManager(user_id="u1", workspace_id="w1")
        ws = await mgr.get_workspace()
        assert isinstance(ws, WorkspaceMemory)
        assert ws.workspace_id == "w1"

    async def test_get_workspace_default_id(self):
        mgr = MemoryManager(user_id="u1")
        ws = await mgr.get_workspace()
        assert ws.workspace_id == "default"

    async def test_get_workspace_cached(self):
        mgr = MemoryManager(user_id="u1")
        w1 = await mgr.get_workspace()
        w2 = await mgr.get_workspace()
        assert w1 is w2

    async def test_get_global_lazy_init(self):
        mgr = MemoryManager(user_id="u1")
        gm = await mgr.get_global()
        assert isinstance(gm, GlobalMemory)
        assert gm.user_id == "u1"

    async def test_get_global_cached(self):
        mgr = MemoryManager(user_id="u1")
        g1 = await mgr.get_global()
        g2 = await mgr.get_global()
        assert g1 is g2

    async def test_store_and_retrieve_across_all(self):
        mgr = MemoryManager(user_id="u1")
        session = await mgr.get_session()
        ws = await mgr.get_workspace()
        gm = await mgr.get_global()

        await session.set("sk", "sv")
        await ws.store("wk", "wv")
        await gm.store("gk", "gv")

        assert await session.get("sk") == "sv"
        assert await ws.retrieve("wk") == "wv"
        assert await gm.retrieve("gk") == "gv"

    async def test_clear_all(self):
        mgr = MemoryManager(user_id="u1")
        session = await mgr.get_session()
        ws = await mgr.get_workspace()
        gm = await mgr.get_global()

        await session.set("k", "v")
        await ws.store("k", "v")
        await gm.store("k", "v")

        await mgr.clear_all()

        assert await session.get("k") is None
        assert await ws.retrieve("k") is None
        assert await gm.retrieve("k") is None

    async def test_clear_all_no_instances_does_not_raise(self):
        mgr = MemoryManager(user_id="u1")
        await mgr.clear_all()

    async def test_snapshot_all(self):
        mgr = MemoryManager(user_id="u1")
        session = await mgr.get_session()
        ws = await mgr.get_workspace()

        await session.set("sk", "sv")
        await ws.store("wk", "wv")

        snap = await mgr.snapshot_all()
        assert "session" in snap
        assert "workspace" in snap
        assert "global" in snap

    async def test_snapshot_all_no_prior_instances_creates_them(self):
        mgr = MemoryManager(user_id="u1")
        snap = await mgr.snapshot_all()
        assert "session" in snap
        assert "workspace" in snap
        assert "global" in snap

    async def test_manager_stores_ids(self):
        mgr = MemoryManager(user_id="u1", workspace_id="w1", session_id="s1")
        assert mgr.user_id == "u1"
        assert mgr.workspace_id == "w1"
        assert mgr.session_id == "s1"


class TestMemoryEvictionStrategy:
    def test_default_policy_is_lru(self):
        strategy = MemoryEvictionStrategy()
        assert strategy.policy == MemoryEvictionPolicy.LRU
        assert strategy.max_entries == 1000

    def test_fifo_policy(self):
        strategy = MemoryEvictionStrategy(policy=MemoryEvictionPolicy.FIFO)
        assert strategy.policy == MemoryEvictionPolicy.FIFO

    def test_lru_policy(self):
        strategy = MemoryEvictionStrategy(policy=MemoryEvictionPolicy.LRU)
        assert strategy.policy == MemoryEvictionPolicy.LRU

    def test_should_evict_when_exceeds_max(self):
        strategy = MemoryEvictionStrategy(max_entries=5)
        assert strategy.should_evict(10) is True

    def test_should_not_evict_when_equal(self):
        strategy = MemoryEvictionStrategy(max_entries=5)
        assert strategy.should_evict(5) is False

    def test_should_not_evict_when_under(self):
        strategy = MemoryEvictionStrategy(max_entries=5)
        assert strategy.should_evict(3) is False

    def test_record_access_appends_key(self):
        strategy = MemoryEvictionStrategy()
        strategy.record_access("a")
        strategy.record_access("b")
        assert strategy._access_order == ["a", "b"]

    def test_record_access_moves_existing_to_end(self):
        strategy = MemoryEvictionStrategy()
        strategy.record_access("a")
        strategy.record_access("b")
        strategy.record_access("a")
        assert strategy._access_order == ["b", "a"]

    def test_get_eviction_candidates_no_excess(self):
        strategy = MemoryEvictionStrategy(max_entries=10)
        store = {"a": 1, "b": 2}
        assert strategy.get_eviction_candidates(store) == []

    def test_get_eviction_candidates_lru(self):
        strategy = MemoryEvictionStrategy(policy=MemoryEvictionPolicy.LRU, max_entries=2)
        strategy.record_access("a")
        strategy.record_access("b")
        strategy.record_access("c")
        store = {"a": 1, "b": 2, "c": 3}
        candidates = strategy.get_eviction_candidates(store)
        assert len(candidates) == 1
        assert candidates[0] in ("a",)

    def test_get_eviction_candidates_fifo(self):
        strategy = MemoryEvictionStrategy(policy=MemoryEvictionPolicy.FIFO, max_entries=2)
        store = {"a": 1, "b": 2, "c": 3}
        candidates = strategy.get_eviction_candidates(store)
        assert len(candidates) == 1
        assert candidates[0] == "a"

    def test_get_eviction_candidates_fifo_multiple(self):
        strategy = MemoryEvictionStrategy(policy=MemoryEvictionPolicy.FIFO, max_entries=1)
        store = {"a": 1, "b": 2, "c": 3}
        candidates = strategy.get_eviction_candidates(store)
        assert len(candidates) == 2
        assert candidates == ["a", "b"]

    async def test_evict_removes_correct_entries(self):
        strategy = MemoryEvictionStrategy(policy=MemoryEvictionPolicy.FIFO, max_entries=1)
        store = {"a": 1, "b": 2, "c": 3}
        removed = await strategy.evict(store)
        assert removed == 2
        assert len(store) == 1
        assert "a" not in store
        assert "b" not in store

    async def test_evict_no_excess(self):
        strategy = MemoryEvictionStrategy(max_entries=10)
        store = {"a": 1}
        removed = await strategy.evict(store)
        assert removed == 0
        assert store == {"a": 1}

    async def test_evict_with_memory_type_param(self):
        strategy = MemoryEvictionStrategy(policy=MemoryEvictionPolicy.FIFO, max_entries=1)
        store = {"a": 1, "b": 2}
        removed = await strategy.evict(store, memory_type="workspace")
        assert removed == 1
        assert "a" not in store


class TestMemorySummarizer:
    async def test_summarize_session(self):
        summarizer = MemorySummarizer()
        memory = {"store": {"k1": "v1", "k2": "v2"}, "context_stack": [{"role": "user", "text": "hi"}]}
        summary = await summarizer.summarize_session(memory)
        assert "2 stored keys" in summary
        assert "1 context entries" in summary

    async def test_summarize_session_empty(self):
        summarizer = MemorySummarizer()
        memory = {"store": {}, "context_stack": []}
        summary = await summarizer.summarize_session(memory)
        assert "0 stored keys" in summary

    async def test_summarize_session_respects_max_length(self):
        summarizer = MemorySummarizer(max_summary_length=10)
        memory = {"store": {f"k{i}": "v" for i in range(100)}, "context_stack": []}
        summary = await summarizer.summarize_session(memory)
        assert len(summary) <= 10

    async def test_summarize_workspace(self):
        summarizer = MemorySummarizer()
        memory = {"store": {"k": "v"}, "papers": [{"id": "p1"}], "analyses": [{"id": "a1"}]}
        summary = await summarizer.summarize_workspace(memory)
        assert "1 stored keys" in summary
        assert "1 papers" in summary
        assert "1 analyses" in summary

    async def test_summarize_workspace_empty(self):
        summarizer = MemorySummarizer()
        memory = {"store": {}, "papers": [], "analyses": []}
        summary = await summarizer.summarize_workspace(memory)
        assert "0 stored keys" in summary

    async def test_generate_summary_session_context(self):
        summarizer = MemorySummarizer()
        data = {"store": {"a": 1}, "context_stack": []}
        summary = await summarizer.generate_summary(data, context="session")
        assert "stored keys" in summary
        assert "context entries" in summary

    async def test_generate_summary_workspace_context(self):
        summarizer = MemorySummarizer()
        data = {"store": {}, "papers": [], "analyses": []}
        summary = await summarizer.generate_summary(data, context="workspace")
        assert "Workspace" in summary

    async def test_generate_summary_default_context(self):
        summarizer = MemorySummarizer()
        data = {"a": 1, "b": 2}
        summary = await summarizer.generate_summary(data, context="other")
        assert "Memory snapshot" in summary
        assert "2 top-level keys" in summary

    async def test_generate_summary_empty_data(self):
        summarizer = MemorySummarizer()
        summary = await summarizer.generate_summary({}, context="session")
        assert "0 stored keys" in summary

    async def test_default_max_summary_length(self):
        summarizer = MemorySummarizer()
        assert summarizer._max_length == 500

    async def test_custom_max_summary_length(self):
        summarizer = MemorySummarizer(max_summary_length=100)
        assert summarizer._max_length == 100
