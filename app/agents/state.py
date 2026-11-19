from typing import TypedDict
from app.services.event_planner import EventRequest

class PlannerState(TypedDict, total=False):
    request: EventRequest
    validation_error: str
    budget: str
    venues: str
    schedule: str
    final_plan: str
