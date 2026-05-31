import streamlit as st

from src.execution.execution_service import get_latest_execution_request
from src.providers.stripe_test_payment_service import get_latest_stripe_test_payment
from src.ui.status_helpers import (
    format_status_label,
    get_case_workflow_stage,
    get_execution_status_guidance,
)


def render_workflow_summary(case):
    """
    Render a compact workflow summary at the top of Case Detail.

    Args:
        case (dict): Billing case record.
    """
    latest_execution_request = get_latest_execution_request(case["case_id"])
    latest_stripe_test_payment = get_latest_stripe_test_payment(case["case_id"])

    execution_status = None

    if latest_execution_request is not None:
        execution_status = latest_execution_request["status"]

    workflow_stage = get_case_workflow_stage(
        case_status=case["status"],
        execution_status=execution_status,
    )

    st.subheader("Workflow Summary")

    col_1, col_2, col_3, col_4 = st.columns(4)

    with col_1:
        st.metric("Current stage", workflow_stage)

    with col_2:
        st.metric("Case status", format_status_label(case["status"]))

    with col_3:
        if execution_status:
            st.metric("Execution status", format_status_label(execution_status))
        else:
            st.metric("Execution status", "Not created")

    with col_4:
        if latest_stripe_test_payment:
            st.metric("Stripe test payment", format_status_label(latest_stripe_test_payment["runtime_result"]))
        else:
            st.metric("Stripe test payment", "Not prepared")

    if latest_execution_request is not None:
        st.info(get_execution_status_guidance(latest_execution_request["status"]))
    else:
        st.info(
            "Review the case, generate an AI brief if useful, evaluate policy, and capture approval before creating an execution request."
        )

    if latest_execution_request is not None:
        with st.expander("Execution identifiers", expanded=False):
            st.write("**Execution Request ID**")
            st.code(latest_execution_request["execution_request_id"])

            st.write("**Provider**")
            st.write(latest_execution_request["provider"])

            st.write("**Idempotency Key**")
            st.code(latest_execution_request["idempotency_key"])

            if latest_execution_request["provider_object_id"]:
                st.write("**Provider Object ID**")
                st.code(latest_execution_request["provider_object_id"])