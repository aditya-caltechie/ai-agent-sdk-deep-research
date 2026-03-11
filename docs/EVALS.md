## Evaluations (Evals) for Deep Research

This document explains **what evaluations are**, **why they matter**, and **how to run practical evals for this Deep Research project**, with concrete examples.

---

### 1. What are evals?

In this context, **evals** are repeatable tests that measure how well your AI system behaves according to your goals:

- **Quality**: Does it answer the question correctly and clearly?
- **Reliability**: Does it behave consistently across runs and inputs?
- **Safety / policy**: Does it avoid disallowed content or actions?
- **Cost / latency**: Is it fast and cheap enough?

Unlike unit tests (which check small pieces of code), evals typically:

- Use **realistic prompts** and **expected outcomes** (sometimes called “goldens”).
- Are run **end‑to‑end** or at the **agent level**, not just per function.
- Are used **continuously** as you change prompts, models, or guardrails.

---

### 2. Why evals are important for this project

This project chains multiple agents and tools:

- `planner_agent` → `search_agent` (3×) → `writer_agent` → `email_agent`

There are **two main layers** you care about:

- **Agent‑level behavior** – Does each agent do its specific job well?
  - Planner: good search plan.
  - Search: faithful summaries of web results.
  - Writer: clear, structured report.
  - Email: clean HTML, sensible subject.
- **Underlying LLM behavior** – Does the base model (e.g. `gpt‑4o‑mini`) follow instructions, stay on policy, and respond with the right style?

Changes to:

- Instructions (prompts),
- Model choice (e.g., switching to a different model),
- Guardrails, or
- Tool behavior (e.g., search or email)

can affect both layers.

Evals help you:

- Detect regressions when you tweak prompts or swap models.
- Compare different configurations (e.g., 3 vs 5 searches, different models per agent).
- Build confidence before shipping changes to production.

---

### 3. Levels of evaluation

You can evaluate this project at three main levels:

- **A. End‑to‑end evals**  
  Run the whole pipeline from query → email and score the final **report** and **overall behavior**.

- **B. Agent‑level evals**  
  Evaluate each agent in isolation:
  - Planner output (search quality and coverage).
  - Search summaries (faithfulness, conciseness).
  - Writer outputs (structure, depth, correctness).
  - Email agent (HTML formatting, subject line quality).

- **C. System health metrics**  
  Track:
  - Latency per step.
  - Cost per run.
  - Error rates (e.g., search failures, email failures).

At a glance, mapping **agents → eval focus**:

- `planner_agent`: coverage of query, diversity of searches, usefulness of reasons.
- `search_agent`: factuality and conciseness of summaries, presence of citations.
- `writer_agent`: structure, depth, correctness, and style of long report.
- `email_agent`: correctness of HTML formatting and subject, safety of outgoing content.

---

### 4. Example evals for this repository

Below are concrete examples you can implement with simple Python scripts, notebooks, or an external eval framework.

#### 4.1 End‑to‑end report quality eval

**Goal**: Ensure the final report is high‑quality for a set of representative queries.

1. Create a file `evals/end_to_end_queries.jsonl` with entries like:

   ```json
   {"id": "agentic_frameworks", "query": "What are top 4 Agentic AI frameworks in 2026?"}
   {"id": "rlhf_overview", "query": "Explain RLHF (Reinforcement Learning from Human Feedback) to a senior engineer."}
   {"id": "vector_databases", "query": "Compare 3 popular vector databases for RAG workloads."}
   ```

2. Write a small script (e.g. `evals/run_end_to_end.py`) that:
   - Loops over each query.
   - Calls `ResearchManager().run(query)` (similar to `deep_research.py`, but without the UI).
   - Captures the final `markdown_report` and metadata (trace ID, runtime).

3. For each report, compute **automatic checks** such as:
   - Word count (e.g., `>= 800` words).
   - Section structure (contains headings like `Introduction`, `Conclusion`).
   - Presence of **sources / citations** (URLs or reference markers).

4. Optionally, run a **model‑graded eval**:
   - Ask a separate model:  
     “On a 1–5 scale, how well does this report answer the query? Explain briefly.”
   - Store both the numeric score and explanation.

5. Summarize results:
   - Average score across queries.
   - Queries where the score or automatic checks fall below thresholds.

This gives you a quick **quality regression test** whenever you change prompts or models.

---

#### 4.2 Planner agent eval

**Goal**: Ensure `planner_agent` proposes useful, on‑topic, non‑redundant searches.

1. Create a small dataset `evals/planner_prompts.jsonl`:

   ```json
   {"id": "agentic_frameworks", "query": "What are top 4 Agentic AI frameworks in 2026?"}
   {"id": "finetuning_vs_rag", "query": "When should I use fine‑tuning vs RAG?"}
   {"id": "startup_pricing", "query": "How should an AI SaaS startup think about pricing?"}
   ```

2. Write a script that:
   - Calls `Runner.run(planner_agent, f"Query: {query}")`.
   - Converts to `WebSearchPlan`.

3. For each plan, compute checks like:
   - Exactly `HOW_MANY_SEARCHES` entries.
   - All `query` fields are non‑empty and reasonably distinct (e.g., Jaccard similarity below a threshold).
   - `reason` fields mention the main topic/topics of the original query.

4. Flag any cases where:
   - Searches are obviously off‑topic.
   - All searches are near‑duplicates.

This helps keep the **search phase focused and diverse**, which directly impacts overall report quality and cost.

---

#### 4.3 Search agent eval

**Goal**: Ensure each search summary is concise, factual, and tool‑backed.

1. Reuse the `planner` eval dataset or create a dedicated set of `(search term, reason)` pairs.

2. Call the search agent the way `ResearchManager.search` does:

   ```python
   input_text = f"Search term: {query}\nReason for searching: {reason}"
   result = await Runner.run(search_agent, input_text)
   summary = str(result.final_output)
   ```

3. Evaluate each summary via:
   - Automatic checks (e.g., length in tokens/words, presence of at least one URL).
   - Optional model‑graded questions like:
     - “Is this summary concise (≤ 300 words) while covering the key aspects of the search term?”
     - “Does this summary clearly separate fact from speculation?”

You can run this eval after changes to `search_agent` instructions or `WebSearchTool` configuration.

---

#### 4.4 Writer agent eval

**Goal**: Ensure `writer_agent` produces structured, long‑form, on‑topic reports.

1. Build synthetic inputs that mimic what `ResearchManager.write_report` sends:

   ```python
   fake_summaries = [
       "Summary 1 about framework A, B, C...",
       "Summary 2 about trends in 2026...",
       "Summary 3 about adoption and use cases..."
   ]
   input_text = (
       "Original query: What are top 4 Agentic AI frameworks in 2026?\n"
       f"Summarized search results: {fake_summaries}"
   )
   ```

2. Call `Runner.run(writer_agent, input_text)` and inspect `ReportData`:
   - `short_summary` length and clarity.
   - `markdown_report` length, headings, organization.
   - `follow_up_questions` relevance and diversity.

3. Evaluate via:
   - Simple regex/heuristics (e.g., must contain at least 3 headings).
   - Model‑graded scores for:
     - **Relevance** to the original query.
     - **Depth / completeness**.
     - **Clarity / structure**.

This lets you iterate on the **writer prompt** and report format without running the full web search pipeline every time.

---

#### 4.5 Safety / policy eval

**Goal**: Ensure the system handles risky or out‑of‑scope inputs safely.

1. Create a small set of **adversarial or policy‑sensitive queries**, e.g.:
   - Requests for personal data.
   - Disallowed topics (depending on your policy).
   - Nonsensical or extremely long inputs.

2. Run:
   - End‑to‑end, or
   - Only the planner + writer agents (with dummy search data).

3. Check that:
   - The system **refuses** or **deflects** unsafe requests.
   - Reports include appropriate **disclaimers** when information is uncertain.

You can combine this with the **guardrails** in `GUARDRAILS.md` (e.g., input validation, topic filters) and verify they work.

---

#### 4.6 LLM‑level evals (model behavior only)

Sometimes you want to evaluate the **raw model behavior** (e.g. `gpt‑4o‑mini`) independent of tools and orchestration. Typical checks:

- **Instruction following** – Does the model respect style/formatting constraints?
- **Reasoning quality** – For smaller tasks, does it reach the right answer?
- **Policy adherence** – Does it refuse disallowed requests?

Examples for this project:

- Take the **writer prompt** (from `writer_agent.py`) and run it on **shorter synthetic tasks** in a notebook:
  - Ask it to write a 2‑paragraph summary instead of a full report.
  - Score the result with a rubric (or another model) for clarity and structure.
- Evaluate different models (e.g., `gpt‑4o‑mini` vs a larger model) on the same small tasks and log:
  - Quality score (human or model‑graded).
  - Latency.
  - Cost.

You can do the same with the **planner** and **search** instructions by calling the underlying model directly (bypassing tools) to compare how different models behave before wiring them back into the full Deep Research pipeline.

---

### 5. How to run evals in practice

You can start simple and evolve over time. Below are **concrete, minimal examples** you can adapt.

- **Example A – End‑to‑end eval script**

  Create `evals/run_end_to_end.py`:

  ```python
  # evals/run_end_to_end.py
  import asyncio
  from research_manager import ResearchManager

  QUERIES = [
      "What are top 4 Agentic AI frameworks in 2026?",
      "Explain RLHF (Reinforcement Learning from Human Feedback) to a senior engineer.",
  ]

  async def run_one(query: str) -> dict:
      manager = ResearchManager()
      final_report = None
      async for chunk in manager.run(query):
          final_report = chunk
      text = str(final_report)
      return {
          "query": query,
          "word_count": len(text.split()),
          "has_introduction": "# Introduction" in text or "## Introduction" in text,
      }

  async def main():
      results = [await run_one(q) for q in QUERIES]
      for r in results:
          print(f"Query: {r['query']}")
          print(f"  word_count={r['word_count']}, has_introduction={r['has_introduction']}")

  if __name__ == "__main__":
      asyncio.run(main())
  ```

  Run:

  ```bash
  uv run python evals/run_end_to_end.py
  ```

  and check that each query meets your simple thresholds (e.g., `word_count >= 800`).

- **Example B – Planner agent eval**

  Create `evals/run_planner_eval.py`:

  ```python
  # evals/run_planner_eval.py
  import asyncio
  from planner_agent import planner_agent, WebSearchPlan
  from agents import Runner

  QUERIES = [
      "What are top 4 Agentic AI frameworks in 2026?",
      "When should I use fine-tuning vs RAG?",
  ]

  async def eval_planner(query: str):
      result = await Runner.run(planner_agent, f"Query: {query}")
      plan = result.final_output_as(WebSearchPlan)
      queries = [item.query for item in plan.searches]
      unique_queries = set(queries)
      print(f"\nQuery: {query}")
      print(f"  searches={len(queries)}, unique={len(unique_queries)}")
      for q in queries:
          print(f"   - {q}")

  async def main():
      for q in QUERIES:
          await eval_planner(q)

  if __name__ == "__main__":
      asyncio.run(main())
  ```

  This lets you **eyeball** whether the planner is proposing useful, diverse searches whenever you change its prompt or model.

- **Example C – Writer agent eval**

  Create `evals/run_writer_eval.py`:

  ```python
  # evals/run_writer_eval.py
  import asyncio
  from writer_agent import writer_agent, ReportData
  from agents import Runner

  async def main():
      fake_summaries = [
          "Summary about major Agentic AI frameworks and their capabilities.",
          "Summary about trends and adoption in 2026.",
          "Summary about developer experience and ecosystem support.",
      ]
      input_text = (
          "Original query: What are top 4 Agentic AI frameworks in 2026?\n"
          f"Summarized search results: {fake_summaries}"
      )
      result = await Runner.run(writer_agent, input_text)
      report: ReportData = result.final_output_as(ReportData)
      words = len(report.markdown_report.split())
      has_headings = "#" in report.markdown_report
      print(f"short_summary: {report.short_summary[:120]}...")
      print(f"word_count={words}, has_headings={has_headings}")

  if __name__ == "__main__":
      asyncio.run(main())
  ```

  Run this after changing the writer prompt to ensure it still produces long, well‑structured reports even when given synthetic inputs.

- **Phase 1 – Manual / notebook‑based (optional)**
  - For quick experiments, you can copy the logic above into a notebook, tweak prompts/models, and re‑run cells by hand.

- **Phase 2 – Scripted evals**
  - Store eval inputs as JSON/CSV.
  - Write small Python scripts that:
    - Run all test cases.
    - Save outputs and metrics to disk (e.g., JSONL or CSV).
  - Run these scripts before committing major prompt/model changes.

- **Phase 3 – Integrated evals**
  - Integrate eval scripts into your **CI pipeline** (see `.github/workflows/ci.yml`).
  - Add a lightweight check, such as:
    - “Average model‑graded score must be ≥ 4.0.”
    - “No safety eval case may fail.”

You do not need a heavy framework to get value; the key is to have **repeatable tests** tied to the specific behavior you care about.

---

### 6. Next steps

If you want to extend evals for this project, consider:

- Adding a `evals/` folder with:
  - Input datasets (JSONL).
  - Python scripts for each eval type.
  - A small README describing how to run them.
- Logging trace IDs for each eval run so you can jump straight from a failing eval case to its **trace / logs** in the OpenAI dashboard.

With even a small set of well‑chosen evals, you can safely iterate on prompts, models, and guardrails while keeping the Deep Research experience high‑quality and predictable.

