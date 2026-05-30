import streamlit as st

from src.cases.case_service import format_amount
from src.ui.approval_panel import render_approval_panel
from src.ui.execution_request_panel import render_execution_request_panel
from src.ui.policy_panel import render_policy_panel


def render_case_detail(case):
    """
    Render details for a selected billing case.

    Args:
        case (dict | None): Billing case record.
    """
    st.header("Case Detail")

    if case is None:
        st.warning("No case selected or case could not be found.")
        return

    amount = format_amount(case["amount_cents"], case["currency"])

    st.subheader(case["case_id"])
    st.caption(f"{case['customer_name']} · {case['invoice_id']}")

    metric_col_1, metric_col_2, metric_col_3 = st.columns(3)

    with metric_col_1:
        st.metric("Amount", amount)

    with metric_col_2:
        st.metric("Priority", case["priority"])

    with metric_col_3:
        st.metric("Status", case["status"])

    st.divider()

    st.subheader("Case Overview")

    overview_col_1, overview_col_2 = st.columns(2)

    with overview_col_1:
        st.write("**Customer ID**")
        st.write(case["customer_id"])

        st.write("**Customer Name**")
        st.write(case["customer_name"])

        st.write("**Invoice ID**")
        st.write(case["invoice_id"])

    with overview_col_2:
        st.write("**Issue Type**")
        st.write(case["issue_type"])

        st.write("**Currency**")
        st.write(case["currency"])

        st.write("**Created At**")
        st.write(case["created_at"])

    st.divider()

    st.subheader("Billing Issue")
    st.write(case["evidence_summary"])

    st.subheader("Proposed Correction")
    st.write(case["proposed_correction"])

    st.divider()

    render_policy_panel(case)

    st.divider()

    render_approval_panel(case)

    st.divider()

    render_execution_request_panel(case)

    st.divider()

    st.subheader("Current Workflow Status")

    st.info(
        "This case now supports deterministic policy evaluation, human approval capture, "
        "durable execution request creation, mock provider execution, and execution attempt tracking. "
        "Retries, reconciliation, and manual recovery will be added in future commits."
    )

    st.subheader("Future Recovery Controls")

    future_col_1, future_col_2 = st.columns(2)

    with future_col_1:
        st.button("Retry failed execution", disabled=True)

    with future_col_2:
        st.button("Run reconciliation", disabled=True)

    st.caption(
        "Disabled controls are intentional placeholders for the upcoming retry and reconciliation lifecycle."
    )