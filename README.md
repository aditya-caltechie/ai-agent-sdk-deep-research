## Deep Research – Multi‑Agent AI Research Assistant

An end‑to‑end **AI research assistant** built with the **OpenAI Agents SDK**, **Gradio**, and **SendGrid**.  
Given a natural‑language query, the app:

- **Plans** a set of focused web searches.
- **Runs searches in parallel** using tools.
- **Synthesizes** the results into a long‑form markdown report.
- **Emails** a nicely formatted HTML version of the report.

This repo is a practical reference for building **agentic, tool‑using, multi‑step workflows** with tracing and a simple web UI.

---

### Objective

The goal of this project is to demonstrate how to:

- Use the **OpenAI Agents SDK** to compose multiple specialized agents.
- Combine **structured outputs (Pydantic)**, **tools** (web search, email), and **tracing**.
- Orchestrate an async workflow in Python that powers a **Gradio UI** and a **SendGrid email** pipeline.

You can use this as a template for your own deep‑research or analysis agents.

---

### High‑Level Architecture

At a high level, the system looks like this:

```text
┌────────────────────────┐
│      Gradio UI         │
│   (`deep_research`)    │
└──────────┬─────────────┘
           │  user query
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
  │ WebSearchPlan │ Web result summaries    │ ReportData
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

**Flow (simplified):**

1. User submits a query in the Gradio UI (`deep_research.py`).
2. `ResearchManager.run`:
   - Plans searches via `PlannerAgent`.
   - Runs web searches in parallel via `SearchAgent`.
   - Calls `WriterAgent` to produce a long markdown report.
   - Calls `EmailAgent` to send the report as HTML.
3. Status messages and the final markdown report are **streamed** back to the UI.

For a more detailed explanation, see `docs/HLD.md` and `docs/BASICS.md`.

---

### Tech Stack

- **Language / Runtime**
  - Python (managed with `uv` and `pyproject.toml`)
- **AI / Agents**
  - **OpenAI Agents SDK** (`agents` package)
  - Models: e.g. `gpt-4o-mini`
  - Concepts: `Agent`, `Runner`, `trace`, `gen_trace_id`, `ModelSettings`, `WebSearchTool`, `function_tool`
- **Web UI**
  - **Gradio** Blocks UI (`deep_research.py`)
- **Email**
  - **SendGrid** Python SDK for sending HTML emails
- **Config / Env**
  - `python-dotenv` (`load_dotenv`) for local `.env` loading

---

### Project Structure

Key files and their responsibilities:

- `src/deep_research.py`  
  - Application entrypoint.  
  - Defines the Gradio Blocks UI and wires it to `ResearchManager().run`.

- `src/research_manager.py`  
  - Orchestration / workflow engine.  
  - Coordinates planning, searching, report writing, and email sending.  
  - Uses `asyncio` to run web searches in parallel.  
  - Wraps the whole run in an OpenAI **trace**.

- `src/planner_agent.py`  
  - Defines `WebSearchItem` and `WebSearchPlan` (Pydantic models).  
  - Configures `planner_agent` to turn a query into a structured search plan.

- `src/search_agent.py`  
  - Configures `search_agent` with `WebSearchTool`.  
  - Performs web searches and returns concise summaries.

- `src/writer_agent.py`  
  - Defines `ReportData` (Pydantic).  
  - Configures `writer_agent` to generate a long, markdown report plus a short summary and follow‑up questions.

- `src/email_agent.py`  
  - Wraps a `send_email(subject, html_body)` function as a **function tool**.  
  - Uses SendGrid to send the HTML report to a fixed recipient.

- `docs/BASICS.md`  
  - Conceptual overview of how the OpenAI Agents SDK is used in this project.

- `docs/HLD.md`  
  - High‑level architecture and data‑flow documentation.

- `docs/DEMO.md`  
  - Narrative walkthrough of running the demo and what you see in terminal + browser.

---

### Prerequisites

- **Python** (compatible with `uv`; see `pyproject.toml` for the exact version)
- **uv** package manager installed (`pip install uv` or follow the official docs)
- An **OpenAI API key** accessible to the `agents` SDK, e.g.:
  - `OPENAI_API_KEY` in your environment or `.env`
- A **SendGrid API key**:
  - `SENDGRID_API_KEY` in your environment or `.env`

---

### Setup

1. **Clone the repo**

```bash
git clone <your-fork-or-repo-url>
cd ai-agent-sdk-deep-research
```

2. **Create and populate `.env`**

Create a `.env` file in the project root (or otherwise set these env vars):

```bash
OPENAI_API_KEY=sk-...
SENDGRID_API_KEY=SG-...
```

Optionally adjust the sender/recipient email addresses in `src/email_agent.py`.

3. **Install dependencies with uv**

```bash
uv sync
```

This will create a virtual environment and install everything from `pyproject.toml` / `uv.lock`.

---

### How to Run

From the project root:

```bash
uv run src/deep_research.py
```

You should see output similar to:

```text
* Running on local URL:  http://127.0.0.1:7863
* To create a public link, set `share=True` in `launch()`.
View trace: https://platform.openai.com/traces/trace?trace_id=...
Starting research...
...
Email sent
Research completed...
```

Then:

1. Open the local URL (e.g. `http://127.0.0.1:7863`) in your browser.
2. Enter a query like `What are top 4 Agentic AI frameworks in 2026`.
3. Click **Run**.
4. Watch status updates and the final markdown report stream into the Gradio UI.
5. Check your inbox for the HTML email sent by `EmailAgent`.

---

### Tracing and Observability

- Each run is wrapped in `trace("Research trace", trace_id=gen_trace_id())`.
- The terminal prints a **“View trace”** URL:

```text
View trace: https://platform.openai.com/traces/trace?trace_id=...
```

- Open this URL to inspect:
  - Agent calls
  - Tool invocations (web search, email)
  - Inputs/outputs at each step

This is extremely useful for debugging and understanding how the multi‑agent workflow behaves.

---

### Extending the Project

Ideas for customization:

- **Change the number of searches** in `planner_agent.py` (`HOW_MANY_SEARCHES`).
- **Adjust summarization style** or length in `search_agent.py`.
- **Tweak report format** or constraints in `writer_agent.py`.
- **Customize recipients / subject templates** in `email_agent.py`.
- Add more tools or agents (e.g. database lookups, company‑internal APIs) and plug them into `ResearchManager`.

This codebase is intentionally small but shows the full pattern for **planning → tools → synthesis → delivery** using the OpenAI Agents SDK.

---

### Cost Caution

- **Each full deep‑research run typically costs around \$0.05–\$0.20 in OpenAI usage**, depending on your query and model pricing.  
- Be mindful when running many queries in a row, especially on paid accounts or in production environments.  
- Consider adding your own limits, logging, or confirmations if you adapt this project for heavy or automated use.
