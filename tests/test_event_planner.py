from datetime import date, time

import pytest

from app.services.event_planner import (
    EVENT_TYPES,
    EventRequest,
    allocate_budget,
    create_event_plan,
    generate_schedule,
    validate_event,
)


def make_request(**overrides: object) -> EventRequest:
    values: dict[str, object] = {
        "name": "Birthday in Pune",
        "event_type": "Birthday party",
        "event_date": date(2030, 5, 20),
        "location": "Pune",
        "guest_count": 30,
        "budget": 30000,
        "preferences": "vegetarian, minimal decor",
        "additional_requirements": "Step-free access",
        "start_time": time(17, 0),
    }
    values.update(overrides)
    return EventRequest(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("total", [1, 7, 99, 30000, 1_000_003])
def test_budget_allocations_sum_to_total_for_small_and_large_amounts(total: int) -> None:
    allocations = allocate_budget(total)

    assert len(allocations) == 6
    assert sum(line.amount for line in allocations) == total
    assert all(line.amount >= 0 for line in allocations)


def test_budget_rejects_zero_or_negative_total() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        allocate_budget(0)


def test_event_validation_accepts_complete_details() -> None:
    validate_event(make_request(), today=date(2030, 1, 1))


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"name": " "}, "event name"),
        ({"event_type": "Retirement party"}, "event type"),
        ({"event_date": date(2029, 12, 31)}, "past"),
        ({"location": " "}, "location"),
        ({"guest_count": 0}, "Guest count"),
        ({"budget": -1}, "Budget"),
    ],
)
def test_event_validation_rejects_invalid_details(overrides: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        validate_event(make_request(**overrides), today=date(2030, 1, 1))


def test_schedule_is_sequential_and_starts_at_requested_time() -> None:
    schedule = generate_schedule(make_request())

    assert len(schedule) == 5
    assert schedule[0].start == "05:00 PM"
    assert schedule[0].end == schedule[1].start
    assert schedule[-1].activity == "Music and closing"


def test_plan_uses_local_venue_categories_and_marks_food_preferences() -> None:
    plan = create_event_plan(make_request(), today=date(2030, 1, 1))

    assert sum(line.amount for line in plan.budget) == 30000
    assert any(venue.category == "Community hall" for venue in plan.venues)
    assert all(venue.planning_allowance > 0 for venue in plan.venues)
    assert any("vegetarian" in item for item in plan.food_suggestions)
    assert plan.schedule[0].start == "05:00 PM"
    assert "Pune" in plan.final_summary


def test_non_vegetarian_preference_does_not_get_misread_as_vegetarian_only() -> None:
    plan = create_event_plan(make_request(preferences="non-vegetarian menu"), today=date(2030, 1, 1))

    assert "non-vegetarian main course" in plan.food_suggestions[0]


def test_plan_has_no_venue_match_when_capacity_exceeds_sample_categories() -> None:
    plan = create_event_plan(make_request(event_type=EVENT_TYPES[-1], guest_count=5000), today=date(2030, 1, 1))

    assert plan.venues == ()
