## Concepts: OpenAI Agents SDK in This Project

This document explains the **core concepts** of the OpenAI Agents SDK as used in this repo, with short, practical examples taken from the `src` code.

The basic workflow (also illustrated by the image in `assets/image-8a5312e7-4e49-41b4-abe0-7b6cdd152182.png`) is:

1. **Create an instance of `Agent`.**
2. **Use `with trace()` to track the run.**
3. **Call `Runner.run()` to run the agent.**

### Quick-start: the simplest agent

This is the smallest useful example that follows the three steps above:

```python
from agents import Agent, Runner, trace

# 1. Make an agent with name, instructions, model
agent = Agent(
    name="Jokester",
    instructions="You are a joke teller",
    model="gpt-4o-mini",
)


async def main() -> None:
    # 2. Use with trace() to track the agent
    with trace("Telling a joke"):
        # 3. Call Runner.run(agent, prompt) then print final_output
        result = await Runner.run(agent, "Tell a joke about Autonomous AI Agents")
        print(result.final_output)
```

Everything else in this document is a refinement of this pattern (adding tools, structured outputs, and composing multiple agents together).

---

### 1. Defining an Agent

An **Agent** combines:

- **Instructions** (what the model should do).
- An optional **output type** (structured output via Pydantic).
- Optional **tools** (functions or web search).
- A **model** (e.g. `gpt-4o-mini`).

Example: a simple web search agent (`search_agent.py`):

```python
from agents import Agent, WebSearchTool, ModelSettings

INSTRUCTIONS = (
    "You are a research assistant. Given a search term, you search the web for that term and "
    "produce a concise summary of the results..."
)

search_agent = Agent(
    name="Search agent",
    instructions=INSTRUCTIONS,
    tools=[WebSearchTool(search_context_size="low")],
    model="gpt-4o-mini",
    model_settings=ModelSettings(tool_choice="required"),
)
```

Key ideas:

- **`instructions`** describe behavior in natural language.
- **`tools`** give the agent capabilities beyond pure text generation (e.g. web search).
- **`model_settings`** can enforce that the agent actually calls tools (`tool_choice="required"`).

---

### 2. Structured Output with Pydantic Models

Structured output is critical when downstream code needs to rely on **typed fields** instead of free-form text.  
We model the expected output with Pydantic `BaseModel` classes and pass them as `output_type` to the agent.

Example: planner output (`planner_agent.py`):

```python
from pydantic import BaseModel, Field
from agents import Agent

class WebSearchItem(BaseModel):
    reason: str = Field(description="Your reasoning for why this search is important to the query.")
    query: str = Field(description="The search term to use for the web search.")


class WebSearchPlan(BaseModel):
    searches: list[WebSearchItem] = Field(
        description="A list of web searches to perform to best answer the query."
    )


planner_agent = Agent(
    name="PlannerAgent",
    instructions="Given a query, come up with a set of web searches to perform...",
    model="gpt-4o-mini",
    output_type=WebSearchPlan,
)
```

Later, when we run this agent, we can retrieve a **typed** `WebSearchPlan` object.

---

### 3. Running Agents with `Runner.run`

The `Runner` utility executes agents and returns a result object that exposes:

- `final_output` – raw final value (often a string, or a model instance if already structured).
- `final_output_as(ModelType)` – helper to coerce/validate into a Pydantic model.

Example: from `research_manager.py` (planning searches):

```python
from agents import Runner
from planner_agent import planner_agent, WebSearchPlan

result = await Runner.run(
    planner_agent,
    f"Query: {query}",
)
search_plan = result.final_output_as(WebSearchPlan)
```

And for the writer agent (`writer_agent.py` / `research_manager.py`):

```python
from writer_agent import writer_agent, ReportData

result = await Runner.run(
    writer_agent,
    input,
)
report: ReportData = result.final_output_as(ReportData)
```

**Pattern:**  
1. Build an input string or object.  
2. Call `Runner.run(agent, input)`.  
3. Use `final_output` or `final_output_as(...)` depending on whether you want raw or structured data.

---

### 4. Using Tools (Function Tools and Web Search)

Agents can call **tools** to perform side effects or gather external data.

#### Web search tool

In `search_agent.py`, we attach `WebSearchTool`:

```python
search_agent = Agent(
    name="Search agent",
    instructions=INSTRUCTIONS,
    tools=[WebSearchTool(search_context_size="low")],
    model="gpt-4o-mini",
    model_settings=ModelSettings(tool_choice="required"),
)
```

The agent decides *when* and *how* to call the web search tool to satisfy the instructions.

#### Function tool (sending email)

In `email_agent.py`, we wrap a Python function as a tool using `@function_tool`:

```python
from typing import Dict
from agents import Agent, function_tool

@function_tool
def send_email(subject: str, html_body: str) -> Dict[str, str]:
    """Send an email with the given subject and HTML body"""
    ...

email_agent = Agent(
    name="Email agent",
    instructions="You can send a nicely formatted HTML email based on a detailed report.",
    tools=[send_email],
    model="gpt-4o-mini",
)
```

The model calls `send_email` with structured arguments, and the SDK handles serialization and execution.

---

### 5. Tracing with `trace` and `gen_trace_id`

Tracing lets you inspect runs in the OpenAI Platform, understand tool usage, and debug workflows.

From `research_manager.py`:

```python
from agents import Runner, trace, gen_trace_id

async def run(self, query: str):
    trace_id = gen_trace_id()
    with trace("Research trace", trace_id=trace_id):
        print(f"View trace: https://platform.openai.com/traces/trace?trace_id={trace_id}")
        ...
        # call Runner.run(...) for planner, search, writer, email agents
```

Conceptually:

1. Generate a unique `trace_id`.
2. Wrap your workflow in `with trace(..., trace_id=trace_id):`.
3. Use the printed URL to inspect the run in the traces UI.

This directly matches the **“Create Agent → trace() → runner.run()”** flow shown in the referenced image.

---

### 6. Async Concurrency (`asyncio` and parallel searches)

The SDK integrates cleanly with Python `asyncio`. This project uses it to **run multiple searches in parallel**.

From `research_manager.py`:

```python
import asyncio

async def perform_searches(self, search_plan: WebSearchPlan) -> list[str]:
    tasks = [asyncio.create_task(self.search(item)) for item in search_plan.searches]
    results = []
    for task in asyncio.as_completed(tasks):
        result = await task
        if result is not None:
            results.append(result)
    return results
```

Concepts:

- `asyncio.create_task(...)` schedules multiple coroutines to run concurrently.
- `asyncio.as_completed(tasks)` yields each task as it finishes, so results are processed as soon as they are ready.
- Each `self.search(item)` internally awaits `Runner.run(search_agent, ...)`, so the agent runs are also async.

If you wanted to use `asyncio.gather`, an equivalent pattern would be:

```python
results = await asyncio.gather(
    *(self.search(item) for item in search_plan.searches),
    return_exceptions=False,
)
```

Both patterns allow you to **fan out** many agent calls and then **fan in** the results efficiently.

---

### 7. Putting It All Together (Minimal Example)

Here is a minimal end-to-end pattern, combining the concepts above:

```python
from agents import Agent, Runner, trace, gen_trace_id

simple_agent = Agent(
    name="EchoAgent",
    instructions="Summarize this query in one short paragraph.",
    model="gpt-4o-mini",
)


async def main(query: str) -> str:
    trace_id = gen_trace_id()
    with trace("Simple trace", trace_id=trace_id):
        result = await Runner.run(simple_agent, query)
        return str(result.final_output)
```

Steps:

1. **Define** the agent with instructions and model.
2. **Wrap** the call in `trace(...)` for observability.
3. **Run** it with `Runner.run(...)` and use `final_output` (or `final_output_as(...)` for structured models).

These are the same building blocks used by the more complex multi-agent workflow in this repository.

