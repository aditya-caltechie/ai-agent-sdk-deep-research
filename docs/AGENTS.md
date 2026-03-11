## Agents in Deep Research

This project uses a small set of **specialized agents** wired together by `ResearchManager` to run the deep‑research workflow.

---

### PlannerAgent (`planner_agent.py`)

- **Role**: Turn the user’s free‑form query into a structured `WebSearchPlan`.
- **Model**: `gpt-4o-mini`.
- **Output**: `WebSearchPlan` (list of `WebSearchItem{query, reason}`).
- **Called from**: `ResearchManager.plan_searches`.

---

### SearchAgent (`search_agent.py`)

- **Role**: For each planned search term, call `WebSearchTool` and summarize results.
- **Model**: `gpt-4o-mini` + `WebSearchTool`.
- **Output**: Short textual summary per search (used later by the writer).
- **Called from**: `ResearchManager.search` / `perform_searches`.

---

### WriterAgent (`writer_agent.py`)

- **Role**: Synthesize the original query and all search summaries into a long markdown report.
- **Model**: `gpt-4o-mini`.
- **Output**: `ReportData{short_summary, markdown_report, follow_up_questions}`.
- **Called from**: `ResearchManager.write_report`.

---

### Email agent (`email_agent.py`)

- **Role**: Convert the markdown report into HTML and send it via SendGrid.
- **Model**: `gpt-4o-mini` + `send_email` function tool.
- **Output**: A single tool call to `send_email(subject, html_body)`.
- **Called from**: `ResearchManager.send_email`.

