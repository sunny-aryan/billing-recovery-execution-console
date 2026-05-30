import streamlit as st

from src.audit.audit_service import get_audit_events_for_case


def render_audit_panel(case):
    """
    Render chronological audit trail for a billing case.

    Args:
        case (dict): Billing case record.
    """
    st.subheader("Audit Trail")

    st.caption(
        "The audit trail records important workflow events across policy, approval, "
        "execution, retry, reconciliation, and manual recovery."
    )

    events = get_audit_events_for_case(case["case_id"])

    if not events:
        st.info("No audit events have been recorded for this case yet.")
        return

    for event in events:
        title = (
            f"{event['created_at']} · {event['event_type']} · "
            f"{event['actor_type']}:{event['actor_name']}"
        )

        with st.expander(title, expanded=False):
            col_1, col_2 = st.columns(2)

            with col_1:
                st.write("**Event ID**")
                st.code(event["event_id"])

                st.write("**Entity Type**")
                st.write(event["entity_type"])

                st.write("**Entity ID**")
                st.code(event["entity_id"])

            with col_2:
                st.write("**Actor Type**")
                st.write(event["actor_type"])

                st.write("**Actor Name**")
                st.write(event["actor_name"])

                st.write("**Event Type**")
                st.write(event["event_type"])

            st.write("**Details**")
            st.json(event["details"])