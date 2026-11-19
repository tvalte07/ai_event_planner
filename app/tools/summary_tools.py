"""Short event summary tool for UI, logs, and future agent nodes."""

from app.services.event_planner import EventPlan, EventRequest


def generate_event_summary(request: EventRequest, plan: EventPlan | None = None) -> str:
    """Summarize the plan when available, otherwise summarize the request."""
    if plan is not None:
        return plan.final_summary
    return (
        f"{request.name.strip()}: {request.event_type} on {request.event_date.isoformat()} in "
        f"{request.location.strip()}, for {request.guest_count} guests with a total budget of ₹{request.budget:,}."
    )
