import streamlit as st

from src.analytics.ops_metrics import (
    get_case_status_counts,
    get_execution_attempt_metrics,
    get_execution_status_counts,
    get_manual_recovery_metrics,
    get_needs_attention_queue,
    get_reconciliation_metrics,
    get_unreconciled_execution_queue,
)
from src.cases.case_service import format_amount


def render_ops_dashboard():
    """
    Render execution operations dashboard.

    This page gives operators a cross-case view of execution health,
    reconciliation risk, and manual recovery burden.
    """
    st.header("Execution Operations Dashboard")

    st.caption(
        "A portfolio-level view of execution health, retries, reconciliation, "
        "and manual recovery across billing correction cases."
    )

    _render_summary_metrics()

    st.divider()

    _render_status_tables()

    st.divider()

    _render_needs_attention_queue()

    st.divider()

    _render_unreconciled_queue()


def _render_summary_metrics():
    """
    Render top-level operational metrics.
    """
    attempt_metrics = get_execution_attempt_metrics()
    reconciliation_metrics = get_reconciliation_metrics()
    recovery_metrics = get_manual_recovery_metrics()

    col_1, col_2, col_3, col_4 = st.columns(4)

    with col_1:
        st.metric(
            "Execution attempts",
            attempt_metrics["total_attempts"],
        )

    with col_2:
        st.metric(
            "Attempt success rate",
            f"{attempt_metrics['attempt_success_rate']:.0%}",
        )

    with col_3:
        st.metric(
            "Reconciliation runs",
            reconciliation_metrics["total_reconciliation_runs"],
        )

    with col_4:
        st.metric(
            "Manual recovery actions",
            recovery_metrics["total_manual_recovery_actions"],
        )

    col_5, col_6, col_7, col_8 = st.columns(4)

    with col_5:
        st.metric(
            "Transient failures",
            attempt_metrics["transient_failures"],
        )

    with col_6:
        st.metric(
            "Permanent failures",
            attempt_metrics["permanent_failures"],
        )

    with col_7:
        st.metric(
            "Unknown failures",
            attempt_metrics["unknown_failures"],
        )

    with col_8:
        st.metric(
            "Mismatches / unknowns",
            reconciliation_metrics["mismatches_or_unknowns"],
        )


def _render_status_tables():
    """
    Render lifecycle and execution status summaries.
    """
    st.subheader("Status Summary")

    case_status_counts = get_case_status_counts()
    execution_status_counts = get_execution_status_counts()

    col_1, col_2 = st.columns(2)

    with col_1:
        st.write("**Case Status Counts**")

        if case_status_counts.empty:
            st.info("No case status data found.")
        else:
            st.dataframe(case_status_counts, use_container_width=True, hide_index=True)

    with col_2:
        st.write("**Execution Status Counts**")

        if execution_status_counts.empty:
            st.info("No execution requests found.")
        else:
            st.dataframe(
                execution_status_counts,
                use_container_width=True,
                hide_index=True,
            )


def _render_needs_attention_queue():
    """
    Render execution requests that require operator attention.
    """
    st.subheader("Needs Attention Queue")

    st.caption(
        "Executions in failed or manual-review states. These are candidates for retry, "
        "reconciliation, or manual recovery."
    )

    needs_attention_df = get_needs_attention_queue()

    if needs_attention_df.empty:
        st.success("No executions currently need operator attention.")
        return

    display_df = needs_attention_df.copy()

    display_df["amount"] = display_df.apply(
        lambda row: format_amount(row["approved_amount_cents"], row["currency"]),
        axis=1,
    )

    display_df = display_df[
        [
            "case_id",
            "customer_name",
            "invoice_id",
            "priority",
            "execution_status",
            "operation_type",
            "amount",
            "updated_at",
        ]
    ]

    display_df = display_df.rename(
        columns={
            "case_id": "Case ID",
            "customer_name": "Customer",
            "invoice_id": "Invoice",
            "priority": "Priority",
            "execution_status": "Execution Status",
            "operation_type": "Operation",
            "amount": "Amount",
            "updated_at": "Last Updated",
        }
    )

    st.dataframe(display_df, use_container_width=True, hide_index=True)


def _render_unreconciled_queue():
    """
    Render execution requests that should be reconciled.
    """
    st.subheader("Unreconciled Execution Queue")

    st.caption(
        "Terminal or unresolved execution states that have not yet been verified "
        "against provider source of truth."
    )

    unreconciled_df = get_unreconciled_execution_queue()

    if unreconciled_df.empty:
        st.success("No unreconciled executions found.")
        return

    display_df = unreconciled_df.rename(
        columns={
            "case_id": "Case ID",
            "customer_name": "Customer",
            "execution_request_id": "Execution Request ID",
            "execution_status": "Execution Status",
            "provider_object_id": "Provider Object ID",
            "updated_at": "Last Updated",
        }
    )

    st.dataframe(display_df, use_container_width=True, hide_index=True)