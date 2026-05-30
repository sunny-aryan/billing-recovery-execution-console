"""
Execution service.

Commit 5 created durable execution requests after human approval.
Commit 6 adds mock provider execution attempts and attempt tracking.

This separates:
- approval
- execution request creation
- provider execution attempt
- provider response handling
"""

import json
import uuid

from src.approvals.approval_rules import APPROVED
from src.approvals.approval_service import get_latest_approval
from src.cases.case_service import update_case_status
from src.database import get_connection
from src.execution.execution_rules import (
    CASE_STATUS_EXECUTION_PENDING,
    CASE_STATUS_FAILED,
    CASE_STATUS_NEEDS_MANUAL_REVIEW,
    CASE_STATUS_PROCESSING,
    CASE_STATUS_SUCCEEDED,
    ERROR_PERMANENT,
    ERROR_TRANSIENT,
    ERROR_UNKNOWN,
    EXECUTION_PENDING,
    FAILED_PERMANENT,
    FAILED_TRANSIENT,
    MOCK_BILLING_PROVIDER,
    NEEDS_MANUAL_REVIEW,
    PROCESSING,
    PROVIDER_FAILED,
    PROVIDER_SUCCEEDED,
    PROVIDER_TIMEOUT,
    SUCCEEDED,
)
from src.execution.idempotency import generate_idempotency_key
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

    created_request = get_execution_request_by_id(execution_request_id)

    return created_request, True


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

    _update_execution_request_status(
        execution_request_id=execution_request_id,
        status=PROCESSING,
    )
    update_case_status(execution_request["case_id"], CASE_STATUS_PROCESSING)

    execution_request = get_execution_request_by_id(execution_request_id)
    attempt_number = _get_next_attempt_number(execution_request_id)
    attempt_id = f"ATT-{uuid.uuid4().hex[:8].upper()}"

    request_payload = {
        "execution_request_id": execution_request["execution_request_id"],
        "operation_type": execution_request["operation_type"],
        "amount_cents": execution_request["approved_amount_cents"],
        "currency": execution_request["currency"],
        "idempotency_key": execution_request["idempotency_key"],
        "provider": execution_request["provider"],
        "simulated_outcome": simulated_outcome,
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

    _update_execution_request_status(
        execution_request_id=execution_request_id,
        status=final_status,
        provider_object_id=provider_response["provider_object_id"],
    )

    update_case_status(execution_request["case_id"], final_case_status)

    return get_execution_request_by_id(execution_request_id)


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


def _get_next_attempt_number(execution_request_id):
    """
    Calculate the next attempt number for an execution request.
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

    return int(attempt_count) + 1


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

    return CASE_STATUS_FAILED