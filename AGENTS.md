## AGENTS — Project overview (Deep Research)

This document is a **contributor-oriented map** of this repo: where things live, what each module does, and the common dev/run commands.

---

### Repository layout

```text
ai-agent-sdk-deep-research/
├── README.md                 # User-facing overview & quickstart
├── AGENTS.md                 # This file (contributor map)
├── pyproject.toml            # Project config & dependencies (managed with uv)
├── docs/
│   ├── BASICS.md             # How the OpenAI Agents SDK is used here
│   ├── HLD.md                # High-level architecture & flow diagrams
│   ├── DEMO.md               # How to run the demo (UI + terminal)
│   ├── OBSERVABILITY.md      # Traces, logs, and debugging a run
│   ├── GUARDRAILS.md         # Safety, limits, and production hardening
│   ├── EVALS.md              # How to evaluate agents & reports
│   └── AGENTS.md             # Short per-agent reference
├── src/
│   ├── deep_research.py      # Entrypoint: Gradio UI + wiring to ResearchManager
│   ├── research_manager.py   # Orchestrator: plans, searches, writes, emails
│   ├── planner_agent.py      # PlannerAgent definition (WebSearchPlan)
│   ├── search_agent.py       # SearchAgent with WebSearchTool
│   ├── writer_agent.py       # WriterAgent producing ReportData
│   └── email_agent.py        # Email agent with send_email function tool (SendGrid)
└── tests/
    └── test_research_manager.py  # Unit tests for the orchestrator
```

---

### Key components (where to start reading)

- **Entrypoint / UI: `src/deep_research.py`**
  - Defines the Gradio Blocks UI (textbox + Run button + markdown output).
  - On submit, calls `ResearchManager().run(query)` and streams updates/results back to the UI.

- **Orchestrator: `src/research_manager.py`**
  - Central async workflow:
    - `plan_searches` → `perform_searches` → `write_report` → `send_email`.
  - Wraps each run in an OpenAI **trace** (`trace("Research trace", trace_id=...)`).
  - Uses `Runner.run(...)` to call each specialized agent.

- **Planner agent: `src/planner_agent.py`**
  - Defines `WebSearchItem` and `WebSearchPlan` (Pydantic models).
  - `planner_agent` (model `gpt-4o-mini`) turns a user query into a small list of concrete web searches, each with a reason.

- **Search agent: `src/search_agent.py`**
  - Configures `search_agent` with `WebSearchTool`.
  - For each `WebSearchItem`, runs a web search and returns a concise 2–3 paragraph summary.
  - Called in parallel from `ResearchManager.perform_searches`.

- **Writer agent: `src/writer_agent.py`**
  - Defines `ReportData` (short summary, long markdown report, follow‑up questions).
  - `writer_agent` (model `gpt-4o-mini`) takes the original query + search summaries and writes the long-form report.

- **Email agent / tool: `src/email_agent.py`**
  - Wraps a `send_email(subject, html_body)` function as a **function tool**.
  - Uses the SendGrid SDK (`SENDGRID_API_KEY`) to send the HTML report to a fixed recipient.
  - `email_agent` turns the markdown report into HTML and calls `send_email`.

---

### Configuration & environment variables

Create a `.env` in the project root (or export vars). Required keys:

| Variable          | Used by         | Purpose                                  |
|-------------------|-----------------|------------------------------------------|
| `OPENAI_API_KEY`  | All agents      | Access to OpenAI models via Agents SDK   |
| `SENDGRID_API_KEY`| `email_agent`   | Sending HTML report emails via SendGrid  |

Example:

```bash
export OPENAI_API_KEY="sk-..."
export SENDGRID_API_KEY="SG-..."
```

---

### Running locally

From the repo root:

```bash
uv sync                 # Install dependencies
uv run src/deep_research.py
```

You should see a local Gradio URL in the terminal (e.g. `http://127.0.0.1:7863`) plus a **trace URL** for observability.

Open the URL in your browser, enter a research query, and click **Run**. Watch status updates stream in, then check your inbox for the HTML report.

---

### Tests and CI

- **Unit tests**:

  ```bash
  uv run pytest -q
  ```

  Currently covers `ResearchManager` behavior (planning, searching, writing, emailing) with mocked agents/tools.

- **GitHub Actions**:
  - `.github/workflows/ci.yml`:
    - Installs Python + `uv`.
    - Runs `uv sync` and a basic sanity check (`python -m compileall src`).

---

### Where to go next

- For **architecture and flows**: see `docs/HLD.md`.
- For a **step-by-step demo** (UI + terminal): see `docs/DEMO.md`.
- For **agent details**: see `docs/AGENTS.md`.
- For **observability, guardrails, and evals** as you move toward production:
  - `docs/OBSERVABILITY.md`
  - `docs/GUARDRAILS.md`
  - `docs/EVALS.md`

