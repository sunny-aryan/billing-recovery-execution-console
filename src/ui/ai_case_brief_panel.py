import streamlit as st

from src.ai.billing_summary import (
    generate_and_store_case_brief,
    get_latest_case_brief,
)
from src.dependencies.dependency_modes import (
    RUNTIME_RESULT_FALLBACK_USED,
    RUNTIME_RESULT_FORCED_MOCK_USED,
    RUNTIME_RESULT_LIVE_SUCCESS,
)
from src.dependencies.dependency_state import get_openai_mode
from src.dependencies.dependency_modes import get_mode_label


def render_ai_case_brief_panel(case):
    """
    Render AI-generated billing case brief.

    Args:
        case (dict): Billing case record.
    """
    st.subheader("AI Case Brief")

    st.caption(
        "AI prepares review context only. It does not approve, reject, execute, retry, "
        "reconcile, or override deterministic policy."
    )

    openai_mode = get_openai_mode()

    st.info(f"Current OpenAI mode: {get_mode_label(openai_mode)}")

    latest_brief = get_latest_case_brief(case["case_id"])

    if latest_brief is not None:
        _render_case_brief(latest_brief)
    else:
        st.info("No AI case brief has been generated for this case yet.")

    if st.button(
        "Generate AI case brief",
        key=f"generate_ai_case_brief_{case['case_id']}",
    ):
        generate_and_store_case_brief(
            case=case,
            dependency_mode=openai_mode,
        )
        st.rerun()


def _render_case_brief(brief):
    """
    Render stored AI case brief.
    """
    col_1, col_2, col_3 = st.columns(3)

    with col_1:
        st.metric("AI source", brief["source"])

    with col_2:
        st.metric("Dependency mode", brief["dependency_mode"])

    with col_3:
        st.metric("Runtime result", brief["runtime_result"])

    if brief["runtime_result"] == RUNTIME_RESULT_LIVE_SUCCESS:
        st.success("OpenAI live response used.")
    elif brief["runtime_result"] == RUNTIME_RESULT_FORCED_MOCK_USED:
        st.info("Forced mock AI brief used. No OpenAI call was made.")
    elif brief["runtime_result"] == RUNTIME_RESULT_FALLBACK_USED:
        st.warning("Fallback AI brief used after live OpenAI path failed or was invalid.")

    if brief["error_message"]:
        with st.expander("Fallback error details", expanded=False):
            st.code(brief["error_message"])

    st.write("**Summary**")
    st.write(brief["summary"])

    st.write("**Customer Impact**")
    st.write(brief["customer_impact"])

    st.write("**Missing Evidence**")
    for item in brief["missing_evidence"]:
        st.write(f"- {item}")

    st.write("**Risk Notes**")
    for item in brief["risk_notes"]:
        st.write(f"- {item}")

    st.write("**Suggested Reviewer Questions**")
    for item in brief["suggested_reviewer_questions"]:
        st.write(f"- {item}")

    st.write("**Customer Message Draft**")
    st.write(brief["customer_message_draft"])

    if "created_at" in brief:
        st.caption(f"Generated at: {brief['created_at']}")