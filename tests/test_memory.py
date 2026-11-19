from datetime import date

import pytest

from app.memory.memory_manager import EventMemory
from app.services.event_planner import EventRequest


def request(**overrides: object) -> EventRequest:
    values: dict[str, object] = {
        "name": "Family birthday",
        "event_type": "Birthday party",
        "event_date": date(2030, 8, 12),
        "location": "Pune",
        "guest_count": 25,
        "budget": 25000,
        "food_preference": "Vegetarian",
        "decoration_style": "Minimal floral",
        "preferences": "Quiet music",
    }
    values.update(overrides)
    return EventRequest(**values)  # type: ignore[arg-type]


def test_empty_profile_returns_graceful_defaults(tmp_path) -> None:
    memory = EventMemory(tmp_path / "memory.sqlite3")

    assert memory.get_user_memory("new-user").typical_budget is None
    assert memory.list_recent_events("new-user") == ()


def test_preferences_and_history_persist_between_manager_instances(tmp_path) -> None:
    database_path = tmp_path / "nested" / "memory.sqlite3"
    EventMemory(database_path).record_event(request(), user_id="profile-a")

    memory = EventMemory(database_path)
    saved = memory.get_user_memory("profile-a")
    recent = memory.list_recent_events("profile-a")

    assert saved.preferred_food == "Vegetarian"
    assert saved.preferred_decoration == "Minimal floral"
    assert saved.preferred_location == "Pune"
    assert saved.typical_budget == 25000
    assert saved.general_preferences == "Quiet music"
    assert len(recent) == 1
    assert recent[0].name == "Family birthday"
    assert recent[0].budget == 25000


def test_profiles_are_isolated_and_typical_budget_averages_saved_plans(tmp_path) -> None:
    memory = EventMemory(tmp_path / "memory.sqlite3")
    memory.record_event(request(budget=20000), "profile-a")
    memory.record_event(request(name="Second event", budget=40000, food_preference="Vegan"), "profile-a")
    memory.record_event(request(food_preference="Omnivore"), "profile-b")

    assert memory.get_user_memory("profile-a").typical_budget == 30000
    assert memory.get_user_memory("profile-a").preferred_food == "Vegan"
    assert memory.get_user_memory("profile-b").preferred_food == "Omnivore"
    assert len(memory.list_recent_events("profile-a")) == 2
    assert len(memory.list_recent_events("profile-b")) == 1


def test_profile_id_and_history_limit_are_validated(tmp_path) -> None:
    memory = EventMemory(tmp_path / "memory.sqlite3")

    with pytest.raises(ValueError, match="User ID"):
        memory.get_user_memory("   ")
    with pytest.raises(ValueError, match="limit"):
        memory.list_recent_events(limit=0)


def test_blank_preference_clears_prefilled_saved_value(tmp_path) -> None:
    memory = EventMemory(tmp_path / "memory.sqlite3")
    memory.record_event(request(), "profile-a")
    memory.record_event(request(food_preference="", decoration_style=""), "profile-a")

    saved = memory.get_user_memory("profile-a")
    assert saved.preferred_food == ""
    assert saved.preferred_decoration == ""
