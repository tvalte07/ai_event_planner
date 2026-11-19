"""Sequential LangGraph orchestration for the local event planner."""
from app.agents.nodes import budget_node, manager_node, schedule_node, validate_node, venue_node

def build_workflow():
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise RuntimeError(
            "LangGraph could not load. Check its installation and whether Windows Application Control "
            "blocked a native dependency such as ormsgpack."
        ) from exc
    from app.agents.state import PlannerState
    g=StateGraph(PlannerState)
    for name,node in [('validate',validate_node),('budget',budget_node),('venue',venue_node),('schedule',schedule_node),('manager',manager_node)]: g.add_node(name,node)
    g.add_edge(START,'validate')
    g.add_conditional_edges('validate',lambda s:'error' if s.get('validation_error') else 'budget',{'error':END,'budget':'budget'})
    g.add_edge('budget','venue'); g.add_edge('venue','schedule'); g.add_edge('schedule','manager'); g.add_edge('manager',END)
    return g.compile()


def run_event_workflow(request):
    result = build_workflow().invoke({'request': request})
    if result.get('validation_error'):
        raise ValueError(result['validation_error'])
    return result
