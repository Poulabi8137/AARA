from __future__ import annotations

import pytest

from app.core.exceptions import RegistryError
from app.plugins.agent_registry import AgentRegistry, BaseAgent
from app.plugins.discovery import PluginLoader
from app.plugins.factory import AgentFactory, ToolFactory
from app.plugins.registration import RegistryValidator
from app.plugins.tool_registry import BaseTool, ToolRegistry
from app.plugins.workflow_registry import WorkflowRegistry


class FakeAgent(BaseAgent):
    agent_id = "fake_agent"
    agent_name = "Fake Agent"
    __version__ = "2.0"


class FakeTool(BaseTool):
    tool_id = "fake_tool"
    description = "A fake tool"


class TestAgentRegistry:
    def test_register_and_list(self):
        registry = AgentRegistry()
        registry.register()(FakeAgent)
        agents = registry.list_agents()
        assert len(agents) == 1
        assert agents[0].agent_id == "fake_agent"
        assert agents[0].version == "2.0"

    def test_get_creates_instance(self):
        registry = AgentRegistry()
        registry.register()(FakeAgent)
        instance = registry.get("fake_agent")
        assert isinstance(instance, FakeAgent)

    def test_get_returns_same_instance(self):
        registry = AgentRegistry()
        registry.register()(FakeAgent)
        assert registry.get("fake_agent") is registry.get("fake_agent")

    def test_get_not_found_raises(self):
        registry = AgentRegistry()
        with pytest.raises(RegistryError):
            registry.get("nonexistent")

    def test_register_twice_raises(self):
        registry = AgentRegistry()
        registry.register()(FakeAgent)
        with pytest.raises(RegistryError):
            registry.register()(FakeAgent)

    def test_get_class(self):
        registry = AgentRegistry()
        registry.register()(FakeAgent)
        cls = registry.get_class("fake_agent")
        assert cls is FakeAgent

    def test_get_metadata(self):
        registry = AgentRegistry()
        registry.register()(FakeAgent)
        meta = registry.get_metadata("fake_agent")
        assert meta.agent_id == "fake_agent"

    def test_contains(self):
        registry = AgentRegistry()
        registry.register()(FakeAgent)
        assert registry.contains("fake_agent") is True
        assert registry.contains("nonexistent") is False

    def test_clear_instances(self):
        registry = AgentRegistry()
        registry.register()(FakeAgent)
        registry.get("fake_agent")
        registry.clear_instances()


class TestToolRegistry:
    def test_register_and_list(self):
        registry = ToolRegistry()
        registry.register()(FakeTool)
        tools = registry.list_tools()
        assert len(tools) == 1
        assert tools[0].tool_id == "fake_tool"

    def test_get_tool(self):
        registry = ToolRegistry()
        registry.register()(FakeTool)
        cls = registry.get_tool("fake_tool")
        assert cls is FakeTool

    def test_get_tool_not_found(self):
        registry = ToolRegistry()
        with pytest.raises(RegistryError):
            registry.get_tool("nonexistent")

    def test_register_twice_raises(self):
        registry = ToolRegistry()
        registry.register()(FakeTool)
        with pytest.raises(RegistryError):
            registry.register()(FakeTool)

    def test_contains(self):
        registry = ToolRegistry()
        registry.register()(FakeTool)
        assert registry.contains("fake_tool") is True

    def test_get_metadata(self):
        registry = ToolRegistry()
        registry.register()(FakeTool)
        meta = registry.get_metadata("fake_tool")
        assert meta.tool_id == "fake_tool"


class TestWorkflowRegistry:
    def test_register_and_list(self):
        registry = WorkflowRegistry()
        registry.register("test_wf", agents=["a1", "a2"])(type("Handler", (), {}))
        workflows = registry.list_workflows()
        assert len(workflows) == 1
        assert workflows[0].workflow_type == "test_wf"

    def test_get_plan(self):
        registry = WorkflowRegistry()
        registry.register("test_wf", agents=["a1"])(type("Handler", (), {}))
        plan = registry.get_plan("test_wf")
        assert plan.workflow_type == "test_wf"
        assert "a1" in plan.agents

    def test_get_plan_not_found(self):
        registry = WorkflowRegistry()
        with pytest.raises(RegistryError):
            registry.get_plan("nonexistent")

    def test_register_twice_raises(self):
        registry = WorkflowRegistry()
        registry.register("tw")(type("H1", (), {}))
        with pytest.raises(RegistryError):
            registry.register("tw")(type("H2", (), {}))

    def test_contains(self):
        registry = WorkflowRegistry()
        registry.register("tw")(type("H", (), {}))
        assert registry.contains("tw") is True

    def test_unregister(self):
        registry = WorkflowRegistry()
        registry.register("tw")(type("H", (), {}))
        registry.unregister("tw")
        assert registry.contains("tw") is False


class TestAgentFactory:
    def test_create(self):
        registry = AgentRegistry()
        registry.register()(FakeAgent)
        factory = AgentFactory(registry)
        agent = factory.create("fake_agent")
        assert isinstance(agent, FakeAgent)

    def test_hooks(self):
        registry = AgentRegistry()
        registry.register()(FakeAgent)
        factory = AgentFactory(registry)
        hooks = []
        factory.register_pre_hook(lambda aid: hooks.append(f"pre:{aid}"))
        factory.register_post_hook(lambda aid, inst: hooks.append(f"post:{aid}"))
        factory.create("fake_agent")
        assert len(hooks) == 2


class TestToolFactory:
    def test_create(self):
        registry = ToolRegistry()
        registry.register()(FakeTool)
        factory = ToolFactory(registry)
        tool = factory.create("fake_tool")
        assert isinstance(tool, FakeTool)


class TestRegistryValidator:
    def test_validate_no_errors(self):
        validator = RegistryValidator()
        ar = AgentRegistry()
        tr = ToolRegistry()
        wr = WorkflowRegistry()
        errors = validator.validate(ar, tr, wr)
        assert errors == []

    def test_validate_unknown_agent_in_workflow(self):
        validator = RegistryValidator()
        ar = AgentRegistry()
        tr = ToolRegistry()
        wr = WorkflowRegistry()
        wr.register("test", agents=["nonexistent"])(type("H", (), {}))
        errors = validator.validate(ar, tr, wr)
        assert len(errors) == 1
        assert "nonexistent" in errors[0]


class TestPluginLoader:
    def test_load_plugins(self):
        loader = PluginLoader()
        result = loader.load_plugins()
        assert isinstance(result, list)

    def test_get_loaded(self):
        loader = PluginLoader()
        assert loader.get_loaded() == []

    def test_discover_local_plugins_no_dir(self):
        loader = PluginLoader()
        result = loader.discover_local_plugins("nonexistent_dir_12345")
        assert result == []
