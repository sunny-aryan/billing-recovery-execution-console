import streamlit as st

from src.cases.case_service import format_amount
from src.dependencies.dependency_modes import (
    RUNTIME_RESULT_FALLBACK_USED,
    RUNTIME_RESULT_FORCED_MOCK_USED,
    RUNTIME_RESULT_LIVE_SUCCESS,
    get_mode_label,
)
from src.dependencies.dependency_state import get_stripe_mode
from src.providers.stripe_test_payment_service import (
    create_and_store_stripe_test_payment,
    get_latest_stripe_test_payment,
)


def render_stripe_test_payment_panel(case):
    """
    Render Stripe test payment setup panel.

    Args:
        case (dict): Billing case record.
    """
    st.subheader("Stripe Test Payment Setup")

    st.caption(
        "This prepares a refundable test payment for future Stripe refund execution. "
        "It does not issue a refund yet."
    )

    stripe_mode = get_stripe_mode()

    st.info(f"Current Stripe mode: {get_mode_label(stripe_mode)}")

    latest_payment = get_latest_stripe_test_payment(case["case_id"])

    if latest_payment is not None:
        _render_test_payment(latest_payment)
        return

    if st.button(
        "Create Stripe test payment",
        key=f"create_stripe_test_payment_{case['case_id']}",
    ):
        create_and_store_stripe_test_payment(
            case=case,
            dependency_mode=stripe_mode,
        )
        st.rerun()


def _render_test_payment(payment):
    """
    Render stored Stripe test payment metadata.
    """
    amount = format_amount(payment["amount_cents"], payment["currency"])

    col_1, col_2, col_3 = st.columns(3)

    with col_1:
        st.metric("Payment status", payment["payment_status"])

    with col_2:
        st.metric("Runtime result", payment["runtime_result"])

    with col_3:
        st.metric("Amount", amount)

    if payment["runtime_result"] == RUNTIME_RESULT_LIVE_SUCCESS:
        st.success("Stripe live test-mode payment was created.")
    elif payment["runtime_result"] == RUNTIME_RESULT_FORCED_MOCK_USED:
        st.info("Forced mock payment metadata used. No Stripe API call was made.")
    elif payment["runtime_result"] == RUNTIME_RESULT_FALLBACK_USED:
        st.warning("Fallback payment metadata used after Stripe setup failed.")

    st.write("**Stripe Test Payment ID**")
    st.code(payment["stripe_test_payment_id"])

    st.write("**PaymentIntent ID**")
    st.code(payment["payment_intent_id"])

    if payment["charge_id"]:
        st.write("**Charge ID**")
        st.code(payment["charge_id"])

    st.write("**Source**")
    st.write(payment["source"])

    if payment["error_message"]:
        with st.expander("Fallback / setup error details", expanded=False):
            st.code(payment["error_message"])

    if "created_at" in payment:
        st.caption(f"Created at: {payment['created_at']}")