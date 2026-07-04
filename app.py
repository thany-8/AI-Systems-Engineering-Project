import streamlit as st
from pawpal_system import Owner, Pet, Task, Schedule

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

# ── Session-state vault ───────────────────────────────────────────────────────
# st.session_state behaves like a dictionary that survives page re-runs.
# The `not in` guard means we only create the objects ONCE; every subsequent
# re-run finds them already in the vault and skips the creation block.

if "owner" not in st.session_state:
    st.session_state.owner    = None   # set after the setup form
    st.session_state.schedule = None

# ── 1. Owner setup ────────────────────────────────────────────────────────────
st.subheader("Owner")

with st.form("owner_form"):
    col1, col2 = st.columns(2)
    with col1:
        owner_name = st.text_input("Name", value="Alice")
    with col2:
        owner_contact = st.text_input("Contact", value="alice@example.com")
    if st.form_submit_button("Save owner"):
        # Only create a new Owner when the form is submitted
        st.session_state.owner    = Owner(owner_name, owner_contact)
        st.session_state.schedule = Schedule(st.session_state.owner)
        st.success(f"Owner '{owner_name}' saved to session.")

if st.session_state.owner:
    st.caption(f"Current owner in session: **{st.session_state.owner}**")

st.divider()

# ── 2. Add a pet ──────────────────────────────────────────────────────────────
st.subheader("Add a Pet")

if not st.session_state.owner:
    st.info("Save an owner first.")
else:
    with st.form("pet_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            pet_name = st.text_input("Pet name", value="Max")
        with col2:
            pet_age = st.number_input("Age", min_value=0, max_value=30, value=3)
        with col3:
            species = st.selectbox("Species", ["dog", "cat", "other"])
        if st.form_submit_button("Add pet"):
            pet = Pet(name=pet_name, age=int(pet_age), species=species)
            # Owner.add_pet() appends the pet AND wires pet.owner back-reference
            st.session_state.owner.add_pet(pet)
            st.rerun()   # re-run the script so get_pets() renders the new pet immediately

    # Owner.get_pets() returns the live list stored in session state
    pets = st.session_state.owner.get_pets()
    if pets:
        for p in pets:
            st.caption(p.get_info())   # uses Pet.get_info() for the richer one-line summary

st.divider()

# ── 3. Add a task ─────────────────────────────────────────────────────────────
st.subheader("Add a Task")

if not st.session_state.owner or not st.session_state.owner.get_pets():
    st.info("Add at least one pet first.")
else:
    pets = st.session_state.owner.get_pets()
    with st.form("task_form"):
        pet_choice = st.selectbox("Pet", options=pets, format_func=str)
        col1, col2 = st.columns(2)
        with col1:
            task_type   = st.selectbox("Type", ["walk", "feeding", "medicine", "grooming"])
            task_date   = st.date_input("Date")
            task_time   = st.time_input("Time")
        with col2:
            description = st.text_input("Description (optional)")
            frequency   = st.selectbox("Frequency", ["once", "daily", "weekly", "monthly"])
            duration    = st.number_input("Duration (min)", min_value=1, max_value=240, value=30)
            priority    = st.selectbox("Priority", ["high", "medium", "low"], index=1)
        if st.form_submit_button("Add task"):
            task = Task(
                task_type   = task_type,
                pet         = pet_choice,
                date        = task_date.isoformat(),
                time        = task_time.strftime("%H:%M"),
                description = description,
                frequency   = frequency,
                duration    = int(duration),
                priority    = priority,
            )
            # Schedule.add_task() appends to the schedule AND registers the task on pet.tasks
            st.session_state.schedule.add_task(task)
            st.rerun()   # re-run so the schedule section below reflects the new task immediately

st.divider()

# ── 4. Smart Daily Plan ───────────────────────────────────────────────────────
st.subheader("Smart Daily Plan")

if not st.session_state.schedule:
    st.info("No schedule yet — save an owner to begin.")
else:
    schedule = st.session_state.schedule

    # Optional time budget — 0 means "plan the whole day" (no limit).
    budget = st.number_input(
        "Time available today (min, 0 = no limit)",
        min_value=0, max_value=1440, value=0, step=15,
    )
    available = int(budget) if budget > 0 else None

    # plan_day() gathers today's (recurring-aware) tasks, sorts them by priority
    # then time, and greedily fits them into the optional time budget.
    plan = schedule.plan_day(available_minutes=available)

    if plan.included:
        st.caption("Planned — highest priority first, then earliest time:")
        for t in plan.included:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"- {t}")
            with col2:
                # task.complete() flips status to 'done'; rerun re-renders the plan
                if t.status == "pending" and st.button("Done", key=f"done_{id(t)}"):
                    t.complete()
                    st.rerun()
    else:
        st.info("No pending tasks scheduled for today.")

    # Tasks that didn't fit the time budget, with the reason why.
    if plan.skipped:
        st.warning(f"{len(plan.skipped)} task(s) skipped — not enough time:")
        for t, reason in plan.skipped:
            st.write(f"  • **{t.task_type}** for {t.pet.name}: {reason}")

    # detect_conflicts() checks overlapping time windows per pet among planned tasks
    if plan.conflicts:
        st.error(f"{len(plan.conflicts)} conflict(s) detected:")
        for a, b in plan.conflicts:
            st.write(f"  • **{a.task_type}** ({a.time}) overlaps **{b.task_type}** ({b.time}) for {a.pet.name}")

    # The scheduler explains its own reasoning (ordering, skips, conflicts).
    with st.expander("Why this plan?"):
        st.code(plan.explain(), language="text")

    # Full task list via owner.get_all_tasks() — traverses all pets, sorted
    all_tasks = st.session_state.owner.get_all_tasks()
    if all_tasks:
        with st.expander(f"All scheduled tasks ({len(all_tasks)})"):
            for t in schedule.sort_tasks(all_tasks):
                st.write(f"- {t}")
