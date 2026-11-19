"""Guest count and invitation planning tools."""

from math import ceil


def calculate_invitation_target(expected_attendees: int, buffer_percent: int = 10) -> int:
    """Add a configurable invitation buffer to the expected attendance count."""
    if expected_attendees < 1:
        raise ValueError("Expected attendees must be at least one.")
    if not 0 <= buffer_percent <= 100:
        raise ValueError("Invitation buffer must be between 0% and 100%.")
    return ceil(expected_attendees * (100 + buffer_percent) / 100)
