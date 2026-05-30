import streamlit as st

from src.database import initialize_database
from src.seed import seed_database
from src.cases.case_service import get_all_cases, get_case_by_id
from src.ui.queue_view import render_queue_view
from src.ui.case_detail import render_case_detail


st.set_page_config(
    page_title="Billing Recovery Execution Console",
    page_icon="💳",
    layout="wide",
)


def initialize_app():
    """
    Initialize local persistence and seed synthetic billing cases.

    SQLite creates billing_recovery.db automatically if it does not exist.
    Seed data is inserted only when the billing_cases table is empty.
    """
    initialize_database()
    seed_database()


def render_about_page():
    """
    Render product context for the initial app shell.
    """
    st.header("About this project")

    st.markdown(
        """
        **Billing Recovery Execution Console** is a portfolio project focused on reliable
        execution after human approval.

        The product models a realistic billing operations workflow where approved
        billing corrections eventually need to become durable execution requests,
        external provider writes, retries, reconciliation checks, and manual recovery paths.
        """
    )

    st.subheader("Product thesis")

    st.info(
        "Billing corrections are not complete when a human approves them. "
        "They are complete only when the approved action is safely executed, "
        "verified against the external billing provider, reconciled with internal state, "
        "and recoverable when execution fails."
    )

    st.subheader("Current commit scope")

    st.markdown(
        """
        This first commit establishes the product and technical foundation:

        - Streamlit app shell
        - SQLite persistence
        - seeded synthetic billing cases
        - billing work queue
        - case detail view
        - modular structure for approval, execution, retry, reconciliation, and audit workflows
        """
    )

    st.subheader("Planned workflow")

    st.code(
        """
Billing issue
→ human review
→ approval
→ execution request
→ external provider write
→ success / failure / timeout
→ retry / reconciliation
→ manual recovery if needed
→ audit trail
        """.strip()
    )

    st.subheader("AI and deterministic system boundary")

    st.markdown(
        """
        Future commits will keep a clear boundary:

        - **AI assistance:** summarize billing issue, identify missing evidence, draft customer-facing context.
        - **Deterministic systems:** approval rules, execution state transitions, idempotency, retries, reconciliation, and audit logging.
        """
    )


def main():
    initialize_app()

    st.title("Billing Recovery Execution Console")
    st.caption(
        "A billing operations system for reliable execution, retry, reconciliation, and recovery after human approval."
    )

    cases_df = get_all_cases()

    with st.sidebar:
        st.header("Navigation")

        page = st.radio(
            "Go to",
            options=["Work Queue", "Case Detail", "About"],
        )

        st.divider()

        st.subheader("Project 4 Focus")
        st.caption(
            "Cross the execution boundary: approval → execution → retry → reconciliation → recovery."
        )

    if page == "Work Queue":
        selected_case_id = render_queue_view(cases_df)

        if selected_case_id:
            st.session_state["selected_case_id"] = selected_case_id

            st.info(
                f"Selected {selected_case_id}. Open the Case Detail page from the sidebar to review it."
            )

    elif page == "Case Detail":
        selected_case_id = st.session_state.get("selected_case_id")

        if selected_case_id is None and not cases_df.empty:
            selected_case_id = cases_df.iloc[0]["case_id"]
            st.session_state["selected_case_id"] = selected_case_id

        case = get_case_by_id(selected_case_id) if selected_case_id else None
        render_case_detail(case)

    elif page == "About":
        render_about_page()


if __name__ == "__main__":
    main()