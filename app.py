"""PawPal+ Streamlit UI — wired to pawpal_system.py backend logic."""

import os
from datetime import date

from dotenv import load_dotenv
import streamlit as st

load_dotenv()

from pawpal_system import Owner, Pet, Task, Scheduler
from rag import ask as rag_ask

# ------------------------------------------------------------------ #
# Page config
# ------------------------------------------------------------------ #
st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")

# ------------------------------------------------------------------ #
# Session-state initialisation
# Store Owner (and therefore all pets/tasks) in st.session_state so
# data persists across Streamlit reruns.
# ------------------------------------------------------------------ #
if "owner" not in st.session_state:
    st.session_state.owner = None  # set when the user fills in their name

# ------------------------------------------------------------------ #
# Sidebar — Owner & pet management
# ------------------------------------------------------------------ #
with st.sidebar:
    st.header("🐾 PawPal+")

    # Owner setup
    st.subheader("Owner")
    owner_name = st.text_input("Your name", value="Jordan")
    if st.button("Set / update owner"):
        if st.session_state.owner is None:
            st.session_state.owner = Owner(owner_name)
        else:
            st.session_state.owner.name = owner_name
        st.success(f"Owner set to **{owner_name}**")

    if st.session_state.owner is None:
        st.info("Set your name above to get started.")
        st.stop()

    owner: Owner = st.session_state.owner

    st.divider()

    # Add a pet
    st.subheader("Add a Pet")
    pet_name_input = st.text_input("Pet name", key="new_pet_name")
    species_input = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"],
                                 key="new_pet_species")
    if st.button("Add pet"):
        if pet_name_input.strip() == "":
            st.warning("Enter a pet name.")
        elif owner.get_pet(pet_name_input.strip()) is not None:
            st.warning(f"**{pet_name_input}** is already in your roster.")
        else:
            owner.add_pet(Pet(pet_name_input.strip(), species_input))
            st.success(f"Added **{pet_name_input}** ({species_input})")

    if owner.pets:
        st.divider()
        st.subheader("Your Pets")
        for pet in owner.pets:
            st.write(f"• {pet.name} ({pet.species})")

# ------------------------------------------------------------------ #
# Main area
# ------------------------------------------------------------------ #
st.title(f"🐾 PawPal+ — {owner.name}'s Dashboard")

if not owner.pets:
    st.info("Add at least one pet in the sidebar to get started.")
    st.stop()

scheduler = Scheduler(owner)

# Tabs for clean navigation
tab_schedule, tab_add, tab_manage, tab_ai = st.tabs(
    ["📅 Today's Schedule", "➕ Add Task", "🔧 Manage Tasks", "🤖 Pet Care Assistant"]
)

# ------------------------------------------------------------------ #
# Tab 1 — Today's Schedule
# ------------------------------------------------------------------ #
with tab_schedule:
    st.subheader("Today's Schedule")

    # Conflict warnings — shown prominently at the top
    warnings = scheduler.get_conflict_warnings()
    if warnings:
        for w in warnings:
            st.warning(f"⚠ {w}")

    schedule = scheduler.get_today_schedule()

    if not schedule:
        st.info("No tasks due today. Add some tasks in the **Add Task** tab.")
    else:
        # Priority-colour legend
        priority_colour = {"high": "🔴", "medium": "🟡", "low": "🟢"}

        for task in schedule:
            col_info, col_btn = st.columns([5, 1])
            with col_info:
                badge = priority_colour.get(task.priority, "⚪")
                st.markdown(
                    f"{badge} **{task.time}** — {task.description} &nbsp;"
                    f"*({task.pet_name}, {task.duration_minutes} min, {task.priority})*"
                )
            with col_btn:
                if st.button("✓ Done", key=f"done_{task.id}"):
                    next_task = scheduler.mark_task_complete(task.id)
                    if next_task:
                        st.success(
                            f"Done! Next '{task.description}' scheduled for "
                            f"{next_task.due_date} ({task.frequency})."
                        )
                    else:
                        st.success(f"'{task.description}' marked complete.")
                    st.rerun()

    st.divider()

    # Filter controls
    st.subheader("Filter & Explore")
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filter_pet = st.selectbox(
            "Filter by pet",
            ["All"] + [p.name for p in owner.pets],
            key="filter_pet",
        )
    with col_f2:
        filter_status = st.selectbox(
            "Filter by status",
            ["All", "Incomplete", "Completed"],
            key="filter_status",
        )
    with col_f3:
        filter_priority = st.selectbox(
            "Filter by priority",
            ["All", "high", "medium", "low"],
            key="filter_priority",
        )

    # Apply filters
    filtered = owner.get_all_tasks()

    if filter_pet != "All":
        filtered = [t for t in filtered if t.pet_name == filter_pet]
    if filter_status == "Incomplete":
        filtered = [t for t in filtered if not t.completed]
    elif filter_status == "Completed":
        filtered = [t for t in filtered if t.completed]
    if filter_priority != "All":
        filtered = [t for t in filtered if t.priority == filter_priority]

    filtered = scheduler.sort_by_time(filtered)

    if filtered:
        rows = [
            {
                "Time": t.time,
                "Task": t.description,
                "Pet": t.pet_name,
                "Duration (min)": t.duration_minutes,
                "Priority": t.priority,
                "Frequency": t.frequency,
                "Due": str(t.due_date),
                "Done": "✓" if t.completed else "",
            }
            for t in filtered
        ]
        st.table(rows)
    else:
        st.info("No tasks match your filters.")

# ------------------------------------------------------------------ #
# Tab 2 — Add Task
# ------------------------------------------------------------------ #
with tab_add:
    st.subheader("Schedule a New Task")

    with st.form("add_task_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            new_desc = st.text_input("Task description", placeholder="e.g. Morning walk")
            new_pet = st.selectbox("Pet", [p.name for p in owner.pets])
            new_time = st.text_input("Time (HH:MM)", value="08:00")
        with col2:
            new_duration = st.number_input("Duration (minutes)", min_value=1, max_value=480, value=30)
            new_priority = st.selectbox("Priority", ["high", "medium", "low"])
            new_frequency = st.selectbox("Frequency", ["once", "daily", "weekly"])

        new_due = st.date_input("Due date", value=date.today())

        submitted = st.form_submit_button("Add Task")
        if submitted:
            if new_desc.strip() == "":
                st.error("Task description cannot be empty.")
            else:
                # Validate time format
                parts = new_time.strip().split(":")
                if len(parts) != 2 or not all(p.isdigit() for p in parts):
                    st.error("Time must be in HH:MM format (e.g. 08:00).")
                else:
                    pet_obj = owner.get_pet(new_pet)
                    task = Task(
                        description=new_desc.strip(),
                        time=new_time.strip(),
                        duration_minutes=int(new_duration),
                        priority=new_priority,
                        frequency=new_frequency,
                        pet_name=new_pet,
                        due_date=new_due,
                    )
                    pet_obj.add_task(task)
                    st.success(f"Added '{task.description}' for {new_pet} at {new_time}.")

# ------------------------------------------------------------------ #
# Tab 3 — Manage Tasks
# ------------------------------------------------------------------ #
with tab_manage:
    st.subheader("Manage Existing Tasks")

    all_tasks = owner.get_all_tasks()
    if not all_tasks:
        st.info("No tasks yet. Add some in the **Add Task** tab.")
    else:
        manage_pet = st.selectbox(
            "Show tasks for",
            ["All"] + [p.name for p in owner.pets],
            key="manage_pet",
        )

        display_tasks = (
            owner.get_all_tasks()
            if manage_pet == "All"
            else scheduler.filter_by_pet(manage_pet)
        )
        display_tasks = scheduler.sort_by_time(display_tasks)

        for task in display_tasks:
            with st.expander(
                f"{'✓' if task.completed else '○'} {task.time} — {task.description} ({task.pet_name})"
            ):
                col_a, col_b = st.columns(2)
                col_a.write(f"**Duration:** {task.duration_minutes} min")
                col_a.write(f"**Priority:** {task.priority}")
                col_b.write(f"**Frequency:** {task.frequency}")
                col_b.write(f"**Due:** {task.due_date}")
                col_b.write(f"**Status:** {'Completed' if task.completed else 'Pending'}")

                col_done, col_del = st.columns(2)
                with col_done:
                    if not task.completed:
                        if st.button("Mark complete", key=f"mgr_done_{task.id}"):
                            scheduler.mark_task_complete(task.id)
                            st.rerun()
                with col_del:
                    if st.button("Delete", key=f"mgr_del_{task.id}"):
                        pet_obj = owner.get_pet(task.pet_name)
                        if pet_obj:
                            pet_obj.remove_task(task.id)
                        st.rerun()

# ------------------------------------------------------------------ #
# Tab 4 — Pet Care Assistant (RAG)
# ------------------------------------------------------------------ #
with tab_ai:
    st.subheader("🤖 Pet Care Assistant")
    st.caption(
        "Ask anything about feeding, medications, exercise, grooming, or vet visits. "
        "Answers are grounded in PawPal+'s built-in pet care knowledge base."
    )

    api_key_set = bool(os.environ.get("GOOGLE_API_KEY", "").strip())
    if not api_key_set:
        st.error(
            "**GOOGLE_API_KEY not set.** "
            "Export it in your terminal before launching the app:\n\n"
            "```\nexport GOOGLE_API_KEY=AIza...\nstreamlit run app.py\n```"
        )
    else:
        # Build pet context string so Claude knows which animals this owner has
        pet_context = ", ".join(
            f"{p.name} ({p.species})" for p in owner.pets
        ) if owner.pets else ""

        # Session-state chat history: list of {"role": "user"|"assistant", ...}
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        # Render existing conversation
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg["role"] == "assistant" and msg.get("sources"):
                    with st.expander("📚 Sources retrieved from knowledge base"):
                        for src in msg["sources"]:
                            st.markdown(f"**{src['source'].capitalize()}**")
                            st.markdown(src["content"][:400] + ("…" if len(src["content"]) > 400 else ""))
                            st.divider()

        # Input box
        user_input = st.chat_input("e.g. How often should I walk my dog?")
        if user_input:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            with st.chat_message("assistant"):
                with st.spinner("Looking up pet care info…"):
                    try:
                        answer, sources = rag_ask(user_input, pet_context=pet_context)
                        st.markdown(answer)
                        if sources:
                            with st.expander("📚 Sources retrieved from knowledge base"):
                                for src in sources:
                                    st.markdown(f"**{src['source'].capitalize()}**")
                                    st.markdown(src["content"][:400] + ("…" if len(src["content"]) > 400 else ""))
                                    st.divider()
                        st.session_state.chat_history.append(
                            {"role": "assistant", "content": answer, "sources": sources}
                        )
                    except EnvironmentError as e:
                        st.error(str(e))
                    except Exception as e:
                        st.error(f"Something went wrong: {e}")

        if st.session_state.chat_history:
            if st.button("🗑 Clear conversation"):
                st.session_state.chat_history = []
                st.rerun()

# ------------------------------------------------------------------ #
# Footer
# ------------------------------------------------------------------ #
st.divider()
total = len(owner.get_all_tasks())
done = len(scheduler.filter_by_status(completed=True))
pending = total - done
st.caption(
    f"Total tasks: {total} &nbsp;|&nbsp; Completed: {done} &nbsp;|&nbsp; Pending: {pending}"
)
