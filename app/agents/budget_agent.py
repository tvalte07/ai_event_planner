from app.agents.state import PlannerState
from app.services.event_planner import allocate_budget


def budget_agent(state: PlannerState) -> PlannerState:
    budget = allocate_budget(state["request"].budget)
    lines = [f"{line.category}: ₹{line.amount:,} ({line.share_percent}%)" for line in budget]
    return {"budget_text": "\n".join(lines)}
