"""Application-facing read/write operations for persistent event memory."""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.memory.database import MemoryDatabase, MemoryStorageError
from app.services.event_planner import EventRequest


DEFAULT_USER_ID = "local-user"


@dataclass(frozen=True)
class RecentEvent:
    name: str
    event_type: str
    event_date: str
    location: str
    guest_count: int
    budget: int
    created_at: str


@dataclass(frozen=True)
class UserMemory:
    preferred_food: str = ""
    preferred_decoration: str = ""
    preferred_location: str = ""
    typical_budget: int | None = None
    general_preferences: str = ""


class EventMemory:
    """Store event history and the latest explicitly provided preferences."""

    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database = MemoryDatabase(database_path)

    @staticmethod
    def _validate_user_id(user_id: str) -> str:
        normalized = user_id.strip()
        if not normalized or len(normalized) > 100:
            raise ValueError("User ID must contain 1 to 100 characters.")
        return normalized

    def record_event(self, request: EventRequest, user_id: str = DEFAULT_USER_ID) -> None:
        """Persist a plan request and refresh preferences that were provided."""
        user_id = self._validate_user_id(user_id)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        preferences = {
            "food": request.food_preference.strip(),
            "decoration": request.decoration_style.strip(),
            "location": request.location.strip(),
            "general": request.preferences.strip(),
        }
        try:
            with self.database.connection() as connection:
                connection.execute(
                    """INSERT INTO planned_events
                       (user_id, name, event_type, event_date, location, guest_count, budget,
                        food_preference, decoration_style, general_preferences,
                        additional_requirements, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (user_id, request.name.strip(), request.event_type, request.event_date.isoformat(),
                     request.location.strip(), request.guest_count, request.budget,
                     preferences["food"], preferences["decoration"], preferences["general"],
                     request.additional_requirements.strip(), now),
                )
                for key, value in preferences.items():
                    connection.execute(
                        """INSERT INTO user_preferences (user_id, preference_key, preference_value, updated_at)
                           VALUES (?, ?, ?, ?)
                           ON CONFLICT(user_id, preference_key) DO UPDATE SET
                               preference_value = excluded.preference_value,
                               updated_at = excluded.updated_at""",
                        (user_id, key, value, now),
                    )
                row = connection.execute(
                    "SELECT AVG(budget) AS average_budget FROM planned_events WHERE user_id = ?", (user_id,)
                ).fetchone()
                typical_budget = str(round(row["average_budget"]))
                connection.execute(
                    """INSERT INTO user_preferences (user_id, preference_key, preference_value, updated_at)
                       VALUES (?, 'typical_budget', ?, ?)
                       ON CONFLICT(user_id, preference_key) DO UPDATE SET
                           preference_value = excluded.preference_value,
                           updated_at = excluded.updated_at""",
                    (user_id, typical_budget, now),
                )
        except MemoryStorageError:
            raise

    def get_user_memory(self, user_id: str = DEFAULT_USER_ID) -> UserMemory:
        """Return saved preferences; a new user receives an empty memory object."""
        user_id = self._validate_user_id(user_id)
        try:
            with self.database.connection() as connection:
                rows = connection.execute(
                    "SELECT preference_key, preference_value FROM user_preferences WHERE user_id = ?", (user_id,)
                ).fetchall()
            values = {row["preference_key"]: row["preference_value"] for row in rows}
            try:
                typical_budget = int(values["typical_budget"]) if values.get("typical_budget") else None
            except ValueError:
                typical_budget = None
            return UserMemory(
                preferred_food=values.get("food", ""),
                preferred_decoration=values.get("decoration", ""),
                preferred_location=values.get("location", ""),
                typical_budget=typical_budget,
                general_preferences=values.get("general", ""),
            )
        except MemoryStorageError:
            raise

    def list_recent_events(self, user_id: str = DEFAULT_USER_ID, limit: int = 10) -> tuple[RecentEvent, ...]:
        """Return recent plans for one local profile, newest first."""
        user_id = self._validate_user_id(user_id)
        if not 1 <= limit <= 100:
            raise ValueError("Recent event limit must be between 1 and 100.")
        try:
            with self.database.connection() as connection:
                rows = connection.execute(
                    """SELECT name, event_type, event_date, location, guest_count, budget, created_at
                       FROM planned_events WHERE user_id = ?
                       ORDER BY created_at DESC, id DESC LIMIT ?""",
                    (user_id, limit),
                ).fetchall()
            return tuple(RecentEvent(**dict(row)) for row in rows)
        except MemoryStorageError:
            raise
