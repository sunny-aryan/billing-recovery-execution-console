import streamlit as st

from src.approvals.approval_rules import APPROVED
from src.dependencies.dependency_modes import get_mode_label
from src.dependencies.dependency_state import get_stripe_mode
from src.approvals.approval_service import get_latest_approval
from src.cases.case_service import format_amount
from src.execution.execution_rules import (
    EXECUTION_PENDING,
    MOCK_PROVIDER_OUTCOMES,
)
from src.execution.execution_service import (
    create_execution_request,
    execute_with_mock_provider,
    execute_with_stripe_provider,
    get_execution_attempts,
    get_latest_execution_request,
    get_retry_eligibility,
    retry_with_mock_provider,
)


def render_execution_request_panel(case):
    """
    Render execution request creation, provider execution, retry controls, and attempt history.

    Args:
        case (dict): Billing case record.
    """
    st.subheader("Execution Request")

    st.caption(
        "An execution request turns a human-approved billing correction into a durable "
        "system command. Mock provider execution records attempts, and transient failures "
        "can now be retried under deterministic retry policy."
    )

    latest_request = get_latest_execution_request(case["case_id"])

    if latest_request is not None:
        _render_execution_request(latest_request)
        _render_provider_execution_controls(latest_request)
        _render_retry_controls(latest_request)
        _render_execution_attempts(latest_request)
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

            st.rerun()

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
            "No provider object exists yet because provider execution has not succeeded."
        )

    if "created_at" in execution_request:
        st.caption(f"Execution request created at: {execution_request['created_at']}")

    st.caption(
        "Duplicate prevention active: this approval already has a durable execution request."
    )


def _render_provider_execution_controls(execution_request):
    """
    Render first-attempt provider execution controls.

    Args:
        execution_request (dict): Execution request record.
    """
    st.subheader("Provider Execution")

    if execution_request["status"] != EXECUTION_PENDING:
        st.info(
            f"Initial provider execution is not available because the request is currently in status: {execution_request['status']}."
        )
        return

    provider_choice = st.radio(
        "Execution provider",
        options=["mock_billing_provider", "stripe_test_mode"],
        key=f"provider_choice_{execution_request['execution_request_id']}",
    )

    if provider_choice == "mock_billing_provider":
        st.caption(
            "Use the mock provider to simulate success, transient failure, permanent failure, or timeout."
        )

        simulated_outcome = st.selectbox(
            "Mock provider outcome",
            options=MOCK_PROVIDER_OUTCOMES,
            key=f"mock_outcome_{execution_request['execution_request_id']}",
        )

        if st.button(
            "Execute with mock provider",
            key=f"execute_mock_provider_{execution_request['execution_request_id']}",
        ):
            try:
                execute_with_mock_provider(
                    execution_request_id=execution_request["execution_request_id"],
                    simulated_outcome=simulated_outcome,
                )

                st.success("Mock provider execution attempt completed.")
                st.rerun()

            except ValueError as error:
                st.error(str(error))

        return

    stripe_mode = get_stripe_mode()

    st.caption(
        "Stripe execution creates a refund against the prepared Stripe test payment. "
        "In forced mock mode, the app simulates a Stripe refund without calling Stripe."
    )

    st.info(f"Current Stripe mode: {get_mode_label(stripe_mode)}")

    st.warning(
        "Provider execution is the external write boundary. Use it only after approval, "
        "test payment setup, and execution request creation."
    )

    if st.button(
        "Execute Stripe test refund",
        key=f"execute_stripe_refund_{execution_request['execution_request_id']}",
    ):
        try:
            execute_with_stripe_provider(
                execution_request_id=execution_request["execution_request_id"],
                dependency_mode=stripe_mode,
            )

            st.success("Stripe refund execution attempt completed.")
            st.rerun()

        except ValueError as error:
            st.error(str(error))


def _render_retry_controls(execution_request):
    """
    Render retry controls for transient failures.

    Args:
        execution_request (dict): Execution request record.
    """
    st.subheader("Retry Controls")

    retry_eligibility = get_retry_eligibility(
        execution_request["execution_request_id"]
    )

    if not retry_eligibility["is_retryable"]:
        st.info(retry_eligibility["reason"])
        return

    st.warning(retry_eligibility["reason"])
    st.metric("Attempts remaining", retry_eligibility["attempts_remaining"])

    simulated_retry_outcome = st.selectbox(
        "Mock retry outcome",
        options=MOCK_PROVIDER_OUTCOMES,
        key=f"mock_retry_outcome_{execution_request['execution_request_id']}",
    )

    if st.button(
        "Retry failed execution",
        key=f"retry_execution_{execution_request['execution_request_id']}",
    ):
        try:
            retry_with_mock_provider(
                execution_request_id=execution_request["execution_request_id"],
                simulated_outcome=simulated_retry_outcome,
            )

            st.success("Retry attempt completed.")
            st.rerun()

        except ValueError as error:
            st.error(str(error))


def _render_execution_attempts(execution_request):
    """
    Render execution attempt history.

    Args:
        execution_request (dict): Execution request record.
    """
    st.subheader("Execution Attempts")

    attempts = get_execution_attempts(execution_request["execution_request_id"])

    if not attempts:
        st.info("No execution attempts have been recorded yet.")
        return

    for attempt in attempts:
        with st.expander(
            f"Attempt {attempt['attempt_number']} · {attempt['provider_status']}",
            expanded=False,
        ):
            st.write("**Attempt ID**")
            st.code(attempt["attempt_id"])

            st.write("**Provider**")
            st.write(attempt["provider"])

            st.write("**Provider Status**")
            st.write(attempt["provider_status"])

            if attempt["error_type"]:
                st.write("**Error Type**")
                st.write(attempt["error_type"])

            if attempt["error_code"]:
                st.write("**Error Code**")
                st.code(attempt["error_code"])

            if attempt["error_message"]:
                st.write("**Error Message**")
                st.write(attempt["error_message"])

            st.write("**Request Payload**")
            st.json(attempt["request_payload"])

            st.write("**Response Payload**")
            st.json(attempt["response_payload"])

            st.caption(f"Started at: {attempt['started_at']}")

            if attempt["finished_at"]:
                st.caption(f"Finished at: {attempt['finished_at']}")