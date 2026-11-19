from datetime import date, time

import pytest

from app.services.event_planner import EventRequest
from app.tools.budget_tools import calculate_event_budget, validate_event_budget
from app.tools.document_tools import search_event_documents
from app.tools.guest_tools import calculate_invitation_target
from app.tools.schedule_tools import generate_event_schedule
from app.tools.summary_tools import generate_event_summary


def test_budget_tools_calculate_and_validate_allocations() -> None:
    allocation = calculate_event_budget(30000)

    assert sum(line.amount for line in allocation) == 30000
    assert validate_event_budget(30000, allocation).is_valid
    assert validate_event_budget(29000, allocation).remaining == -1000
    assert validate_event_budget(31000, allocation).remaining == 1000


@pytest.mark.parametrize("attendees,buffer,expected", [(30, 10, 33), (1, 10, 2), (25, 0, 25)])
def test_guest_invitation_target(attendees: int, buffer: int, expected: int) -> None:
    assert calculate_invitation_target(attendees, buffer) == expected


def test_guest_tool_rejects_invalid_counts_and_buffers() -> None:
    with pytest.raises(ValueError, match="at least one"):
        calculate_invitation_target(0)
    with pytest.raises(ValueError, match="between 0% and 100%"):
        calculate_invitation_target(5, 101)


def test_schedule_tool_uses_selected_event_type_and_start_time() -> None:
    schedule = generate_event_schedule("Birthday party", date(2030, 5, 20), time(18, 0))

    assert schedule[0].start == "06:00 PM"
    assert schedule[0].activity == "Guest arrival and welcome"
    assert schedule[-1].end == "09:30 PM"


def test_document_search_matches_text_and_skips_other_file_types(tmp_path) -> None:
    (tmp_path / "menu.txt").write_text("Vegetarian dinner options\nDessert menu", encoding="utf-8")
    (tmp_path / "notes.md").write_text("Ask about vegetarian meals", encoding="utf-8")
    (tmp_path / "brochure.pdf").write_text("vegetarian", encoding="utf-8")

    matches = search_event_documents("VEGETARIAN", tmp_path)

    assert [match.file_name for match in matches] == ["menu.txt", "notes.md"]
    assert matches[0].line_number == 1
    assert "Vegetarian" in matches[0].excerpt


def test_document_search_handles_missing_folder_and_validates_query(tmp_path) -> None:
    assert search_event_documents("catering", tmp_path / "missing") == ()
    with pytest.raises(ValueError, match="search query"):
        search_event_documents("  ", tmp_path)


def test_event_summary_tool_summarizes_request() -> None:
    request = EventRequest("Team lunch", "Corporate event", date(2030, 4, 3), "Pune", 18, 12000)

    summary = generate_event_summary(request)

    assert "Team lunch" in summary
    assert "18 guests" in summary
    assert "₹12,000" in summary
