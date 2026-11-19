"""SQLite persistence for planned events and per-user preferences."""

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Iterator


class MemoryStorageError(RuntimeError):
    """Raised when local memory cannot be read or written."""


class MemoryDatabase:
    """Small SQLite repository; connections are short-lived and per operation."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else Path(__file__).resolve().parents[2] / "data" / "planner_memory.sqlite3"
        self.initialize()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.path, timeout=5)
            connection.row_factory = sqlite3.Row
        except (OSError, sqlite3.Error) as exc:
            raise MemoryStorageError(f"Could not open the local memory database at {self.path}.") from exc

        try:
            yield connection
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise MemoryStorageError("Could not save or read local event memory.") from exc
        finally:
            connection.close()

    def initialize(self) -> None:
        """Create the minimal tables if this is a fresh installation."""
        try:
            with self.connection() as connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS planned_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        event_date TEXT NOT NULL,
                        location TEXT NOT NULL,
                        guest_count INTEGER NOT NULL,
                        budget INTEGER NOT NULL,
                        food_preference TEXT NOT NULL DEFAULT '',
                        decoration_style TEXT NOT NULL DEFAULT '',
                        general_preferences TEXT NOT NULL DEFAULT '',
                        additional_requirements TEXT NOT NULL DEFAULT '',
                        created_at TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_planned_events_user_created
                        ON planned_events(user_id, created_at DESC);
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        user_id TEXT NOT NULL,
                        preference_key TEXT NOT NULL,
                        preference_value TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        PRIMARY KEY (user_id, preference_key)
                    );
                    CREATE TABLE IF NOT EXISTS event_guests (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id INTEGER NOT NULL REFERENCES planned_events(id) ON DELETE CASCADE,
                        guest_name TEXT NOT NULL,
                        contact TEXT NOT NULL DEFAULT '',
                        rsvp_status TEXT NOT NULL DEFAULT 'pending',
                        dietary_notes TEXT NOT NULL DEFAULT '',
                        created_at TEXT NOT NULL,
                        UNIQUE(event_id, guest_name)
                    );
                    """
                )
        except MemoryStorageError:
            raise

