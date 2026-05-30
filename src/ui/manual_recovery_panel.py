import streamlit as st

from src.execution.execution_rules import (
    MANUAL_ACTION_ATTACH_PROVIDER_REFERENCE,
    MANUAL_RECOVERY_ACTIONS,
)
from src.recovery.manual_recovery_service import (
    can_manually_recover,
    create_manual_recovery_action,
    get_manual_recovery_actions,
)


def render_manual_recovery_panel(execution_request):
    """
    Render manual recovery controls and history.

    Args:
        execution_request (dict | None): Latest execution request.
    """
    st.subheader("Manual Recovery")

    st.caption(
        "Manual recovery is used when automation cannot safely complete the execution lifecycle. "
        "Operators must record the recovery action and rationale."
    )

    if execution_request is None:
        st.info("Create an execution request before manual recovery is available.")
        return

    allowed, reason = can_manually_recover(execution_request)

    if not allowed:
        st.info(reason)
        _render_manual_recovery_history(execution_request)
        return

    st.warning(reason)

    
    action_type = st.selectbox(
        "Manual recovery action",
        options=MANUAL_RECOVERY_ACTIONS,
        key=f"manual_recovery_action_{execution_request['execution_request_id']}",
    )

    with st.form(key=f"manual_recovery_form_{execution_request['execution_request_id']}"):
        operator_name = st.text_input("Operator name")

        provider_reference_id = None

        if action_type == MANUAL_ACTION_ATTACH_PROVIDER_REFERENCE:
            provider_reference_id = st.text_input(
                "Provider reference ID",
                help="Use this when an operator has manually verified the provider object.",
            )

        rationale = st.text_area(
            "Recovery rationale",
            help="Explain what was verified and why this recovery action is safe.",
        )

        submitted = st.form_submit_button("Submit manual recovery action")

    if submitted:
        try:
            create_manual_recovery_action(
                execution_request_id=execution_request["execution_request_id"],
                action_type=action_type,
                operator_name=operator_name,
                rationale=rationale,
                provider_reference_id=provider_reference_id,
            )

            st.success("Manual recovery action recorded.")
            st.rerun()

        except ValueError as error:
            st.error(str(error))

    _render_manual_recovery_history(execution_request)


def _render_manual_recovery_history(execution_request):
    """
    Render manual recovery history.
    """
    actions = get_manual_recovery_actions(execution_request["execution_request_id"])

    if not actions:
        st.info("No manual recovery actions have been recorded yet.")
        return

    st.write("**Manual Recovery History**")

    for action in actions:
        with st.expander(
            f"{action['action_type']} · {action['created_at']}",
            expanded=False,
        ):
            col_1, col_2 = st.columns(2)

            with col_1:
                st.metric("Previous status", action["previous_execution_status"])

            with col_2:
                st.metric("New status", action["new_execution_status"])

            st.write("**Manual Recovery ID**")
            st.code(action["manual_recovery_id"])

            st.write("**Operator**")
            st.write(action["operator_name"])

            st.write("**Rationale**")
            st.write(action["rationale"])

            if action["provider_reference_id"]:
                st.write("**Provider Reference ID**")
                st.code(action["provider_reference_id"])