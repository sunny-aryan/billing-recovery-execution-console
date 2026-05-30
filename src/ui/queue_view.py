import streamlit as st

from src.cases.case_service import format_amount


def render_queue_view(cases_df):
    """
    Render the billing work queue.

    Args:
        cases_df (pandas.DataFrame): Billing cases fetched from SQLite.

    Returns:
        str | None: Selected case_id, or None if no case is selected.
    """
    st.header("Billing Work Queue")

    st.caption(
        "Review billing correction cases before approval, execution, retry, and reconciliation workflows are added."
    )

    if cases_df.empty:
        st.info("No billing cases found.")
        return None

    total_cases = len(cases_df)
    high_priority_cases = len(cases_df[cases_df["priority"] == "high"])
    pending_approval_cases = len(cases_df[cases_df["status"] == "pending_approval"])

    metric_col_1, metric_col_2, metric_col_3 = st.columns(3)

    with metric_col_1:
        st.metric("Total cases", total_cases)

    with metric_col_2:
        st.metric("High priority", high_priority_cases)

    with metric_col_3:
        st.metric("Pending approval", pending_approval_cases)

    st.divider()

    display_df = cases_df.copy()

    display_df["amount"] = display_df.apply(
        lambda row: format_amount(row["amount_cents"], row["currency"]),
        axis=1,
    )

    display_df = display_df[
        [
            "case_id",
            "customer_name",
            "invoice_id",
            "issue_type",
            "amount",
            "priority",
            "status",
        ]
    ]

    display_df = display_df.rename(
        columns={
            "case_id": "Case ID",
            "customer_name": "Customer",
            "invoice_id": "Invoice",
            "issue_type": "Issue Type",
            "amount": "Amount",
            "priority": "Priority",
            "status": "Status",
        }
    )

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.subheader("Open case")

    selected_case_id = st.selectbox(
        "Select a case to review",
        options=cases_df["case_id"].tolist(),
        format_func=lambda case_id: _format_case_option(cases_df, case_id),
        index=0,
    )

    return selected_case_id


def _format_case_option(cases_df, case_id):
    """
    Format case options shown in the selectbox.
    """
    matching_rows = cases_df[cases_df["case_id"] == case_id]

    if matching_rows.empty:
        return case_id

    row = matching_rows.iloc[0]
    amount = format_amount(row["amount_cents"], row["currency"])

    return f"{row['case_id']} · {row['customer_name']} · {row['issue_type']} · {amount}"