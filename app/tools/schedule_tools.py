"""Reusable event schedule generation tool."""

from datetime import date, time

from app.services.event_planner import EVENT_TYPES, EventRequest, ScheduleItem, generate_schedule


def generate_event_schedule(
    event_type: str,
    event_date: date,
    start_time: time = time(17, 0),
) -> tuple[ScheduleItem, ...]:
    """Create a typed timeline for a supported event type."""
    if event_type not in EVENT_TYPES:
        raise ValueError("Choose a supported event type.")
    request = EventRequest(
        name="Schedule",
        event_type=event_type,
        event_date=event_date,
        location="",
        guest_count=1,
        budget=1,
        start_time=start_time,
    )
    return generate_schedule(request)
