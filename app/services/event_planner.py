"""Deterministic Phase 2 event planning logic, independent of the UI."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
import json
from pathlib import Path
from typing import Any


EVENT_TYPES = (
    "Birthday party",
    "Wedding",
    "Corporate event",
    "Team outing",
    "Anniversary",
    "Family function",
    "College event",
)

# Percentages are planning defaults, not market quotations.
BUDGET_SHARES: tuple[tuple[str, int], ...] = (
    ("Venue", 25),
    ("Food and catering", 35),
    ("Decoration", 12),
    ("Cake or occasion items", 6),
    ("Activities and entertainment", 10),
    ("Miscellaneous and contingency", 12),
)

SCHEDULE_TEMPLATES: dict[str, tuple[tuple[str, int], ...]] = {
    "Birthday party": (("Guest arrival and welcome", 30), ("Games and social time", 45), ("Cake cutting and photos", 30), ("Meal", 60), ("Music and closing", 45)),
    "Wedding": (("Guest arrival", 30), ("Ceremony", 60), ("Photos and greetings", 30), ("Meal", 75), ("Celebration and closing", 45)),
    "Corporate event": (("Arrival and registration", 30), ("Welcome and opening", 20), ("Talks or presentations", 60), ("Meal and networking", 60), ("Closing and departures", 40)),
    "Team outing": (("Arrival and welcome", 30), ("Icebreakers", 30), ("Team activities", 90), ("Meal and informal time", 60), ("Closing", 30)),
    "Anniversary": (("Guest arrival", 30), ("Welcome and mingling", 30), ("Toasts and celebration", 45), ("Meal", 60), ("Photos and closing", 45)),
    "Family function": (("Guest arrival", 30), ("Welcome and introductions", 30), ("Main ceremony or activities", 60), ("Meal", 75), ("Family photos and closing", 45)),
    "College event": (("Registration and arrival", 30), ("Opening remarks", 20), ("Performances or activities", 90), ("Refreshments and social time", 45), ("Closing", 25)),
}


@dataclass(frozen=True)
class EventRequest:
    name: str
    event_type: str
    event_date: date
    location: str
    guest_count: int
    budget: int
    preferences: str = ""
    additional_requirements: str = ""
    start_time: time = time(17, 0)
    food_preference: str = ""
    decoration_style: str = ""


@dataclass(frozen=True)
class BudgetLine:
    category: str
    amount: int
    share_percent: int


@dataclass(frozen=True)
class VenueOption:
    category: str
    capacity_min: int
    capacity_max: int
    reason: str
    selection_checks: tuple[str, ...]
    planning_allowance: int


@dataclass(frozen=True)
class ScheduleItem:
    start: str
    end: str
    activity: str


@dataclass(frozen=True)
class EventPlan:
    request: EventRequest
    budget: tuple[BudgetLine, ...]
    venues: tuple[VenueOption, ...]
    food_suggestions: tuple[str, ...]
    decoration_suggestions: tuple[str, ...]
    schedule: tuple[ScheduleItem, ...]
    guest_suggestions: tuple[str, ...]
    final_summary: str


def validate_event(request: EventRequest, today: date | None = None) -> None:
    """Raise ValueError with a user-readable message for invalid event details."""
    if not request.name.strip():
        raise ValueError("Enter an event name.")
    if request.event_type not in EVENT_TYPES:
        raise ValueError("Choose a supported event type.")
    if request.event_date < (today or date.today()):
        raise ValueError("Event date cannot be in the past.")
    if not request.location.strip():
        raise ValueError("Enter an event location.")
    if not 1 <= request.guest_count <= 5000:
        raise ValueError("Guest count must be between 1 and 5,000.")
    if request.budget <= 0:
        raise ValueError("Budget must be greater than zero.")


def allocate_budget(total: int) -> tuple[BudgetLine, ...]:
    """Allocate an integer-rupee budget and distribute rounding rupees exactly."""
    if total <= 0:
        raise ValueError("Budget must be greater than zero.")
    raw_amounts = [(name, total * share // 100, share, total * share % 100) for name, share in BUDGET_SHARES]
    remainder = total - sum(amount for _, amount, _, _ in raw_amounts)
    # Largest-remainder allocation keeps the total exact even for small budgets.
    remainder_order = sorted(range(len(raw_amounts)), key=lambda i: raw_amounts[i][3], reverse=True)
    extra_rupees = {index for index in remainder_order[:remainder]}
    return tuple(
        BudgetLine(name, amount + (1 if index in extra_rupees else 0), share)
        for index, (name, amount, share, _) in enumerate(raw_amounts)
    )


def recommend_venues(request: EventRequest, budget: tuple[BudgetLine, ...], data_path: Path | None = None) -> tuple[VenueOption, ...]:
    """Filter local sample venue categories by event type and guest capacity."""
    path = data_path or Path(__file__).resolve().parents[2] / "data" / "sample_venues.json"
    try:
        records: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not load sample venue categories from {path}.") from exc

    venue_allowance = next((line.amount for line in budget if line.category == "Venue"), 0)
    options = []
    for record in records:
        if request.event_type not in record["event_types"]:
            continue
        if not record["capacity_min"] <= request.guest_count <= record["capacity_max"]:
            continue
        options.append(VenueOption(
            category=record["category"],
            capacity_min=record["capacity_min"],
            capacity_max=record["capacity_max"],
            reason=record["reason"],
            selection_checks=tuple(record["selection_checks"]),
            planning_allowance=venue_allowance,
        ))
    return tuple(options)


def generate_schedule(request: EventRequest) -> tuple[ScheduleItem, ...]:
    """Create an event-specific timeline relative to the selected start time."""
    cursor = datetime.combine(request.event_date, request.start_time)
    items = []
    for activity, minutes in SCHEDULE_TEMPLATES[request.event_type]:
        end = cursor + timedelta(minutes=minutes)
        items.append(ScheduleItem(cursor.strftime("%I:%M %p"), end.strftime("%I:%M %p"), activity))
        cursor = end
    return tuple(items)


def _food_suggestions(request: EventRequest) -> tuple[str, ...]:
    preferences = f"{request.food_preference} {request.preferences}".casefold()
    if "non-vegetarian" in preferences or "non vegetarian" in preferences:
        menu = ["Offer a non-vegetarian main course alongside at least one vegetarian option."]
    elif "vegetarian" in preferences or "veg" in preferences:
        menu = ["Plan a vegetarian main course with a filling side and a lighter option."]
    else:
        menu = ["Ask the caterer for a balanced menu with vegetarian and non-vegetarian choices."]
    menu.extend(("Collect allergy and dietary requirements before confirming the menu.", "Confirm serving style, water, and a small buffer for late arrivals."))
    return tuple(menu)


def _decoration_suggestions(request: EventRequest) -> tuple[str, ...]:
    style = request.decoration_style.strip() or request.preferences.strip()
    if style:
        return (f"Use '{style}' as a starting point for the color palette and table details.", "Prioritize one photo or focal area and reusable table accents.")
    return ("Choose two or three coordinated colors suited to the event type.", "Prioritize one photo or focal area and reusable table accents.")


def _guest_suggestions(request: EventRequest) -> tuple[str, ...]:
    return (
        f"Track invitations and RSVPs for {request.guest_count} planned guests.",
        "Ask about dietary, accessibility, and seating needs with the RSVP.",
        "Send the confirmed address, arrival time, parking or transit details, and a reminder.",
    )


def create_event_plan(request: EventRequest, today: date | None = None, data_path: Path | None = None) -> EventPlan:
    """Validate an event and assemble a lightweight, fully local starter plan."""
    validate_event(request, today=today)
    budget = allocate_budget(request.budget)
    venues = recommend_venues(request, budget, data_path=data_path)
    schedule = generate_schedule(request)
    venue_summary = ", ".join(option.category for option in venues) if venues else "venue categories sized for this guest count"
    summary = (
        f"{request.name.strip()} is a {request.event_type.lower()} for {request.guest_count} guests "
        f"in {request.location.strip()} on {request.event_date.isoformat()}. "
        f"The illustrative budget allocation totals ₹{sum(line.amount for line in budget):,}; "
        f"sample venue categories to explore: {venue_summary}."
    )
    return EventPlan(
        request=request,
        budget=budget,
        venues=venues,
        food_suggestions=_food_suggestions(request),
        decoration_suggestions=_decoration_suggestions(request),
        schedule=schedule,
        guest_suggestions=_guest_suggestions(request),
        final_summary=summary,
    )
