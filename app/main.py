"""Streamlit interface for the Phase 2 event-planning MVP."""

import logging
from datetime import date, time, timedelta

import streamlit as st

from app.config import get_settings
from app.llm.ollama_client import OllamaClient, OllamaError
from app.memory.database import MemoryStorageError
from app.memory.memory_manager import DEFAULT_USER_ID, EventMemory, UserMemory
from app.services.event_planner import EVENT_TYPES, EventPlan, EventRequest, create_event_plan


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@st.cache_resource
def get_ollama_client() -> OllamaClient:
    """Reuse one lightweight client instance across Streamlit reruns."""
    return OllamaClient()


@st.cache_resource
def get_event_memory() -> EventMemory:
    """Reuse the SQLite memory manager across Streamlit reruns."""
    return EventMemory()


@st.cache_resource
def get_vector_store():
    from app.rag.vector_store import EventVectorStore
    return EventVectorStore()


def _show_plan(plan: EventPlan) -> None:
    request = plan.request
    st.header("Your starter event plan")
    st.subheader("Event overview")
    st.write(plan.final_summary)
    if request.food_preference:
        st.caption(f"Food preference: {request.food_preference}")
    if request.decoration_style:
        st.caption(f"Decoration style: {request.decoration_style}")
    if request.preferences:
        st.caption(f"Other preferences: {request.preferences}")
    if request.additional_requirements:
        st.caption(f"Additional requirements: {request.additional_requirements}")

    st.subheader("Illustrative budget breakdown")
    st.caption("Planning allocation only. These amounts are not vendor quotes or verified market prices.")
    st.dataframe(
        [{"Category": item.category, "Allocation (₹)": item.amount, "Share": f"{item.share_percent}%"} for item in plan.budget],
        hide_index=True,
        use_container_width=True,
    )
    st.metric("Total allocated", f"₹{sum(item.amount for item in plan.budget):,}")
    st.bar_chart(
        [{"Category": item.category, "Allocation": item.amount} for item in plan.budget],
        x="Category",
        y="Allocation",
        horizontal=True,
    )

    st.subheader("Venue categories to explore")
    st.caption(
        f"These are locally stored sample categories for {request.location}; no real venues, availability, or prices were searched. "
        "The allowance shown is the overall venue portion of your planning budget."
    )
    if plan.venues:
        for venue in plan.venues:
            with st.expander(f"{venue.category} · sample capacity {venue.capacity_min}–{venue.capacity_max}"):
                st.write(venue.reason)
                st.write(f"Illustrative venue budget allocation: ₹{venue.planning_allowance:,}")
                st.markdown("**Questions to check with a venue**")
                for check in venue.selection_checks:
                    st.markdown(f"- {check}")
    else:
        st.info("No sample category exactly matches this guest count and event type. Ask local venues about capacity, or revise the guest count.")

    left, right = st.columns(2)
    with left:
        st.subheader("Food and catering")
        for suggestion in plan.food_suggestions:
            st.markdown(f"- {suggestion}")
    with right:
        st.subheader("Decoration")
        for suggestion in plan.decoration_suggestions:
            st.markdown(f"- {suggestion}")

    st.subheader("Event schedule")
    st.dataframe(
        [{"Start": item.start, "End": item.end, "Activity": item.activity} for item in plan.schedule],
        hide_index=True,
        use_container_width=True,
    )

    st.subheader("Guest management")
    for suggestion in plan.guest_suggestions:
        st.markdown(f"- {suggestion}")
    st.caption("This starter plan is generated from local rules and sample data. It does not verify vendors, prices, or availability.")


def main() -> None:
    settings = get_settings()
    st.set_page_config(page_title="AI Event Planner", page_icon="🎉", layout="wide")
    st.title("🎉 AI Event Planner Agent")
    st.write("Turn your event details into a practical first draft. Planning calculations run locally.")

    memory: EventMemory | None = None
    saved_memory = UserMemory()
    with st.sidebar:
        st.header("Local profile")
        user_id = st.text_input("Profile ID", value=DEFAULT_USER_ID, max_chars=100, help="A local label for separating saved preferences on this device; this is not authentication.")
        profile_id = user_id.strip() or DEFAULT_USER_ID
        try:
            memory = get_event_memory()
            saved_memory = memory.get_user_memory(profile_id)
        except (MemoryStorageError, ValueError) as exc:
            logger.warning("Local event memory is unavailable: %s", exc)
            st.warning("Local memory is unavailable for this session. You can still create a plan.")
        if saved_memory.typical_budget is not None:
            st.caption(f"Typical budget from saved plans: ₹{saved_memory.typical_budget:,}")
        if saved_memory.preferred_food or saved_memory.preferred_decoration:
            st.caption("Saved food and decoration preferences are prefilled below; edit them for this event.")

    with st.form("event_details"):
        st.subheader("Tell us about your event")
        name = st.text_input("Event name", placeholder="e.g. Ananya's birthday")
        event_type = st.selectbox("Event type", EVENT_TYPES)
        event_date = st.date_input("Event date", value=date.today() + timedelta(days=14), min_value=date.today())
        location = st.text_input("Event location", value=saved_memory.preferred_location, placeholder="City or area, e.g. Pune")
        first, second = st.columns(2)
        with first:
            guest_count = st.number_input("Number of guests", min_value=1, max_value=5000, value=30, step=1)
            budget = st.number_input("Total budget (₹)", min_value=1, value=saved_memory.typical_budget or 30000, step=1000)
        with second:
            start_time = st.time_input("Event start time", value=time(17, 0), step=900)
            food_preference = st.text_input("Food preference", value=saved_memory.preferred_food, placeholder="e.g. vegetarian")
            decoration_style = st.text_input("Decoration style", value=saved_memory.preferred_decoration, placeholder="e.g. minimal, floral")
        preferences = st.text_input("Other preferences", value=saved_memory.general_preferences, placeholder="e.g. family-friendly activities")
        requirements = st.text_area("Additional requirements", placeholder="Accessibility, dietary needs, activities, or other notes")
        submitted = st.form_submit_button("Create event plan", type="primary", use_container_width=True)

    if submitted:
        request = EventRequest(
            name=name,
            event_type=event_type,
            event_date=event_date,
            location=location,
            guest_count=int(guest_count),
            budget=int(budget),
            preferences=preferences,
            additional_requirements=requirements,
            start_time=start_time,
            food_preference=food_preference,
            decoration_style=decoration_style,
        )
        try:
            plan = create_event_plan(request)
        except (ValueError, RuntimeError) as exc:
            st.error(str(exc))
            st.session_state.pop("event_plan", None)
            st.session_state.pop("event_plan_owner", None)
        else:
            st.session_state["event_plan"] = plan
            st.session_state["event_plan_owner"] = profile_id
            if memory is not None:
                try:
                    memory.record_event(request, profile_id)
                    st.success("Plan saved to local memory for this profile.")
                except MemoryStorageError as exc:
                    logger.warning("Could not save event memory: %s", exc)
                    st.warning("The plan was created, but it could not be saved to local memory.")

    if st.session_state.get("event_plan_owner") == profile_id and (plan := st.session_state.get("event_plan")):
        _show_plan(plan)
        st.subheader("Agent generated plan")
        if st.button("Generate consolidated AI plan"):
            try:
                from app.graph.workflow import run_event_workflow
                result = run_event_workflow(plan.request)
                st.session_state["agent_final_plan"] = result["final_plan"]
            except ModuleNotFoundError:
                st.error("LangGraph is not installed in this Python environment. Run `python -m pip install -r requirements.txt` and restart Streamlit.")
            except (ValueError, RuntimeError, OllamaError) as exc:
                st.error(str(exc))
        if st.session_state.get("agent_final_plan"):
            st.write(st.session_state["agent_final_plan"])

    if memory is not None:
        try:
            recent = memory.list_recent_events(profile_id, limit=10)
            with st.expander("Recent plans saved on this device"):
                if recent:
                    st.dataframe(
                        [{"Event": event.name, "Type": event.event_type, "Date": event.event_date,
                          "Location": event.location, "Guests": event.guest_count, "Budget (₹)": event.budget}
                         for event in recent],
                        hide_index=True,
                        use_container_width=True,
                    )
                else:
                    st.caption("No saved events for this profile yet.")
        except MemoryStorageError as exc:
            logger.warning("Could not load recent event memory: %s", exc)

    st.divider()
    st.header("Event documents and questions")
    uploads = st.file_uploader("Upload venue brochures, menus, or planning notes", type=["pdf", "txt"], accept_multiple_files=True)
    if uploads and st.button("Index uploaded documents"):
        for upload in uploads:
            try:
                from app.rag.chunking import split_text
                from app.rag.document_loader import extract_text_bytes
                text = extract_text_bytes(upload.name, upload.getvalue())
                chunks = split_text(text)
                count = get_vector_store().add_document(upload.name, chunks)
                st.success(f"Indexed {upload.name}: {count} text chunks.")
            except ModuleNotFoundError as exc:
                logger.warning("RAG dependency missing: %s", exc.name)
                st.error("RAG dependency is missing. Run `python -m pip install -r requirements.txt` in the same environment as Streamlit, then restart the app.")
            except (ValueError, RuntimeError) as exc:
                st.error(f"{upload.name}: {exc}")
            except Exception as exc:
                logger.exception("Document indexing failed")
                st.error(f"Could not index {upload.name}: {exc}")

    question = st.text_input("Ask a question answered by uploaded documents")
    if st.button("Search documents"):
        try:
            from app.rag.retriever import answer_from_documents
            answer, sources = answer_from_documents(question, get_vector_store())
            st.write(answer)
            if sources:
                st.caption("Retrieved excerpts: " + ", ".join(sorted({item["source"] for item in sources})))
        except ModuleNotFoundError as exc:
            logger.warning("RAG dependency missing: %s", exc.name)
            st.error("RAG dependency is missing. Run `python -m pip install -r requirements.txt` in the same environment as Streamlit, then restart the app.")
        except (ValueError, RuntimeError) as exc:
            st.error(str(exc))

    with st.expander("Local Ollama setup check"):
        st.caption(f"Provider: Ollama · Model: `{settings.ollama_model}` · URL: `{settings.ollama_base_url}`")
        if st.button("Check Ollama connection"):
            try:
                models = get_ollama_client().list_models()
                st.success("Connected to Ollama.")
                st.write("Installed models:", ", ".join(models) if models else "No models found.")
                if settings.ollama_model not in models:
                    st.info(f"Pull the configured model with `ollama pull {settings.ollama_model}`.")
            except OllamaError as exc:
                logger.warning("Ollama connectivity check failed: %s", exc)
                st.error(str(exc))

    with st.expander("FastAPI backend connection"):
        st.markdown("[Open API documentation](http://127.0.0.1:8000/docs)")
        if st.button("Load events from FastAPI"):
            try:
                from app.api.client import list_api_events
                st.dataframe(list_api_events(user_id=profile_id), hide_index=True, use_container_width=True)
            except RuntimeError as exc:
                st.error(str(exc))


if __name__ == "__main__":
    main()
