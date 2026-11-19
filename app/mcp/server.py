"""FastMCP tools for event budgets, schedules, guests, events, and documents."""

from datetime import date, time, datetime, timezone
from typing import Literal

from fastmcp import FastMCP

from app.memory.database import MemoryDatabase
from app.services.event_planner import allocate_budget
from app.tools.document_tools import search_event_documents as search_local_documents
from app.tools.schedule_tools import generate_event_schedule


mcp = FastMCP("AI Event Planner")
database = MemoryDatabase()


@mcp.tool()
def calculate_event_budget(total_budget: int) -> dict:
    """Split a positive event budget into illustrative category allocations in whole rupees."""
    if total_budget <= 0:
        raise ValueError("Total budget must be greater than zero.")
    lines = allocate_budget(total_budget)
    return {"items": [{"category": x.category, "amount": x.amount, "share_percent": x.share_percent} for x in lines], "total": sum(x.amount for x in lines), "illustrative": True}


@mcp.tool()
def generate_event_schedule(event_type: str, event_date: str, start_time: str = "17:00") -> list[dict]:
    """Generate a timeline for a supported event type; provide ISO date and 24-hour time."""
    try:
        day = date.fromisoformat(event_date)
        start = time.fromisoformat(start_time)
    except ValueError as exc:
        raise ValueError("Use YYYY-MM-DD for date and HH:MM for start_time.") from exc
    items = generate_event_schedule(event_type, day, start)
    return [{"start": x.start, "end": x.end, "activity": x.activity} for x in items]


@mcp.tool()
def manage_guest_list(action: Literal["add", "list"], event_id: int, guest_name: str = "", contact: str = "", rsvp_status: Literal["pending", "accepted", "declined"] = "pending", dietary_notes: str = "") -> dict:
    """Add or list guests for an existing local event. Add requires guest_name; event_id comes from get_event_details."""
    if event_id <= 0:
        raise ValueError("event_id must be a positive event record ID.")
    with database.connection() as connection:
        if connection.execute("SELECT 1 FROM planned_events WHERE id=?", (event_id,)).fetchone() is None:
            raise ValueError("Event was not found in local memory.")
        if action == "add":
            if not guest_name.strip():
                raise ValueError("guest_name is required when adding a guest.")
            connection.execute("""INSERT INTO event_guests(event_id,guest_name,contact,rsvp_status,dietary_notes,created_at)
                VALUES(?,?,?,?,?,?) ON CONFLICT(event_id,guest_name) DO UPDATE SET contact=excluded.contact,
                rsvp_status=excluded.rsvp_status,dietary_notes=excluded.dietary_notes""",
                (event_id, guest_name.strip(), contact.strip(), rsvp_status, dietary_notes.strip(), datetime.now(timezone.utc).isoformat(timespec="seconds")))
        rows = connection.execute("SELECT guest_name,contact,rsvp_status,dietary_notes FROM event_guests WHERE event_id=? ORDER BY guest_name", (event_id,)).fetchall()
        return {"event_id": event_id, "guests": [dict(row) for row in rows], "count": len(rows)}


@mcp.tool()
def get_event_details(event_id: int) -> dict:
    """Get a saved event by its numeric local event_id from SQLite memory."""
    if event_id <= 0:
        raise ValueError("event_id must be a positive integer.")
    with database.connection() as connection:
        row = connection.execute("SELECT id,name,event_type,event_date,location,guest_count,budget,created_at FROM planned_events WHERE id=?", (event_id,)).fetchone()
    if row is None:
        raise ValueError("Event was not found in local memory.")
    return dict(row)


@mcp.tool()
def search_event_documents(query: str, max_results: int = 10) -> list[dict]:
    """Search local TXT or Markdown files in data/uploads by literal phrase."""
    return [dict(file_name=x.file_name, line_number=x.line_number, excerpt=x.excerpt) for x in search_local_documents(query, max_results=max_results)]


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
