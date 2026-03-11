## Deep Research Architecture

This document describes the high-level architecture of the **Deep Research** application.

### Overview

The system is an AI-powered research assistant that:

- Accepts a user query through a Gradio web UI.
- Plans a set of relevant web searches.
- Executes those searches in parallel.
- Synthesizes the results into a long-form report.
- Sends the report via email.

The orchestration is handled by a central `ResearchManager` class, which coordinates a set of specialized agents built on top of the `agents` SDK.

### Component Diagram (Logical)

```text
┌────────────────────────┐
│      Gradio UI         │
│   (`deep_research`)    │
└──────────┬─────────────┘
           │  query
           ▼
┌────────────────────────┐
│    ResearchManager     │
│ (`research_manager`)   │
└──────────┬─────────────┘
   plan    │    write, email
           │
  ┌────────┴────────┬─────────────────────────┐
  ▼                 ▼                         ▼
PlannerAgent    SearchAgent               WriterAgent
(`planner_`     (`search_`                (`writer_`
 `agent`)        `agent`)                  `agent`)
  │               │                         │
  │ WebSearchPlan │ Web results summaries   │ ReportData
  ▼               ▼                         ▼
                      ┌────────────────────┐
                      │    EmailAgent      │
                      │  (`email_agent`)   │
                      └─────────┬──────────┘
                                │
                                ▼
                           Email via
                         SendGrid API
```

### Flow Diagram

The following image shows the end-to-end flow of the system, from user query to final email:

![Deep Research Flow](../assets/image-2b4324bd-2387-444e-94a3-f2a4805844c5.png)

### Data Flow

1. **User query submission**
   - The user submits a research query via the Gradio UI defined in `deep_research.py`.
   - The UI calls `ResearchManager().run(query)` as an async generator and streams status updates plus the final markdown report back to the UI.

2. **Planning searches**
   - `ResearchManager.plan_searches` calls `Runner.run(planner_agent, f"Query: {query}")`.
   - `planner_agent` (in `planner_agent.py`) is an `Agent` that:
     - Receives the user query.
     - Produces a `WebSearchPlan` Pydantic model consisting of a list of `WebSearchItem` objects, each containing:
       - `query`: a concrete search term.
       - `reason`: why this search is relevant.

3. **Executing searches**
   - `ResearchManager.perform_searches` iterates over `WebSearchPlan.searches` and schedules concurrent tasks using `asyncio.create_task(self.search(item))`.
   - Each `search` call:
     - Formats an input string: `"Search term: {item.query}\nReason for searching: {item.reason}"`.
     - Invokes `Runner.run(search_agent, input)`.
     - `search_agent` (in `search_agent.py`) is an `Agent` configured with:
       - `WebSearchTool(search_context_size="low")` to perform web searches.
       - Instructions tailored to produce a concise 2–3 paragraph summary (< 300 words).
   - Results are collected as `list[str]` of text summaries (skipping failures) and returned to the manager.

4. **Writing the report**
   - `ResearchManager.write_report` builds an input string combining:
     - The original query.
     - The summarized search results list.
   - It calls `Runner.run(writer_agent, input)`.
   - `writer_agent` (in `writer_agent.py`) is an `Agent` that:
     - Uses detailed instructions to create an outline and then a long-form markdown report.
     - Outputs a `ReportData` Pydantic model with:
       - `short_summary`: brief findings.
       - `markdown_report`: the full report content.
       - `follow_up_questions`: suggested future research topics.

5. **Sending the email**
   - `ResearchManager.send_email` calls `Runner.run(email_agent, report.markdown_report)`.
   - `email_agent` (in `email_agent.py`) is an `Agent` configured with a `send_email` function tool.
   - The `send_email` tool:
     - Uses the SendGrid SDK with `SENDGRID_API_KEY` from environment variables.
     - Constructs an HTML email from the report and sends it from a configured sender to a fixed recipient.

6. **Streaming results back to the UI**
   - Throughout `ResearchManager.run`, intermediate status messages (e.g., “Searches planned…”, “Report written…”) and the final `markdown_report` are `yield`ed.
   - The Gradio UI displays these messages progressively to the user.

### Key Modules and Responsibilities

- **`deep_research.py`**
  - Application entrypoint.
  - Defines and launches the Gradio Blocks UI.
  - Bridges user input to `ResearchManager.run`.

- **`research_manager.py`**
  - Orchestration layer / workflow engine.
  - Coordinates planning, searching, report writing, and email sending.
  - Manages async concurrency for web searches.

- **`planner_agent.py`**
  - Defines the `WebSearchItem` and `WebSearchPlan` Pydantic models.
  - Configures `planner_agent` to transform a user query into a structured search plan.

- **`search_agent.py`**
  - Defines `search_agent` using `WebSearchTool`.
  - Responsible for performing web searches and summarizing results.

- **`writer_agent.py`**
  - Defines `ReportData` Pydantic model.
  - Configures `writer_agent` to synthesize search results into a long markdown report.

- **`email_agent.py`**
  - Defines the `send_email` function tool using SendGrid.
  - Configures `email_agent` to convert the report into HTML and send it via email.

### External Dependencies and Integrations

- **Agents SDK (`agents`)**
  - Provides `Agent`, `Runner`, `trace`, `gen_trace_id`, `ModelSettings`, `WebSearchTool`, and `function_tool`.
  - Used to define and execute all AI agents and tools.

- **Gradio**
  - Provides the web UI (Blocks, Textbox, Button, Markdown display).

- **SendGrid**
  - Used by `email_agent` to send the final report via email.
  - Requires `SENDGRID_API_KEY` to be set in the environment.

### Tracing and Observability

- `ResearchManager.run` wraps the workflow in a `trace("Research trace", trace_id=trace_id)` context.
- A trace ID is generated via `gen_trace_id()` and printed as an OpenAI Platform trace URL:
  - `https://platform.openai.com/traces/trace?trace_id={trace_id}`
- This enables inspection of the end-to-end workflow in the OpenAI traces UI.

