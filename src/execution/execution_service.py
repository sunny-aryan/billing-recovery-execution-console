"""
Execution request service.

Commit 5 creates durable execution requests after human approval, but does
not yet call an external billing provider.

This separates the human authorization step from the future provider write.
"""

import uuid

from src.approvals.approval_rules import APPROVED
from src.approvals.approval_service import get_latest_approval
from src.cases.case_service import update_case_status
from src.database import get_connection
from src.execution.execution_rules import (
    CASE_STATUS_EXECUTION_PENDING,
    EXECUTION_PENDING,
    MOCK_BILLING_PROVIDER,
)
from src.execution.idempotency import generate_idempotency_key


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
        raise ValueError("Execution request cannot be created because the latest approval decision is not approved.")

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