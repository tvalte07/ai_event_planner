from datetime import date

import pytest

from app.agents import nodes
from app.services.event_planner import EventRequest


def request(**changes):
    values = dict(name="Test party", event_type="Birthday party", event_date=date(2030, 5, 10), location="Pune", guest_count=25, budget=25000)
    values.update(changes)
    return EventRequest(**values)


def test_specialist_nodes_return_sequential_planning_artifacts():
    state = {"request": request()}
    assert nodes.validate_node(state) == {}
    state.update(nodes.budget_node(state))
    state.update(nodes.venue_node(state))
    state.update(nodes.schedule_node(state))
    assert "Venue:" in state["budget"]
    assert "Community hall" in state["venues"]
    assert "Guest arrival" in state["schedule"]


def test_validation_routes_invalid_event_to_error_state():
    state = nodes.validate_node({"request": request(budget=0)})
    assert "validation_error" in state


def test_event_manager_uses_local_model_and_passes_guardrails(monkeypatch):
    captured = {}

    def fake_generate(self, prompt):
        captured["prompt"] = prompt
        return "Draft plan"

    monkeypatch.setattr(nodes.OllamaClient, "generate", fake_generate)
    result = nodes.manager_node({"request": request(), "budget": "Venue: ₹6250", "venues": "Community hall", "schedule": "5 PM arrival"})
    assert result["final_plan"] == "Draft plan"
    assert "Do not invent prices" in captured["prompt"]


def test_langgraph_validation_path_when_dependency_is_installed():
    pytest.importorskip("langgraph")
    try:
        from app.graph.workflow import run_event_workflow
        # Importing LangGraph may fail after its pure-Python package check when
        # Windows Application Control blocks its ormsgpack native extension.
        from langgraph.graph import StateGraph  # noqa: F401
    except (ImportError, OSError) as exc:
        pytest.skip(f"LangGraph native dependency unavailable in this environment: {exc}")
    with pytest.raises(ValueError, match="Budget"):
        run_event_workflow(request(budget=0))
