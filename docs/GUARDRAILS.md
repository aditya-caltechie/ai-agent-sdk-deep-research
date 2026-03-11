## Guardrails for Deep Research

This document explains **what guardrails are**, **why they matter**, and **where you can add them** as you move this project from a local demo into a production‑grade system.

---

### 1. What are guardrails?

In this context, **guardrails** are any **technical or policy controls** you put around the AI system to:

- **Constrain behavior** (what the model / agents are allowed to do).
- **Limit blast radius** (how much they can spend, access, or change).
- **Protect users and data** (privacy, safety, compliance).

They are not a single feature, but a **layered set of practices** across:

- **Prompts and instructions** – clearly stating allowed / disallowed behavior.
- **Model and tool configuration** – which tools exist, which inputs are allowed, and what they can touch.
- **Runtime checks** – validating inputs/outputs, enforcing limits, and logging/alerting.

---

### 2. Why guardrails are needed

As long as this project is a local demo, the risk is low. In production, the same workflow can:

- **Spend real money** (OpenAI calls, web search, email sending).
- **Touch sensitive data** (internal URLs, customer information).
- **Trigger side effects** (sending outbound emails, hitting APIs).

Guardrails help you:

- **Avoid misuse** (e.g., generating or emailing inappropriate content).
- **Avoid accidents** (e.g., infinite loops, unbounded search, runaway costs).
- **Make debugging easier** by keeping traces, logs, and decisions auditable.

---

### 3. Where guardrails fit in this codebase

There are several natural insertion points in this project:

- **UI layer (`deep_research.py`)**
  - Validate and sanitize the **user query** before sending it to `ResearchManager`.
  - Enforce simple policies like max length, disallowed topics, or allowed languages.

- **Orchestrator (`research_manager.py`)**
  - Central place to add:
    - **Rate limits** (per user / per IP / per time window).
    - **Budget limits** (max number of searches, max tokens, max run time).
    - **Fallback behavior** when agents or tools fail.
  - Because all agents are called from here, you can wrap each step with **try/except**, logging, and policy checks.

- **Agent definitions (`planner_agent.py`, `search_agent.py`, `writer_agent.py`, `email_agent.py`)**
  - Strengthen **instructions** to:
    - Avoid certain content (e.g., hate, violence, PII).
    - Avoid making factual claims without citing sources.
    - Stay within specific formatting requirements.
  - Use **structured outputs (Pydantic models)** as a basic guardrail so you can validate types, lengths, and ranges before using the data.

- **Tools and external calls (`email_agent.py`, any future tools)**
  - Add **pre‑send checks** before sending email:
    - Strip or escape dangerous HTML.
    - Enforce subject/body length and content policies.
    - Optionally require a **human approval step** in production (e.g., queue email drafts for review instead of sending automatically).
  - For new tools (e.g., internal APIs, databases), wrap them with **whitelists and parameter validations** so agents cannot call arbitrary endpoints.

---

### 4. Concrete examples for this project

Here are a few practical guardrails you can add as you harden the system:

- **Limit search scope and cost**
  - In `planner_agent.py`, keep `HOW_MANY_SEARCHES` small and document why.
  - In `research_manager.py`, cap the number of concurrent tasks and/or total runtime for `perform_searches`.

- **Validate planner output**
  - After `plan_searches`, enforce:
    - `1 <= len(plan.searches) <= 3`.
    - Each `query` is non‑empty and within a max length.
    - Each `reason` is present and not obviously unsafe.

- **Filter and normalize search summaries**
  - Before passing `search_results` to the writer agent:
    - Truncate very long summaries.
    - Optionally strip URLs or unwanted HTML.

- **Post‑process the report**
  - After `write_report`, you can:
    - Enforce a **max word count**.
    - Remove disallowed phrases, URLs, or HTML.
    - Add a standard **disclaimer** section at the end.

- **Email safety**
  - In `send_email` (inside `email_agent.py`):
    - Sanitize the HTML.
    - Add a fixed **subject prefix** like `[Deep Research Demo]` so emails are clearly labeled.
    - In production, consider **sending to a safe test address** or staging environment before rolling out to real users.

---

### 5. Concrete code examples in this repo

Below are **non-breaking example snippets** showing how you might implement some of these guardrails in this codebase. They are meant as starting points rather than copy‑paste requirements.

- **Input validation in `deep_research.py`**

  Add a simple check before calling `ResearchManager().run(query)`:

  ```python
  MAX_QUERY_CHARS = 500

  def validate_query(query: str) -> str:
      cleaned = query.strip()
      if not cleaned:
          raise ValueError("Query must not be empty.")
      if len(cleaned) > MAX_QUERY_CHARS:
          raise ValueError("Query is too long. Please shorten it.")
      return cleaned
  ```

  Then, in the Gradio `run` handler:

  ```python
  def run(query: str):
      query = validate_query(query)
      return ResearchManager().run(query)
  ```

- **Planner output checks in `research_manager.py`**

  After `plan_searches` returns a `WebSearchPlan`, validate it before continuing:

  ```python
  def _validate_plan(self, plan: WebSearchPlan) -> WebSearchPlan:
      if not 1 <= len(plan.searches) <= 3:
          raise ValueError("Planner produced an invalid number of searches.")
      for item in plan.searches:
          if not item.query or len(item.query) > 200:
              raise ValueError("Planner produced an invalid search query.")
      return plan
  ```

  And in `plan_searches`:

  ```python
  result = await Runner.run(planner_agent, f"Query: {query}")
  plan = result.final_output_as(WebSearchPlan)
  return self._validate_plan(plan)
  ```

- **Limiting search concurrency in `research_manager.py`**

  If you want to cap concurrent searches:

  ```python
  MAX_CONCURRENT_SEARCHES = 3
  ```

  And inside `perform_searches`, use a semaphore:

  ```python
  sem = asyncio.Semaphore(MAX_CONCURRENT_SEARCHES)

  async def guarded_search(item: WebSearchItem):
      async with sem:
          return await self.search(item)

  tasks = [asyncio.create_task(guarded_search(item)) for item in search_plan.searches]
  ```

- **Post‑processing the report in `research_manager.py`**

  After `write_report` returns `ReportData`, enforce word count and add a disclaimer:

  ```python
  def _post_process_report(self, report: ReportData) -> ReportData:
      words = report.markdown_report.split()
      MAX_WORDS = 3000
      if len(words) > MAX_WORDS:
          report.markdown_report = " ".join(words[:MAX_WORDS]) + "\n\n_[Truncated for length]_"

      disclaimer = (
          "\n\n---\n"
          "_This report is generated by an AI system and may contain inaccuracies. "
          "Please verify critical information independently._"
      )
      if disclaimer not in report.markdown_report:
          report.markdown_report += disclaimer
      return report
  ```

  And in `write_report`:

  ```python
  result = await Runner.run(writer_agent, input)
  report = result.final_output_as(ReportData)
  return self._post_process_report(report)
  ```

- **Email guardrails in `email_agent.py`**

  You can add a subject prefix and basic HTML sanitization:

  ```python
  def _sanitize_html(html_body: str) -> str:
      # Example: very light guardrail – in production consider a real HTML sanitizer.
      return html_body.replace("<script", "&lt;script")
  ```

  And inside `send_email`:

  ```python
  safe_html = _sanitize_html(html_body)
  prefixed_subject = f"[Deep Research Demo] {subject}"
  mail = Mail(from_email, to_email, prefixed_subject, Content("text/html", safe_html)).get()
  ```

---

### 6. Moving from demo to production

When you’re ready to treat this as a production service, consider adding:

- **Authentication & authorization**
  - Gate the Gradio UI or any API endpoint behind auth.
  - Apply different limits per user/role (e.g., internal vs. external users).

- **Central configuration**
  - Move things like `HOW_MANY_SEARCHES`, model names, and max token limits into **config files or environment variables** so you can tighten guardrails without redeploying code.

- **Monitoring & alerts**
  - Build lightweight dashboards from traces/logs:
    - Number of runs, failures, average cost, average latency.
  - Create alerts for:
    - Repeated failures in one step (e.g., email tool errors).
    - Unusually long or expensive runs.

- **Human‑in‑the‑loop options**
  - Allow certain high‑risk queries to:
    - Be **blocked** outright (with a polite message).
    - Or be **held for review** so a human can approve or edit the report before sending it.

Guardrails are an ongoing process, not a one‑time task. As you add new agents or tools, treat each as a new surface area and ask:

> What can go wrong here, and how do we prevent or contain it?

This mindset will help you evolve the Deep Research project from a powerful demo into a safe, reliable production system.

