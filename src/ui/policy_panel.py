import streamlit as st

from src.policy.policy_service import (
    evaluate_and_store_policy,
    get_latest_policy_evaluation,
)


def render_policy_panel(case):
    """
    Render deterministic policy evaluation controls and latest policy result.

    Args:
        case (dict): Billing case record.
    """
    st.subheader("Policy Evaluation")

    st.caption(
        "Policy evaluation is deterministic. It controls whether this billing "
        "correction can move toward human approval. AI summaries may assist "
        "reviewers later, but policy rules govern eligibility."
    )

    latest_evaluation = get_latest_policy_evaluation(case["case_id"])

    if latest_evaluation is None:
        st.info("No policy evaluation has been run for this case yet.")
    else:
        _render_policy_result(latest_evaluation)

    if st.button("Evaluate policy", key=f"evaluate_policy_{case['case_id']}"):
        evaluation = evaluate_and_store_policy(case)

        st.success("Policy evaluation completed and stored.")
        _render_policy_result(evaluation)

        st.caption(
            "Refresh or reopen the case to see the updated lifecycle status in the case header."
        )


def _render_policy_result(evaluation):
    """
    Render a stored or newly-created policy evaluation result.

    Args:
        evaluation (dict): Policy evaluation result.
    """
    outcome = evaluation["outcome"]
    risk_level = evaluation["risk_level"]

    status_col_1, status_col_2, status_col_3 = st.columns(3)

    with status_col_1:
        st.metric("Policy outcome", outcome)

    with status_col_2:
        st.metric("Risk level", risk_level)

    with status_col_3:
        manager_approval = (
            "Yes" if evaluation["requires_manager_approval"] else "No"
        )
        st.metric("Manager approval required", manager_approval)

    if evaluation["is_blocked"]:
        st.error(evaluation["primary_reason"])
    elif evaluation["requires_manager_approval"]:
        st.warning(evaluation["primary_reason"])
    elif outcome == "needs_more_review":
        st.warning(evaluation["primary_reason"])
    else:
        st.success(evaluation["primary_reason"])

    st.write("**Rules triggered**")

    for rule in evaluation["rules_triggered"]:
        st.code(rule)

    if "created_at" in evaluation:
        st.caption(f"Last evaluated at: {evaluation['created_at']}")