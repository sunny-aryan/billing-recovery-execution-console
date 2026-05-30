import streamlit as st

from src.approvals.approval_rules import APPROVED
from src.approvals.approval_service import get_latest_approval
from src.cases.case_service import format_amount
from src.execution.execution_service import (
    create_execution_request,
    get_latest_execution_request,
)


def render_execution_request_panel(case):
    """
    Render execution request creation and current execution request state.

    Args:
        case (dict): Billing case record.
    """
    st.subheader("Execution Request")

    st.caption(
        "An execution request turns a human-approved billing correction into a durable "
        "system command. This commit creates the request and idempotency key, but does "
        "not call an external provider yet."
    )

    latest_request = get_latest_execution_request(case["case_id"])

    if latest_request is not None:
        _render_execution_request(latest_request)
        return

    latest_approval = get_latest_approval(case["case_id"])

    if latest_approval is None:
        st.info("Human approval is required before an execution request can be created.")
        return

    if latest_approval["decision"] != APPROVED:
        st.warning(
            "The latest approval decision is not approved, so no execution request can be created."
        )
        return

    st.info(
        "This case has an approved correction. You can now create a durable execution request."
    )

    if st.button(
        "Create execution request",
        key=f"create_execution_request_{case['case_id']}",
    ):
        try:
            execution_request, created_new = create_execution_request(case)

            if created_new:
                st.success("Execution request created.")
            else:
                st.info("Execution request already exists for this approval.")

            _render_execution_request(execution_request)

            st.caption(
                "Refresh or reopen the case to see the updated lifecycle status in the case header."
            )

        except ValueError as error:
            st.error(str(error))


def _render_execution_request(execution_request):
    """
    Render a stored execution request.

    Args:
        execution_request (dict): Execution request record.
    """
    amount = format_amount(
        execution_request["approved_amount_cents"],
        execution_request["currency"],
    )

    col_1, col_2, col_3 = st.columns(3)

    with col_1:
        st.metric("Execution status", execution_request["status"])

    with col_2:
        st.metric("Operation", execution_request["operation_type"])

    with col_3:
        st.metric("Amount", amount)

    st.write("**Execution Request ID**")
    st.code(execution_request["execution_request_id"])

    st.write("**Approval ID**")
    st.code(execution_request["approval_id"])

    st.write("**Provider**")
    st.write(execution_request["provider"])

    st.write("**Idempotency Key**")
    st.code(execution_request["idempotency_key"])

    if execution_request["provider_object_id"]:
        st.write("**Provider Object ID**")
        st.code(execution_request["provider_object_id"])
    else:
        st.caption(
            "No provider object exists yet because provider execution has not been added."
        )

    if "created_at" in execution_request:
        st.caption(f"Execution request created at: {execution_request['created_at']}")

    st.caption(
        "Duplicate prevention active: this approval already has a durable execution request."
    )