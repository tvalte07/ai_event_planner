"""Independent nodes used by the sequential LangGraph workflow."""
from app.agents.state import PlannerState
from app.services.event_planner import allocate_budget, recommend_venues, generate_schedule, validate_event
from app.llm.ollama_client import OllamaClient

def validate_node(s: PlannerState) -> PlannerState:
    try:
        validate_event(s['request'])
        return {}
    except ValueError as exc:
        return {'validation_error': str(exc)}
def budget_node(s: PlannerState) -> PlannerState:
    return {'budget': '\n'.join(f'{x.category}: ₹{x.amount}' for x in allocate_budget(s['request'].budget))}
def venue_node(s: PlannerState) -> PlannerState:
    r=s['request']; vs=recommend_venues(r,allocate_budget(r.budget))
    return {'venues': '\n'.join(v.category for v in vs) or 'No matching sample category'}
def schedule_node(s: PlannerState) -> PlannerState:
    return {'schedule': '\n'.join(f'{x.start}-{x.end} {x.activity}' for x in generate_schedule(s['request']))}
def manager_node(s: PlannerState) -> PlannerState:
    r = s['request']
    prompt = (
        "Create a concise event plan from these provided details. Treat budget allocations and venue categories as "
        "illustrative. Do not invent prices, specific venues, availability, contacts, or bookings.\n"
        f"Event: {r.name}; type: {r.event_type}; date: {r.event_date}; location: {r.location}; guests: {r.guest_count}.\n"
        f"Budget:\n{s['budget']}\nSample venue categories:\n{s['venues']}\nSchedule:\n{s['schedule']}\n"
        f"Preferences: {r.preferences}; {r.food_preference}; {r.decoration_style}.\n"
        f"Additional requirements: {r.additional_requirements}"
    )
    return {'final_plan': OllamaClient().generate(prompt)}
