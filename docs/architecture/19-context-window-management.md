# Document 19 — Context Window Management

## The Problem

Each agent's ReAct loop appends to a growing context: Plan → Reason → Tool call → Observation → Reflect → Validate. After 5-8 iterations, this can exceed 32K tokens. After 10+ iterations, even 128K models may fail.

This document defines the context management strategy (accepted architectural decision: handle via prompt engineering rather than a separate summarization agent).

## Strategy: Structured Prompt Engineering

```python
class ContextManager:
    """Manages agent context to stay within model limits."""

    def __init__(self, max_tokens: int = 32000, model: str = "gpt-4o-mini"):
        self.max_tokens = max_tokens
        self.model = model
        self.tokenizer = TokenizerFactory.get_tokenizer(model)

    async def prepare_context(self, agent: BaseAgent, task: dict,
                               history: list[AgentMessage]) -> list[dict]:
        """Build a context window that fits within model limits."""

        messages = []

        # 1. System prompt (always included, small)
        system_prompt = await self._load_system_prompt(agent)
        messages.append({"role": "system", "content": system_prompt})
        tokens_used = self.tokenizer.count(system_prompt)

        # 2. Task description (always included)
        task_str = json.dumps(task)
        messages.append({"role": "user", "content": task_str})
        tokens_used += self.tokenizer.count(task_str)

        # 3. Conversation history (trimmed to fit)
        budget = self.max_tokens - tokens_used - self._reserve_for_output(agent)
        history_tokens = sum(self.tokenizer.count(m.content) for m in history)

        if history_tokens <= budget:
            # All history fits
            for msg in history:
                messages.append(self._to_dict(msg))
        else:
            # Trim from the oldest messages, keep the most recent
            trimmed = self._trim_history(history, budget)
            for msg in trimmed:
                messages.append(self._to_dict(msg))

        return messages

    def _trim_history(self, history: list[AgentMessage],
                       budget: int) -> list[AgentMessage]:
        """Remove oldest messages while preserving the most recent interactions."""
        # Always keep the last 2 interactions (current plan + observation)
        keep = 2
        preserved = history[-keep:] if len(history) >= keep else history
        preserved_tokens = sum(self.tokenizer.count(m.content) for m in preserved)

        remaining_budget = budget - preserved_tokens
        if remaining_budget <= 0:
            return preserved

        # Add earlier messages while we have budget
        result = []
        for msg in reversed(history[:-keep]):
            tokens = self.tokenizer.count(msg.content)
            if tokens <= remaining_budget:
                result.insert(0, msg)
                remaining_budget -= tokens
            else:
                break  # No more budget

        result.extend(preserved)
        return result

    def _reserve_for_output(self, agent: BaseAgent) -> int:
        """Reserve tokens for the agent's output."""
        return agent.max_output_tokens or 2048
```

## Prompt Engineering Rules for Agents

Each agent's system prompt includes explicit instructions to manage context:

```
CONTEXT MANAGEMENT RULES:
1. Keep each response under 500 tokens.
2. Do not repeat information already provided in previous turns.
3. When listing papers, use format: [id] Title (year). No abstracts.
4. When reflecting, state only: "Sufficient" / "Need more: [specific gap]"
5. Tool outputs: summarize, do not verbatim copy.
6. If the information needed is already in context, reference it by ID
   rather than repeating.
7. Use structured JSON output — no explanatory text outside the schema.
```

## Agent Output Structure (Minimizes Token Usage)

```python
class ResearchAgentOutput(BaseModel):
    """Structured output that minimizes token usage."""
    papers: list[PaperSummary]  # Title + ID only, no abstracts
    search_metadata: SearchMetadata
    reflections: list[str]  # Max 50 chars each
    needs_more: bool
    refinement_query: str | None
```

## Model Selection by Context Needs

```python
class ContextRouter:
    """Routes requests to models based on context size."""

    CONTEXT_THRESHOLDS = {
        "gpt-4o-mini": {
            "max_context": 128000,
            "cost_per_1k_input": 0.00015,
            "cost_per_1k_output": 0.0006,
        },
        "gpt-4o": {
            "max_context": 128000,
            "cost_per_1k_input": 0.0025,
            "cost_per_1k_output": 0.01,
        },
        "gemini-1.5-flash": {
            "max_context": 1048576,  # 1M tokens
            "cost_per_1k_input": 0.000075,
            "cost_per_1k_output": 0.0003,
        },
        "claude-3-haiku": {
            "max_context": 200000,
            "cost_per_1k_input": 0.00025,
            "cost_per_1k_output": 0.00125,
        },
    }

    def select_model(self, estimated_tokens: int,
                     complexity: str = "medium") -> str:
        if estimated_tokens > 100000:
            return "gemini-1.5-flash"  # Largest context window
        elif complexity == "high" and estimated_tokens < 64000:
            return "gpt-4o"  # Best reasoning
        else:
            return "gpt-4o-mini"  # Default: cost-optimized
```

## Trade-offs

| Decision | Alternative | Rationale |
|---|---|---|
| Prompt engineering instead of summarizer agent | LLM-as-Judge summarizer | Simpler; avoids additional API calls and latency |
| Trim oldest history first | Summarize past turns | Trimming is lossy but fast; summarization costs extra tokens |
| Reserve output tokens | Dynamic allocation | Prevents truncation of agent output |
| Structured JSON outputs | Free-form text | JSON is more token-efficient than natural language for structured data |
