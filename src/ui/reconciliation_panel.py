import streamlit as st

from src.dependencies.dependency_modes import get_mode_label
from src.dependencies.dependency_state import get_stripe_mode
from src.execution.execution_rules import STRIPE_TEST_MODE

from src.execution.execution_rules import (
    PROVIDER_NOT_FOUND,
    PROVIDER_SUCCEEDED,
    PROVIDER_UNKNOWN,
)
from src.reconciliation.reconciliation_service import (
    get_reconciliation_runs,
    run_reconciliation,
)


def render_reconciliation_panel(execution_request):
    """
    Render reconciliation controls and history.

    Args:
        execution_request (dict | None): Latest execution request.
    """
    st.subheader("Reconciliation")

    st.caption(
        "Reconciliation compares internal execution state with provider source of truth. "
        "For Stripe executions, this means looking up the refund status by refund ID."
    )

    if execution_request is None:
        st.info("Create an execution request before running reconciliation.")
        return

    simulated_provider_state = None
    stripe_mode = get_stripe_mode()

    if execution_request["provider"] == STRIPE_TEST_MODE:
        st.info(f"Stripe reconciliation mode: {get_mode_label(stripe_mode)}")

        st.caption(
            "Live mode retrieves the Stripe refund by refund ID. Forced mock mode uses "
            "deterministic Stripe refund lookup without calling Stripe."
        )

    else:
        provider_state_options = [
            "use_default_provider_lookup",
            PROVIDER_SUCCEEDED,
            PROVIDER_NOT_FOUND,
            PROVIDER_UNKNOWN,
        ]

        selected_provider_state = st.selectbox(
            "Simulated provider source-of-truth state",
            options=provider_state_options,
            key=f"reconciliation_provider_state_{execution_request['execution_request_id']}",
            help=(
                "Use the default lookup for normal testing, or override provider state "
                "to demonstrate mismatch scenarios."
            ),
        )

        if selected_provider_state != "use_default_provider_lookup":
            simulated_provider_state = selected_provider_state

    if st.button(
        "Run reconciliation",
        key=f"run_reconciliation_{execution_request['execution_request_id']}",
    ):
        try:
            run_reconciliation(
                execution_request_id=execution_request["execution_request_id"],
                simulated_provider_state=simulated_provider_state,
                dependency_mode=stripe_mode,
            )
            st.success("Reconciliation completed.")
            st.rerun()

        except ValueError as error:
            st.error(str(error))

    _render_reconciliation_history(execution_request)


def _render_reconciliation_history(execution_request):
    """
    Render reconciliation run history.
    """
    runs = get_reconciliation_runs(execution_request["execution_request_id"])

    if not runs:
        st.info("No reconciliation runs have been recorded yet.")
        return

    st.write("**Reconciliation History**")

    for run in runs:
        with st.expander(
            f"{run['result']} · {run['created_at']}",
            expanded=False,
        ):
            col_1, col_2, col_3 = st.columns(3)

            with col_1:
                st.metric("Internal status", run["internal_status"])

            with col_2:
                st.metric("Provider status", run["provider_status"])

            with col_3:
                st.metric("Action taken", run["action_taken"])

            st.write("**Reconciliation ID**")
            st.code(run["reconciliation_id"])

            if run["provider_object_id"]:
                st.write("**Provider Object ID**")
                st.code(run["provider_object_id"])

            if run["mismatch_reason"]:
                st.warning(run["mismatch_reason"])
            else:
                st.success("No mismatch detected.")