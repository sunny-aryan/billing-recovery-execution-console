"""
Manual recovery service.

Manual recovery is used when automation cannot safely determine or complete
the execution lifecycle. Operators can resolve, cancel, attach provider
references, or reopen cases for investigation.
"""

import uuid

from src.cases.case_service import update_case_status
from src.audit.audit_service import record_audit_event
from src.database import get_connection
from src.execution.execution_rules import (
    CASE_STATUS_CANCELLED,
    CASE_STATUS_MANUALLY_RESOLVED,
    CASE_STATUS_UNDER_REVIEW,
    CANCELLED,
    MANUAL_ACTION_ATTACH_PROVIDER_REFERENCE,
    MANUAL_ACTION_CANCEL_EXECUTION,
    MANUAL_ACTION_MARK_RESOLVED,
    MANUAL_ACTION_REOPEN_FOR_INVESTIGATION,
    MANUAL_RECOVERY_ACTIONS,
    MANUAL_RECOVERY_ELIGIBLE_STATUSES,
    MANUALLY_RESOLVED,
)
from src.execution.execution_service import (
    attach_provider_reference,
    get_execution_request_by_id,
    update_execution_request_status,
)


def can_manually_recover(execution_request):
    """
    Determine whether manual recovery is available.

    Args:
        execution_request (dict): Execution request record.

    Returns:
        tuple[bool, str]: allowed, reason
    """
    if execution_request is None:
        return False, "Create an execution request before manual recovery."

    if execution_request["status"] in MANUAL_RECOVERY_ELIGIBLE_STATUSES:
        return (
            True,
            "This execution is eligible for manual recovery because it is failed, unresolved, or needs manual review.",
        )

    return (
        False,
        f"Manual recovery is not available from status: {execution_request['status']}.",
    )


def create_manual_recovery_action(
    execution_request_id,
    action_type,
    operator_name,
    rationale,
    provider_reference_id=None,
):
    """
    Persist and apply a manual recovery action.

    Args:
        execution_request_id (str): Execution request identifier.
        action_type (str): Manual recovery action.
        operator_name (str): Operator performing recovery.
        rationale (str): Recovery rationale.
        provider_reference_id (str | None): Optional provider reference ID.

    Returns:
        dict: Created manual recovery action.

    Raises:
        ValueError: If recovery is not allowed or fields are invalid.
    """
    execution_request = get_execution_request_by_id(execution_request_id)

    allowed, reason = can_manually_recover(execution_request)

    if not allowed:
        raise ValueError(reason)

    _validate_manual_recovery_fields(
        action_type=action_type,
        operator_name=operator_name,
        rationale=rationale,
        provider_reference_id=provider_reference_id,
    )

    previous_status = execution_request["status"]
    new_status = _get_new_execution_status(action_type)
    manual_recovery_id = f"MAN-{uuid.uuid4().hex[:8].upper()}"

    if action_type == MANUAL_ACTION_ATTACH_PROVIDER_REFERENCE:
        attach_provider_reference(
            execution_request_id=execution_request_id,
            provider_object_id=provider_reference_id.strip(),
        )

    update_execution_request_status(
        execution_request_id=execution_request_id,
        status=new_status,
    )

    _update_case_status_after_manual_recovery(
        case_id=execution_request["case_id"],
        action_type=action_type,
    )

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO manual_recovery_actions (
            manual_recovery_id,
            execution_request_id,
            action_type,
            operator_name,
            rationale,
            provider_reference_id,
            previous_execution_status,
            new_execution_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            manual_recovery_id,
            execution_request_id,
            action_type,
            operator_name.strip(),
            rationale.strip(),
            provider_reference_id.strip() if provider_reference_id else None,
            previous_status,
            new_status,
        ),
    )

    conn.commit()
    conn.close()

    record_audit_event(
        case_id=execution_request["case_id"],
        entity_type="manual_recovery_action",
        entity_id=manual_recovery_id,
        event_type="manual_recovery_recorded",
        actor_type="operator",
        actor_name=operator_name.strip(),
        details={
            "execution_request_id": execution_request_id,
            "action_type": action_type,
            "provider_reference_id": provider_reference_id.strip()
            if provider_reference_id
            else None,
            "previous_execution_status": previous_status,
            "new_execution_status": new_status,
            "rationale": rationale.strip(),
        },
    )

    return {
        "manual_recovery_id": manual_recovery_id,
        "execution_request_id": execution_request_id,
        "action_type": action_type,
        "operator_name": operator_name.strip(),
        "rationale": rationale.strip(),
        "provider_reference_id": provider_reference_id.strip()
        if provider_reference_id
        else None,
        "previous_execution_status": previous_status,
        "new_execution_status": new_status,
    }


def get_manual_recovery_actions(execution_request_id):
    """
    Fetch manual recovery history for an execution request.

    Args:
        execution_request_id (str): Execution request identifier.

    Returns:
        list[dict]: Manual recovery actions.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            manual_recovery_id,
            execution_request_id,
            action_type,
            operator_name,
            rationale,
            provider_reference_id,
            previous_execution_status,
            new_execution_status,
            created_at
        FROM manual_recovery_actions
        WHERE execution_request_id = ?
        ORDER BY created_at DESC
        """,
        (execution_request_id,),
    )

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def _validate_manual_recovery_fields(
    action_type,
    operator_name,
    rationale,
    provider_reference_id,
):
    """
    Validate manual recovery fields.
    """
    if action_type not in MANUAL_RECOVERY_ACTIONS:
        raise ValueError("Unsupported manual recovery action.")

    if not operator_name or not operator_name.strip():
        raise ValueError("Operator name is required.")

    if not rationale or not rationale.strip():
        raise ValueError("Manual recovery rationale is required.")

    if (
        action_type == MANUAL_ACTION_ATTACH_PROVIDER_REFERENCE
        and (not provider_reference_id or not provider_reference_id.strip())
    ):
        raise ValueError(
            "Provider reference ID is required when attaching a provider reference."
        )


def _get_new_execution_status(action_type):
    """
    Map manual recovery action to execution request status.
    """
    if action_type in [
        MANUAL_ACTION_MARK_RESOLVED,
        MANUAL_ACTION_ATTACH_PROVIDER_REFERENCE,
    ]:
        return MANUALLY_RESOLVED

    if action_type == MANUAL_ACTION_CANCEL_EXECUTION:
        return CANCELLED

    if action_type == MANUAL_ACTION_REOPEN_FOR_INVESTIGATION:
        return MANUAL_ACTION_REOPEN_FOR_INVESTIGATION

    return MANUALLY_RESOLVED


def _update_case_status_after_manual_recovery(case_id, action_type):
    """
    Update case status after manual recovery.
    """
    if action_type in [
        MANUAL_ACTION_MARK_RESOLVED,
        MANUAL_ACTION_ATTACH_PROVIDER_REFERENCE,
    ]:
        update_case_status(case_id, CASE_STATUS_MANUALLY_RESOLVED)
        return

    if action_type == MANUAL_ACTION_CANCEL_EXECUTION:
        update_case_status(case_id, CASE_STATUS_CANCELLED)
        return

    if action_type == MANUAL_ACTION_REOPEN_FOR_INVESTIGATION:
        update_case_status(case_id, CASE_STATUS_UNDER_REVIEW)