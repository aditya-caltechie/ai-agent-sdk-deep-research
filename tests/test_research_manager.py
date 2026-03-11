import asyncio
from types import SimpleNamespace

from planner_agent import WebSearchItem, WebSearchPlan, planner_agent
from writer_agent import ReportData, writer_agent
from email_agent import email_agent
from research_manager import ResearchManager


class DummyResult:
    def __init__(self, final_output):
        self.final_output = final_output

    def final_output_as(self, _type):
        # For these tests we just return the stored object,
        # ignoring the requested type.
        return self.final_output


def test_plan_searches_uses_runner_and_returns_plan(monkeypatch):
    manager = ResearchManager()

    expected_plan = WebSearchPlan(
        searches=[
            WebSearchItem(reason="reason 1", query="query 1"),
            WebSearchItem(reason="reason 2", query="query 2"),
        ]
    )

    async def fake_run(agent, input_text):
        assert agent is planner_agent
        assert "Query:" in input_text
        return DummyResult(expected_plan)

    monkeypatch.setattr(
        "research_manager.Runner",
        SimpleNamespace(run=fake_run),
    )

    result_plan = asyncio.run(manager.plan_searches("some query"))

    assert isinstance(result_plan, WebSearchPlan)
    assert len(result_plan.searches) == 2
    assert result_plan.searches[0].query == "query 1"


def test_perform_searches_gathers_results_and_skips_none():
    manager = ResearchManager()

    search_items = WebSearchPlan(
        searches=[
            WebSearchItem(reason="ok", query="ok-query"),
            WebSearchItem(reason="skip", query="skip-query"),
        ]
    )

    async def fake_search(item: WebSearchItem):
        if item.query == "skip-query":
            return None
        return f"result-for-{item.query}"

    # Override the instance method to avoid calling the real agent.
    manager.search = fake_search  # type: ignore[assignment]

    results = asyncio.run(manager.perform_searches(search_items))

    assert results == ["result-for-ok-query"]


def test_search_returns_string_on_success(monkeypatch):
    manager = ResearchManager()

    item = WebSearchItem(reason="r", query="q")

    async def fake_run(agent, input_text):
        assert "Search term:" in input_text
        return DummyResult(final_output="search-output")

    monkeypatch.setattr(
        "research_manager.Runner",
        SimpleNamespace(run=fake_run),
    )

    result = asyncio.run(manager.search(item))
    assert result == "search-output"


def test_search_returns_none_on_exception(monkeypatch):
    manager = ResearchManager()
    item = WebSearchItem(reason="r", query="q")

    async def fake_run(agent, input_text):
        raise RuntimeError("network error")

    monkeypatch.setattr(
        "research_manager.Runner",
        SimpleNamespace(run=fake_run),
    )

    result = asyncio.run(manager.search(item))
    assert result is None


def test_write_report_returns_report_data(monkeypatch):
    manager = ResearchManager()

    expected_report = ReportData(
        short_summary="summary",
        markdown_report="# Report",
        follow_up_questions=["q1", "q2"],
    )

    async def fake_run(agent, input_text):
        assert agent is writer_agent
        assert "Original query:" in input_text
        return DummyResult(expected_report)

    monkeypatch.setattr(
        "research_manager.Runner",
        SimpleNamespace(run=fake_run),
    )

    report = asyncio.run(manager.write_report("query", ["result"]))

    assert isinstance(report, ReportData)
    assert report.markdown_report.startswith("# Report")


def test_send_email_invokes_runner_with_email_agent(monkeypatch):
    manager = ResearchManager()

    report = ReportData(
        short_summary="summary",
        markdown_report="# Report body",
        follow_up_questions=[],
    )

    called = {}

    async def fake_run(agent, input_text):
        called["agent"] = agent
        called["input"] = input_text
        return DummyResult(final_output=None)

    monkeypatch.setattr(
        "research_manager.Runner",
        SimpleNamespace(run=fake_run),
    )

    result = asyncio.run(manager.send_email(report))

    assert called["agent"] is email_agent
    assert "# Report body" in called["input"]
    # The current implementation returns the report object.
    assert result is report

