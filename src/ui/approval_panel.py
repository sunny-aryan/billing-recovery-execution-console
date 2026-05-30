import streamlit as st

from src.approvals.approval_rules import (
    APPROVAL_DECISIONS,
    APPROVED_ACTIONS,
    APPROVER_ROLES,
)
from src.approvals.approval_service import (
    can_case_be_approved,
    create_approval_decision,
    get_latest_approval,
)
from src.cases.case_service import format_amount


def render_approval_panel(case):
    """
    Render human approval controls and latest approval decision.

    Args:
        case (dict): Billing case record.
    """
    st.subheader("Human Approval")

    st.caption(
        "Human approval authorizes a billing correction after deterministic policy evaluation. "
        "Approval does not execute the correction yet; execution will be handled in a future workflow."
    )

    latest_approval = get_latest_approval(case["case_id"])

    if latest_approval is not None:
        _render_latest_approval(latest_approval, case["currency"])
        return

    allowed, reason, latest_policy = can_case_be_approved(case["case_id"])

    if latest_policy is None:
        st.info(reason)
        st.caption("Run policy evaluation before capturing an approval decision.")
        return

    if not allowed:
        st.warning(reason)
        return

    st.info(reason)

    with st.form(key=f"approval_form_{case['case_id']}"):
        approver_name = st.text_input("Approver name")

        approver_role = st.selectbox(
            "Approver role",
            options=APPROVER_ROLES,
        )

        decision = st.selectbox(
            "Decision",
            options=APPROVAL_DECISIONS,
        )

        approved_action = st.selectbox(
            "Approved action",
            options=APPROVED_ACTIONS,
        )

        default_amount = case["amount_cents"] / 100

        approved_amount = st.number_input(
            "Approved amount",
            min_value=0.0,
            value=float(default_amount),
            step=1.0,
            help="Amount is stored internally in cents.",
        )

        rationale = st.text_area(
            "Approval rationale",
            help="Explain why this correction is approved or rejected.",
        )

        submitted = st.form_submit_button("Submit approval decision")

    if submitted:
        try:
            approval = create_approval_decision(
                case_id=case["case_id"],
                approver_name=approver_name,
                approver_role=approver_role,
                decision=decision,
                approved_action=approved_action,
                approved_amount_cents=int(round(approved_amount * 100)),
                rationale=rationale,
            )

            st.success("Approval decision saved.")
            _render_latest_approval(approval, case["currency"])

            st.caption(
                "Refresh or reopen the case to see the updated lifecycle status in the case header."
            )

        except ValueError as error:
            st.error(str(error))


def _render_latest_approval(approval, currency):
    """
    Render the latest stored approval decision.

    Args:
        approval (dict): Approval decision.
        currency (str): Billing case currency.
    """
    amount = format_amount(approval["approved_amount_cents"], currency)

    col_1, col_2, col_3 = st.columns(3)

    with col_1:
        st.metric("Decision", approval["decision"])

    with col_2:
        st.metric("Approved action", approval["approved_action"])

    with col_3:
        st.metric("Approved amount", amount)

    st.write("**Approver**")
    st.write(f"{approval['approver_name']} ({approval['approver_role']})")

    st.write("**Rationale**")
    st.write(approval["rationale"])

    if "created_at" in approval:
        st.caption(f"Decision captured at: {approval['created_at']}")