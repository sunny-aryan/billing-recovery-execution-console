"""
Execution service.

Commit 5 created durable execution requests after human approval.
Commit 6 added mock provider execution attempts and attempt tracking.
Commit 7 adds retry handling for transient failures.

This separates:
- approval
- execution request creation
- provider execution attempt
- retry eligibility
- provider response handling
"""

import json
import uuid

from src.approvals.approval_rules import APPROVED
from src.audit.audit_service import record_audit_event
from src.approvals.approval_service import get_latest_approval
from src.cases.case_service import update_case_status
from src.database import get_connection
from src.dependencies.dependency_modes import (
    DEPENDENCY_MODE_FORCED_MOCK,
    DEPENDENCY_MODE_LIVE,
)
from src.providers.stripe_adapter import (
    build_mock_refund_response,
    build_stripe_refund_fallback_response,
    execute_test_mode_refund,
)
from src.providers.stripe_test_payment_service import get_latest_stripe_test_payment
from src.execution.execution_rules import (
    CASE_STATUS_EXECUTION_PENDING,
    CASE_STATUS_FAILED,
    CASE_STATUS_NEEDS_MANUAL_REVIEW,
    CASE_STATUS_PROCESSING,
    CASE_STATUS_RETRYING,
    CASE_STATUS_SUCCEEDED,
    ERROR_PERMANENT,
    ERROR_TRANSIENT,
    ERROR_UNKNOWN,
    EXECUTION_PENDING,
    FAILED_PERMANENT,
    FAILED_TRANSIENT,
    MAX_RETRY_ATTEMPTS,
    MOCK_BILLING_PROVIDER,
    NEEDS_MANUAL_REVIEW,
    PROCESSING,
    PROVIDER_FAILED,
    PROVIDER_SUCCEEDED,
    PROVIDER_TIMEOUT,
    RETRYING,
    SUCCEEDED,
    CASE_STATUS_RECONCILED,
    RECONCILED,
    STRIPE_TEST_MODE,
)
from src.execution.idempotency import generate_idempotency_key
from src.execution.retry_policy import evaluate_retry_eligibility
from src.providers.mock_billing_adapter import execute_billing_operation


def create_execution_request(case):
    """
    Create a durable execution request from the latest approved decision.

    Args:
        case (dict): Billing case record.

    Returns:
        tuple[dict, bool]: execution_request, created_new

    Raises:
        ValueError: If no valid approval exists or approval is not approved.
    """
    latest_approval = get_latest_approval(case["case_id"])

    if latest_approval is None:
        raise ValueError("Execution request cannot be created before human approval.")

    if latest_approval["decision"] != APPROVED:
        raise ValueError(
            "Execution request cannot be created because the latest approval decision is not approved."
        )

    existing_request = get_execution_request_by_approval_id(
        latest_approval["approval_id"]
    )

    if existing_request is not None:
        return existing_request, False

    operation_type = latest_approval["approved_action"]
    approved_amount_cents = int(latest_approval["approved_amount_cents"])

    idempotency_key = generate_idempotency_key(
        case_id=case["case_id"],
        approval_id=latest_approval["approval_id"],
        operation_type=operation_type,
        approved_amount_cents=approved_amount_cents,
    )

    execution_request_id = f"EXE-{uuid.uuid4().hex[:8].upper()}"

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO execution_requests (
            execution_request_id,
            case_id,
            approval_id,
            operation_type,
            provider,
            approved_amount_cents,
            currency,
            idempotency_key,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            execution_request_id,
            case["case_id"],
            latest_approval["approval_id"],
            operation_type,
            MOCK_BILLING_PROVIDER,
            approved_amount_cents,
            case["currency"],
            idempotency_key,
            EXECUTION_PENDING,
        ),
    )

    conn.commit()
    conn.close()

    update_case_status(case["case_id"], CASE_STATUS_EXECUTION_PENDING)

    record_audit_event(
        case_id=case["case_id"],
        entity_type="execution_request",
        entity_id=execution_request_id,
        event_type="execution_request_created",
        actor_type="system",
        actor_name="execution_service",
        details={
            "approval_id": latest_approval["approval_id"],
            "operation_type": operation_type,
            "provider": MOCK_BILLING_PROVIDER,
            "approved_amount_cents": approved_amount_cents,
            "currency": case["currency"],
            "idempotency_key": idempotency_key,
            "status": EXECUTION_PENDING,
        },
    )

    created_request = get_execution_request_by_id(execution_request_id)

    return created_request, True

def execute_with_stripe_provider(execution_request_id, dependency_mode):
    """
    Execute a pending execution request through Stripe test mode or forced mock.

    Args:
        execution_request_id (str): Execution request identifier.
        dependency_mode (str): live or forced_mock.

    Returns:
        dict: Updated execution request.

    Raises:
        ValueError: If execution request is missing, not executable, or missing test payment.
    """
    execution_request = get_execution_request_by_id(execution_request_id)

    if execution_request is None:
        raise ValueError("Execution request not found.")

    if execution_request["status"] != EXECUTION_PENDING:
        raise ValueError(
            f"Execution request is not executable from status {execution_request['status']}."
        )

    stripe_test_payment = get_latest_stripe_test_payment(execution_request["case_id"])

    if stripe_test_payment is None:
        raise ValueError(
            "Stripe test payment must be created before Stripe refund execution."
        )

    return _run_stripe_refund_attempt(
        execution_request=execution_request,
        stripe_test_payment=stripe_test_payment,
        dependency_mode=dependency_mode,
    )

def execute_with_mock_provider(execution_request_id, simulated_outcome):
    """
    Execute a pending execution request with the mock billing provider.

    Args:
        execution_request_id (str): Execution request identifier.
        simulated_outcome (str): Controlled mock provider outcome.

    Returns:
        dict: Updated execution request.

    Raises:
        ValueError: If the execution request is missing or not executable.
    """
    execution_request = get_execution_request_by_id(execution_request_id)

    if execution_request is None:
        raise ValueError("Execution request not found.")

    if execution_request["status"] != EXECUTION_PENDING:
        raise ValueError(
            f"Execution request is not executable from status {execution_request['status']}."
        )

    return _run_provider_attempt(
        execution_request=execution_request,
        simulated_outcome=simulated_outcome,
        in_progress_status=PROCESSING,
        in_progress_case_status=CASE_STATUS_PROCESSING,
    )


def retry_with_mock_provider(execution_request_id, simulated_outcome):
    """
    Retry a transiently failed execution request with the mock billing provider.

    Args:
        execution_request_id (str): Execution request identifier.
        simulated_outcome (str): Controlled mock provider outcome.

    Returns:
        dict: Updated execution request.

    Raises:
        ValueError: If the execution request is missing or not retryable.
    """
    execution_request = get_execution_request_by_id(execution_request_id)

    if execution_request is None:
        raise ValueError("Execution request not found.")

    attempt_count = get_execution_attempt_count(execution_request_id)
    retry_eligibility = evaluate_retry_eligibility(execution_request, attempt_count)

    if not retry_eligibility["is_retryable"]:
        raise ValueError(retry_eligibility["reason"])

    updated_request = _run_provider_attempt(
        execution_request=execution_request,
        simulated_outcome=simulated_outcome,
        in_progress_status=RETRYING,
        in_progress_case_status=CASE_STATUS_RETRYING,
    )

    refreshed_request = get_execution_request_by_id(execution_request_id)
    refreshed_attempt_count = get_execution_attempt_count(execution_request_id)

    if (
        refreshed_request["status"] == FAILED_TRANSIENT
        and refreshed_attempt_count >= MAX_RETRY_ATTEMPTS
    ):
        _update_execution_request_status(
            execution_request_id=execution_request_id,
            status=NEEDS_MANUAL_REVIEW,
        )
        update_case_status(
            refreshed_request["case_id"],
            CASE_STATUS_NEEDS_MANUAL_REVIEW,
        )
        return get_execution_request_by_id(execution_request_id)

    return updated_request

def mark_execution_reconciled(execution_request_id):
    """
    Mark an execution request as reconciled.

    Args:
        execution_request_id (str): Execution request identifier.
    """
    execution_request = get_execution_request_by_id(execution_request_id)

    if execution_request is None:
        raise ValueError("Execution request not found.")

    _update_execution_request_status(
        execution_request_id=execution_request_id,
        status=RECONCILED,
    )

    update_case_status(
        execution_request["case_id"],
        CASE_STATUS_RECONCILED,
    )

    record_audit_event(
        case_id=execution_request["case_id"],
        entity_type="execution_request",
        entity_id=execution_request_id,
        event_type="execution_marked_reconciled",
        actor_type="system",
        actor_name="reconciliation_service",
        details={
            "previous_status": execution_request["status"],
            "new_status": RECONCILED,
        },
    )

def update_execution_request_status(execution_request_id, status):
    """
    Public helper to update execution request status.

    Args:
        execution_request_id (str): Execution request identifier.
        status (str): New execution status.
    """
    execution_request = get_execution_request_by_id(execution_request_id)

    if execution_request is None:
        raise ValueError("Execution request not found.")

    _update_execution_request_status(
        execution_request_id=execution_request_id,
        status=status,
    )

    record_audit_event(
        case_id=execution_request["case_id"],
        entity_type="execution_request",
        entity_id=execution_request_id,
        event_type="execution_status_updated",
        actor_type="system",
        actor_name="execution_service",
        details={
            "previous_status": execution_request["status"],
            "new_status": status,
        },
    )


def attach_provider_reference(execution_request_id, provider_object_id):
    """
    Attach a provider reference ID to an execution request.

    Used when an operator manually verifies an external provider object.

    Args:
        execution_request_id (str): Execution request identifier.
        provider_object_id (str): External provider object/reference ID.
    """
    execution_request = get_execution_request_by_id(execution_request_id)

    if execution_request is None:
        raise ValueError("Execution request not found.")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE execution_requests
        SET
            provider_object_id = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE execution_request_id = ?
        """,
        (provider_object_id, execution_request_id),
    )

    conn.commit()
    conn.close()


def get_latest_execution_request(case_id):
    """
    Fetch the latest execution request for a case.

    Args:
        case_id (str): Billing case identifier.

    Returns:
        dict | None: Latest execution request, or None if not found.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            execution_request_id,
            case_id,
            approval_id,
            operation_type,
            provider,
            approved_amount_cents,
            currency,
            idempotency_key,
            status,
            provider_object_id,
            created_at,
            updated_at
        FROM execution_requests
        WHERE case_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (case_id,),
    )

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return dict(row)


def get_execution_request_by_approval_id(approval_id):
    """
    Fetch an execution request created from a specific approval.

    Args:
        approval_id (str): Human approval identifier.

    Returns:
        dict | None: Execution request, or None if not found.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            execution_request_id,
            case_id,
            approval_id,
            operation_type,
            provider,
            approved_amount_cents,
            currency,
            idempotency_key,
            status,
            provider_object_id,
            created_at,
            updated_at
        FROM execution_requests
        WHERE approval_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (approval_id,),
    )

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return dict(row)


def get_execution_request_by_id(execution_request_id):
    """
    Fetch an execution request by its ID.

    Args:
        execution_request_id (str): Execution request identifier.

    Returns:
        dict | None: Execution request, or None if not found.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            execution_request_id,
            case_id,
            approval_id,
            operation_type,
            provider,
            approved_amount_cents,
            currency,
            idempotency_key,
            status,
            provider_object_id,
            created_at,
            updated_at
        FROM execution_requests
        WHERE execution_request_id = ?
        """,
        (execution_request_id,),
    )

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return dict(row)


def get_execution_attempts(execution_request_id):
    """
    Fetch execution attempts for an execution request.

    Args:
        execution_request_id (str): Execution request identifier.

    Returns:
        list[dict]: Execution attempt records.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            attempt_id,
            execution_request_id,
            attempt_number,
            provider,
            request_payload_json,
            response_payload_json,
            provider_status,
            error_type,
            error_code,
            error_message,
            started_at,
            finished_at
        FROM execution_attempts
        WHERE execution_request_id = ?
        ORDER BY attempt_number ASC
        """,
        (execution_request_id,),
    )

    rows = cursor.fetchall()
    conn.close()

    attempts = []

    for row in rows:
        attempt = dict(row)
        attempt["request_payload"] = json.loads(attempt.pop("request_payload_json"))
        attempt["response_payload"] = json.loads(attempt.pop("response_payload_json"))
        attempts.append(attempt)

    return attempts


def get_execution_attempt_count(execution_request_id):
    """
    Count execution attempts for an execution request.

    Args:
        execution_request_id (str): Execution request identifier.

    Returns:
        int: Number of attempts recorded.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT COUNT(*) AS attempt_count
        FROM execution_attempts
        WHERE execution_request_id = ?
        """,
        (execution_request_id,),
    )

    attempt_count = cursor.fetchone()["attempt_count"]
    conn.close()

    return int(attempt_count)


def get_retry_eligibility(execution_request_id):
    """
    Get retry eligibility for an execution request.

    Args:
        execution_request_id (str): Execution request identifier.

    Returns:
        dict: Retry eligibility result.
    """
    execution_request = get_execution_request_by_id(execution_request_id)

    if execution_request is None:
        return {
            "is_retryable": False,
            "reason": "Execution request not found.",
            "attempts_remaining": 0,
        }

    attempt_count = get_execution_attempt_count(execution_request_id)

    return evaluate_retry_eligibility(execution_request, attempt_count)


def _run_stripe_refund_attempt(
    execution_request,
    stripe_test_payment,
    dependency_mode,
):
    """
    Run one Stripe refund attempt and update execution state.

    Args:
        execution_request (dict): Execution request record.
        stripe_test_payment (dict): Stored Stripe test payment metadata.
        dependency_mode (str): live or forced_mock.

    Returns:
        dict: Updated execution request.
    """
    execution_request_id = execution_request["execution_request_id"]

    _update_execution_request_provider_and_status(
        execution_request_id=execution_request_id,
        provider=STRIPE_TEST_MODE,
        status=PROCESSING,
    )
    update_case_status(execution_request["case_id"], CASE_STATUS_PROCESSING)

    execution_request = get_execution_request_by_id(execution_request_id)
    attempt_number = get_execution_attempt_count(execution_request_id) + 1
    attempt_id = f"ATT-{uuid.uuid4().hex[:8].upper()}"

    request_payload = {
        "execution_request_id": execution_request["execution_request_id"],
        "operation_type": execution_request["operation_type"],
        "amount_cents": execution_request["approved_amount_cents"],
        "currency": execution_request["currency"],
        "idempotency_key": execution_request["idempotency_key"],
        "provider": STRIPE_TEST_MODE,
        "dependency_mode": dependency_mode,
        "payment_intent_id": stripe_test_payment["payment_intent_id"],
        "charge_id": stripe_test_payment["charge_id"],
        "attempt_number": attempt_number,
    }

    if dependency_mode == DEPENDENCY_MODE_FORCED_MOCK:
        provider_response = build_mock_refund_response(execution_request)

    elif dependency_mode == DEPENDENCY_MODE_LIVE:
        try:
            provider_response = execute_test_mode_refund(
                execution_request=execution_request,
                stripe_test_payment=stripe_test_payment,
            )
        except Exception as error:
            provider_response = build_stripe_refund_fallback_response(
                execution_request=execution_request,
                error=error,
            )

    else:
        provider_response = build_stripe_refund_fallback_response(
            execution_request=execution_request,
            error=ValueError(f"Unsupported Stripe dependency mode: {dependency_mode}"),
        )

    final_status = _map_provider_response_to_execution_status(provider_response)
    final_case_status = _map_execution_status_to_case_status(final_status)

    _store_execution_attempt(
        attempt_id=attempt_id,
        execution_request_id=execution_request_id,
        attempt_number=attempt_number,
        provider=STRIPE_TEST_MODE,
        request_payload=request_payload,
        provider_response=provider_response,
    )

    record_audit_event(
        case_id=execution_request["case_id"],
        entity_type="execution_attempt",
        entity_id=attempt_id,
        event_type="stripe_refund_attempt_recorded",
        actor_type="provider",
        actor_name=STRIPE_TEST_MODE,
        details={
            "execution_request_id": execution_request_id,
            "attempt_number": attempt_number,
            "dependency_mode": dependency_mode,
            "provider_status": provider_response["provider_status"],
            "provider_object_id": provider_response["provider_object_id"],
            "error_type": provider_response["error_type"],
            "error_code": provider_response["error_code"],
            "final_execution_status": final_status,
            "idempotency_key": execution_request["idempotency_key"],
        },
    )

    _update_execution_request_status(
        execution_request_id=execution_request_id,
        status=final_status,
        provider_object_id=provider_response["provider_object_id"],
    )

    update_case_status(execution_request["case_id"], final_case_status)

    return get_execution_request_by_id(execution_request_id)

def _run_provider_attempt(
    execution_request,
    simulated_outcome,
    in_progress_status,
    in_progress_case_status,
):
    """
    Run one provider attempt and update execution state from provider response.

    Args:
        execution_request (dict): Execution request record.
        simulated_outcome (str): Controlled mock provider outcome.
        in_progress_status (str): Status while attempt is in progress.
        in_progress_case_status (str): Case status while attempt is in progress.

    Returns:
        dict: Updated execution request.
    """
    execution_request_id = execution_request["execution_request_id"]

    _update_execution_request_status(
        execution_request_id=execution_request_id,
        status=in_progress_status,
    )
    update_case_status(execution_request["case_id"], in_progress_case_status)

    execution_request = get_execution_request_by_id(execution_request_id)
    attempt_number = get_execution_attempt_count(execution_request_id) + 1
    attempt_id = f"ATT-{uuid.uuid4().hex[:8].upper()}"

    request_payload = {
        "execution_request_id": execution_request["execution_request_id"],
        "operation_type": execution_request["operation_type"],
        "amount_cents": execution_request["approved_amount_cents"],
        "currency": execution_request["currency"],
        "idempotency_key": execution_request["idempotency_key"],
        "provider": execution_request["provider"],
        "simulated_outcome": simulated_outcome,
        "attempt_number": attempt_number,
    }

    provider_response = execute_billing_operation(
        execution_request=execution_request,
        simulated_outcome=simulated_outcome,
    )

    final_status = _map_provider_response_to_execution_status(provider_response)
    final_case_status = _map_execution_status_to_case_status(final_status)

    _store_execution_attempt(
        attempt_id=attempt_id,
        execution_request_id=execution_request_id,
        attempt_number=attempt_number,
        provider=execution_request["provider"],
        request_payload=request_payload,
        provider_response=provider_response,
    )

    record_audit_event(
        case_id=execution_request["case_id"],
        entity_type="execution_attempt",
        entity_id=attempt_id,
        event_type="provider_execution_attempt_recorded",
        actor_type="provider",
        actor_name=execution_request["provider"],
        details={
            "execution_request_id": execution_request_id,
            "attempt_number": attempt_number,
            "simulated_outcome": simulated_outcome,
            "provider_status": provider_response["provider_status"],
            "error_type": provider_response["error_type"],
            "error_code": provider_response["error_code"],
            "final_execution_status": final_status,
            "idempotency_key": execution_request["idempotency_key"],
        },
    )

    _update_execution_request_status(
        execution_request_id=execution_request_id,
        status=final_status,
        provider_object_id=provider_response["provider_object_id"],
    )

    update_case_status(execution_request["case_id"], final_case_status)

    return get_execution_request_by_id(execution_request_id)


def _store_execution_attempt(
    attempt_id,
    execution_request_id,
    attempt_number,
    provider,
    request_payload,
    provider_response,
):
    """
    Persist an execution attempt and provider response.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO execution_attempts (
            attempt_id,
            execution_request_id,
            attempt_number,
            provider,
            request_payload_json,
            response_payload_json,
            provider_status,
            error_type,
            error_code,
            error_message,
            finished_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            attempt_id,
            execution_request_id,
            attempt_number,
            provider,
            json.dumps(request_payload),
            json.dumps(provider_response["response_payload"]),
            provider_response["provider_status"],
            provider_response["error_type"],
            provider_response["error_code"],
            provider_response["error_message"],
        ),
    )

    conn.commit()
    conn.close()

def _update_execution_request_provider_and_status(
    execution_request_id,
    provider,
    status,
):
    """
    Update execution request provider and status.

    This is used when the user chooses a provider execution path after the
    execution request has already been created.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE execution_requests
        SET
            provider = ?,
            status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE execution_request_id = ?
        """,
        (provider, status, execution_request_id),
    )

    conn.commit()
    conn.close()

def _update_execution_request_status(
    execution_request_id,
    status,
    provider_object_id=None,
):
    """
    Update execution request status and optional provider object ID.
    """
    conn = get_connection()
    cursor = conn.cursor()

    if provider_object_id:
        cursor.execute(
            """
            UPDATE execution_requests
            SET
                status = ?,
                provider_object_id = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE execution_request_id = ?
            """,
            (status, provider_object_id, execution_request_id),
        )
    else:
        cursor.execute(
            """
            UPDATE execution_requests
            SET
                status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE execution_request_id = ?
            """,
            (status, execution_request_id),
        )

    conn.commit()
    conn.close()


def _map_provider_response_to_execution_status(provider_response):
    """
    Map provider response to execution request status.
    """
    if provider_response["provider_status"] == PROVIDER_SUCCEEDED:
        return SUCCEEDED

    if (
        provider_response["provider_status"] == PROVIDER_FAILED
        and provider_response["error_type"] == ERROR_TRANSIENT
    ):
        return FAILED_TRANSIENT

    if (
        provider_response["provider_status"] == PROVIDER_FAILED
        and provider_response["error_type"] == ERROR_PERMANENT
    ):
        return FAILED_PERMANENT

    if (
        provider_response["provider_status"] == PROVIDER_TIMEOUT
        or provider_response["error_type"] == ERROR_UNKNOWN
    ):
        return NEEDS_MANUAL_REVIEW

    return NEEDS_MANUAL_REVIEW


def _map_execution_status_to_case_status(execution_status):
    """
    Map execution request status to case lifecycle status.
    """
    if execution_status == SUCCEEDED:
        return CASE_STATUS_SUCCEEDED

    if execution_status in [FAILED_TRANSIENT, FAILED_PERMANENT]:
        return CASE_STATUS_FAILED

    if execution_status == NEEDS_MANUAL_REVIEW:
        return CASE_STATUS_NEEDS_MANUAL_REVIEW

    if execution_status == PROCESSING:
        return CASE_STATUS_PROCESSING

    if execution_status == RETRYING:
        return CASE_STATUS_RETRYING

    return CASE_STATUS_FAILED