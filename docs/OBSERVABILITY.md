## Observability: Traces and Logs for the Deep Research Run

This document explains how to interpret what you see in the **terminal**, **OpenAI traces**, and **API logs** when you run the Deep Research app. The screenshots in the `assets/` folder are referenced to show the sequence from planning searches to sending the email.

---

### 1. High-level run in the terminal

When you start the app:

```bash
uv run src/deep_research.py
```

You see terminal output like:

```text
View trace: https://platform.openai.com/traces/trace?trace_id=trace_271a508365f34a1bb13fabacc3df67dd
Starting research...
Planning searches...
Will perform 3 searches
Searching...
Searching... 1/3 completed
Searching... 2/3 completed
Searching... 3/3 completed
Finished searching
Thinking about report...
Finished writing report
Writing email...
Email sent
```

This comes from `ResearchManager.run` and gives a **high-level timeline**:

- **Planning searches** (planner agent).
- **Running searches in parallel** (search agent + web search tool).
- **Writing the report** (writer agent).
- **Sending the email** (email agent + SendGrid tool).

You can click the `View trace` URL to see the detailed trace in the OpenAI Platform.

---

### 2. Logs overview: all calls in one place

Screenshot: `assets/Screenshot_2026-03-11_at_7.17.31_AM-b3d0d772-6403-497d-97b6-56dfa0a58683.png`

This shows the **Logs → Responses** view in the OpenAI dashboard:

- Each row corresponds to a **single agent call** (planner, each search, writer, email).
- The **Input** column contains the prompt or tool arguments.
- The **Output** column contains the model’s reply or tool calls.
- You can filter by prompt ID, date, or model to debug a specific run.

This view is useful to quickly confirm that all steps (plan, search, write, email) executed for a given query.

---

### 3. Planner agent: planning the web searches

Screenshot: `assets/Screenshot_2026-03-11_at_7.18.49_AM-9ab5614e-eafc-4c18-a668-60226197f7b6.png`

This log entry corresponds to the **planner agent**:

- **Instructions**: describe the agent as a research assistant that should output exactly 3 search terms.
- **Input**: the original user query, e.g. `What are top 4 Agentic AI frameworks in 2026`.
- **Output**: a JSON object with a `searches` list. Each item has:
  - `reason`: why this search is relevant.
  - `query`: the concrete search term.

In code, this is the agent defined in `planner_agent.py`, returning a structured `WebSearchPlan`.  
`ResearchManager.plan_searches` reads this output and logs `Will perform 3 searches` in the terminal based on `len(searches)`.

---

### 4. Search agent: running web searches in parallel

Screenshots:

- `assets/Screenshot_2026-03-11_at_7.19.16_AM-7a3f70d7-35d7-44be-9b59-bfe3134c71ed.png`
- `assets/Screenshot_2026-03-11_at_7.19.51_AM-caf7eb5b-f33b-44ee-b06b-2a5e8238b39e.png`

Each of these log entries corresponds to one **search agent** call:

- **Instructions**: tell the agent to search the web and produce a concise 2–3 paragraph summary (< 300 words).
- **Input**: a string combining
  - `Search term: ...`
  - `Reason for searching: ...`
- **Output**:
  - A **tool call** to `Web Search` (the `WebSearchTool`).
  - A textual **summary** of the web results, referencing links found during the search.

In `ResearchManager.perform_searches`:

- For each `WebSearchItem` from the planner, `self.search(item)` runs the search agent.
- `asyncio.create_task` schedules all searches concurrently.
- `asyncio.as_completed` yields results as they finish, which drives the terminal updates:
  - `Searching... 1/3 completed`
  - `Searching... 2/3 completed`
  - `Searching... 3/3 completed`

The summaries returned here become the **“summarized search results”** passed into the writer agent.

---

### 5. Writer agent: creating the long-form report

Screenshot: `assets/Screenshot_2026-03-11_at_7.20.42_AM-73dd0153-ebb9-4134-9a97-4045a8fa823b.png`

This log entry corresponds to the **writer agent**:

- **Instructions**: describe a senior researcher who must:
  - Read the original query and search summaries.
  - Create an outline.
  - Write a long markdown report (5–10 pages, ≥ 1000 words).
- **Input**: text that includes:
  - `Original query: ...`
  - `Summarized search results: [...]` (the list of search summaries).
- **Output**: a structured `ReportData` object with:
  - `short_summary`
  - `markdown_report`
  - `follow_up_questions`

`ResearchManager.write_report` reads this output and logs:

- `Thinking about report...`
- `Finished writing report`

The `markdown_report` field is what you see rendered in the browser UI and what gets passed to the email agent.

---

### 6. Email agent: formatting to HTML and sending the email

Screenshots:

- `assets/Screenshot_2026-03-11_at_7.21.14_AM-9727226c-772b-426c-a0c1-82dec13b8eed.png`
- `assets/Screenshot_2026-03-11_at_7.22.01_AM-d1f250b5-f89d-4637-8bc1-b16b2f389560.png`

These log entries correspond to the **email agent**:

- **Instructions**: tell the agent to send a nicely formatted HTML email based on a detailed report.
- **Input**: the full markdown report created by the writer agent.
- **Output** (Function Call):
  - A call to the `send_email` tool with arguments:
    - `subject`: e.g. `"Report on Top Agentic AI Frameworks in 2026"`.
    - `html_body`: the report converted into HTML.

In the local environment:

- `send_email` (in `email_agent.py`) uses the SendGrid SDK and environment variable `SENDGRID_API_KEY`.
- It sends the HTML email to the configured recipient and prints the SendGrid response status.
- `ResearchManager.send_email` logs:
  - `Writing email...`
  - `Email sent`

In some hosted environments, you may see an additional assistant message like:

> “It seems I encountered an issue while trying to send the email…”

This reflects limitations of the hosted environment, but in your local run the tool completes and the email is actually sent.

---

### 7. Putting it all together: how to debug a run

To understand or debug a run end-to-end:

1. **Start from the terminal**
   - Check the `View trace` URL and the high-level status messages.
2. **Open the trace / logs in the dashboard**
   - Use the trace or prompt ID to filter responses.
3. **Follow the sequence of agents**
   - Planner agent → search agents (three entries, one per search) → writer agent → email agent.
4. **Inspect inputs and outputs**
   - Confirm that the planner produced the expected `searches`.
   - Verify that each search agent call successfully used the web search tool and returned a summary.
   - Check that the writer agent produced a coherent `markdown_report`.
   - Ensure the email agent called `send_email` with the right subject and HTML body.

These observability tools (terminal logs, traces, and API logs) together give you a complete picture of what is happening at each step when you run the Deep Research project.

