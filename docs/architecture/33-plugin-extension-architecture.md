# Document 33 — Plugin & Extension Architecture

## Design Goal

New agents, tools, providers, and workflow types can be added with zero changes to existing code — only imports and registration.

## Registry Architecture

```
Extension Point           Registry             Registration
────────────────────────────────────────────────────────────
Agent                     AgentRegistry        @agent.register("custom")
Tool                      ToolRegistry         @tool.register("custom_tool")
LLM Provider              ProviderRegistry     @provider.register("custom_llm")
Embedding Provider        EmbedderRegistry     @embedder.register("custom_embedder")
Research Provider         ResearchRegistry     @research.register("custom_api")
Vector DB Provider        VectorDBRegistry     @vectordb.register("custom_db")
Storage Provider          StorageRegistry      @storage.register("custom_store")
Workflow Type             WorkflowRegistry     @workflow.register("custom_workflow")
MCP Tool                  MCPToolRegistry      @mcp.register("custom_mcp")
Export Format             ExportRegistry       @exporter.register("custom_format")
Metric                    MetricRegistry       @metric.register("custom_metric")
```

### Agent Registry

```python
class AgentRegistry:
    """Central registry for all agent types."""

    def __init__(self):
        self._agents: dict[str, type[BaseAgent]] = {}
        self._instances: dict[str, BaseAgent] = {}

    def register(self, agent_id: str = None):
        """Decorator: register an agent class."""
        def decorator(cls: type[BaseAgent]) -> type[BaseAgent]:
            aid = agent_id or cls.agent_id
            if aid in self._agents:
                raise RegistryError(f"Agent '{aid}' already registered")
            self._agents[aid] = cls
            return cls
        return decorator

    def get(self, agent_id: str) -> BaseAgent:
        """Get or create an agent instance (lazy singleton per workflow)."""
        if agent_id not in self._instances:
            cls = self._agents.get(agent_id)
            if not cls:
                raise RegistryError(f"Agent '{agent_id}' not found")
            self._instances[agent_id] = cls()
        return self._instances[agent_id]

    def list_agents(self) -> list[AgentMetadata]:
        return [
            AgentMetadata(id=aid, name=cls.agent_name, version=getattr(cls, "__version__", "1.0"))
            for aid, cls in self._agents.items()
        ]

    def clear_instances(self):
        """Clear per-workflow instances after workflow completes."""
        self._instances.clear()


# Usage
@agent.register()
class CustomResearcher(BaseAgent):
    agent_id = "custom_researcher"
    agent_name = "Custom Researcher"
    __version__ = "2.0"

    async def execute(self, context: AgentContext) -> AgentOutput:
        ...
```

### Tool Registry

```python
class ToolRegistry:
    """Central registry for all tools available to agents."""

    def __init__(self):
        self._tools: dict[str, type[BaseTool]] = {}

    def register(self, tool_id: str = None):
        def decorator(cls: type[BaseTool]) -> type[BaseTool]:
            tid = tool_id or cls.tool_id
            self._tools[tid] = cls
            return cls
        return decorator

    def get_tool(self, tool_id: str) -> type[BaseTool]:
        tool = self._tools.get(tool_id)
        if not tool:
            raise RegistryError(f"Tool '{tool_id}' not registered")
        return tool

    def list_tools(self) -> list[ToolMetadata]:
        return [
            ToolMetadata(id=tid, description=cls.__doc__)
            for tid, cls in self._tools.items()
        ]


@tool.register()
class SemanticScholarTool(BaseTool):
    tool_id = "semantic_scholar_search"
    description = "Search Semantic Scholar for academic papers"
    requires_auth = False
    rate_limit = 100  # requests per minute
```

### Provider Registry

```python
class ProviderRegistry:
    """Registry for LLM providers with dynamic selection."""

    def __init__(self):
        self._providers: dict[str, type[BaseProvider]] = {}

    def register(self, provider_id: str = None):
        def decorator(cls: type[BaseProvider]) -> type[BaseProvider]:
            pid = provider_id or cls.provider_id
            self._providers[pid] = cls
            return cls
        return decorator

    def get_provider(self, provider_id: str, config: ProviderConfig) -> BaseProvider:
        cls = self._providers.get(provider_id)
        if not cls:
            raise RegistryError(f"Provider '{provider_id}' not found")
        return cls(config=config)

    def get_available(self) -> list[str]:
        return list(self._providers.keys())
```

### Workflow Registry

```python
class WorkflowRegistry:
    """Registry for workflow types (execution plans)."""

    def __init__(self):
        self._workflows: dict[str, WorkflowDefinition] = {}

    def register(self, workflow_type: str, description: str = "", agents: list[str] = None):
        def decorator(cls: type) -> type:
            self._workflows[workflow_type] = WorkflowDefinition(
                workflow_type=workflow_type,
                description=description,
                agents=agents or [],
                handler=cls,
            )
            return cls
        return decorator

    def get_plan(self, workflow_type: str) -> WorkflowDefinition:
        wf = self._workflows.get(workflow_type)
        if not wf:
            raise RegistryError(f"Workflow '{workflow_type}' not registered")
        return wf


@workflow.register("literature_review", description="Full literature review with gap analysis",
                    agents=["planner", "researcher", "analyst"])
class LiteratureReviewWorkflow:
    """Execution plan for a literature review workflow."""
    async def create_plan(self, query: str) -> ExecutionPlan:
        return ExecutionPlan(steps=[
            Step(agent_id="researcher", input={"query": query}),
            Step(agent_id="analyst", input={}),
        ])
```

## Registration Lifecycle

```
1. Import time:    @register decorator runs → class stored in registry dict
2. Startup:        registry.list_*() validates all registrations are consistent
3. Runtime:        registry.get() creates lazy instance for each workflow
4. Shutdown:       registry.clear_instances() releases per-workflow instances
```

```python
class RegistryValidator:
    """Validates all registrations at startup."""

    def validate(self, agent_registry: AgentRegistry,
                 tool_registry: ToolRegistry,
                 workflow_registry: WorkflowRegistry) -> list[str]:
        errors = []

        # All workflow agents must exist
        for wf_type, wf_def in workflow_registry._workflows.items():
            for agent_id in wf_def.agents:
                try:
                    agent_registry.get(agent_id)
                except RegistryError:
                    errors.append(f"Workflow '{wf_type}' references unknown agent '{agent_id}'")

        # All tool IDs must be unique
        tool_ids = list(tool_registry._tools.keys())
        if len(tool_ids) != len(set(tool_ids)):
            errors.append("Duplicate tool IDs detected")

        return errors
```

## Dependency Injection

The system uses FastAPI's built-in dependency injection for services, with a manual DI container for non-HTTP contexts (agents, background jobs).

```python
class ServiceContainer:
    """Simple DI container for agent and workflow contexts."""

    def __init__(self):
        self._services: dict[str, Any] = {}
        self._factories: dict[str, Callable] = {}

    def register_singleton(self, key: str, instance: Any):
        self._services[key] = instance

    def register_factory(self, key: str, factory: Callable):
        self._factories[key] = factory

    def resolve(self, key: str) -> Any:
        if key in self._services:
            return self._services[key]
        factory = self._factories.get(key)
        if factory:
            instance = factory()
            self._services[key] = instance
            return instance
        raise RegistryError(f"Service '{key}' not registered")


# Setup at application startup
container = ServiceContainer()
container.register_singleton("db", engine)
container.register_singleton("qdrant", qdrant_client)
container.register_factory("tool_router", ToolRouter)
container.register_factory("event_bus", EventBus)
```

## Factory Pattern

Used wherever multiple implementation variants exist behind a common interface.

```python
class EmbedderFactory:
    """Creates embedder instances based on model_id."""

    _registry: dict[str, type[BaseEmbedder]] = {}

    @classmethod
    def register(cls, model_id: str):
        def decorator(embedder_cls: type[BaseEmbedder]):
            cls._registry[model_id] = embedder_cls
            return embedder_cls
        return decorator

    @classmethod
    def create(cls, model_id: str, **kwargs) -> BaseEmbedder:
        embedder_cls = cls._registry.get(model_id)
        if not embedder_cls:
            raise ValueError(f"No embedder registered for model '{model_id}'")
        return embedder_cls(**kwargs)


# Usage
@EmbedderFactory.register("sentence-transformers/all-MiniLM-L6-v2")
class MiniLMEmbedder(BaseEmbedder):
    ...

embedder = EmbedderFactory.create("sentence-transformers/all-MiniLM-L6-v2")
```

## Strategy Pattern

Used for algorithms that vary at runtime.

```python
class DedupStrategy(ABC):
    """Strategy interface for paper deduplication algorithms."""

    @abstractmethod
    async def deduplicate(self, papers: list[Paper]) -> list[Paper]: ...

class DOIDedupStrategy(DedupStrategy):
    """Fast: exact DOI match only."""

    async def deduplicate(self, papers: list[Paper]) -> list[Paper]:
        seen: set[str] = set()
        result = []
        for p in papers:
            if p.doi and p.doi not in seen:
                seen.add(p.doi)
                result.append(p)
        return result

class FullDedupStrategy(DedupStrategy):
    """Full: DOI + title similarity + author+year."""

    async def deduplicate(self, papers: list[Paper]) -> list[Paper]:
        # Multi-pass dedup
        ...

class DedupService:
    """Uses strategy pattern to switch between dedup algorithms."""

    def __init__(self, strategy: DedupStrategy = FullDedupStrategy()):
        self._strategy = strategy

    async def deduplicate(self, papers: list[Paper]) -> list[Paper]:
        return await self._strategy.deduplicate(papers)
```

## Extension Guidelines

### Adding a New Agent

```python
# 1. Create the agent class
@agent.register()
class MyNewAgent(BaseAgent):
    agent_id = "my_agent"
    agent_name = "My Custom Agent"
    __version__ = "1.0"
    max_retries = 3

    async def execute(self, context: AgentContext) -> MyAgentOutput:
        ...

# 2. (Optional) Register a workflow that uses it
@workflow.register("custom_workflow", agents=["planner", "my_agent"])
class CustomWorkflow:
    ...

# 3. No other code changes needed
```

### Adding a New LLM Provider

```python
@provider.register("custom_llm")
class CustomLLMProvider(BaseProvider):
    provider_id = "custom_llm"
    model = "custom-model"
    max_context_tokens = 32000

    async def infer(self, messages: list[dict], **kwargs) -> InferenceResponse:
        ...
```

### Adding a New Tool

```python
@tool.register()
class MyCustomTool(BaseTool):
    tool_id = "my_custom_tool"
    description = "Does something useful"

    async def execute(self, params: dict) -> ToolResult:
        ...
```

### Adding a New Export Format

```python
@exporter.register("my_format")
class MyFormatExporter(BaseExporter):
    exporter_id = "my_format"
    exporter_name = "My Format"

    async def export(self, draft: PaperDraft, **kwargs) -> ExportResult:
        ...
```

## Version Compatibility

```python
class VersionedRegistry:
    """Registry that tracks version compatibility."""

    API_VERSION = "1.0"

    def __init__(self):
        self._entries: dict[str, RegistryEntry] = {}

    def register(self, key: str, version: str = "1.0", min_api_version: str = "1.0"):
        def decorator(cls):
            if self._is_compatible(min_api_version):
                self._entries[key] = RegistryEntry(
                    cls=cls, version=version, min_api_version=min_api_version
                )
            return cls
        return decorator

    def _is_compatible(self, min_api_version: str) -> bool:
        """Check if the extension's minimum API version is satisfied."""
        return tuple(map(int, min_api_version.split("."))) <= tuple(map(int, self.API_VERSION.split(".")))
```

## Plugin Discovery

```python
class PluginLoader:
    """Discovers and loads plugins from installed packages."""

    PLUGIN_ENTRY_POINT = "aara.plugins"

    def load_plugins(self):
        """Load all installed AARA plugins via entry points."""
        import importlib.metadata
        plugins = importlib.metadata.entry_points(group=self.PLUGIN_ENTRY_POINT)
        for plugin in plugins:
            try:
                plugin.load()
                logger.info(f"Loaded plugin: {plugin.name}")
            except Exception as e:
                logger.error(f"Failed to load plugin {plugin.name}: {e}")

    def discover_local_plugins(self, plugin_dir: str = "plugins"):
        """Discover plugins from a local directory (development)."""
        import importlib.util
        from pathlib import Path
        plugin_path = Path(plugin_dir)
        if plugin_path.exists():
            for pyfile in plugin_path.glob("*.py"):
                spec = importlib.util.spec_from_file_location(pyfile.stem, pyfile)
                if spec and spec.loader:
                    spec.loader.exec_module(importlib.util.module_from_spec(spec))
```

## Backward Compatibility Policy

| Change Type | Compatible? | Mechanism |
|---|---|---|
| Add new agent | ✅ Yes | Registry auto-discovers; no existing code affected |
| Add new tool | ✅ Yes | Tool Registry iteration unchanged |
| Add new provider | ✅ Yes | Provider Router selects by availability |
| Add new metric | ✅ Yes | New metric registered; old metrics unchanged |
| Remove agent | ❌ No | Remove from registry; update workflows that reference it |
| Change agent input schema | ⚠️ Minor | New fields must be optional with defaults |
| Change tool output schema | ⚠️ Minor | New fields must be optional; old clients ignore extras |
| Rename registry key | ❌ No | Deprecate old key, add new, remove in next major version |

## Registry Integration with Existing Architecture

```
ToolRouter
  ├── depends_on → ToolRegistry (built-in tools)
  ├── depends_on → MCPToolRegistry (external MCP tools)
  └── depends_on → PluginLoader (discovered plugins)

AgentRegistry
  ├── used_by → Supervisor Agent (delegates execution)
  └── used_by → Workflow Engine (creates agent instances)

ProviderRegistry
  ├── used_by → ProviderRouter (LLM selection)
  └── used_by → EmbedderFactory (embedding selection)
```
