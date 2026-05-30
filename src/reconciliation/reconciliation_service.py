"""
Reconciliation service.

Reconciliation compares internal execution state with the mock provider
source of truth. It determines whether an execution is verified, mismatched,
unknown, or needs manual review.
"""

import uuid

from src.cases.case_service import update_case_status
from src.database import get_connection
from src.execution.execution_rules import (
    CASE_STATUS_NEEDS_MANUAL_REVIEW,
    FAILED_PERMANENT,
    FAILED_TRANSIENT,
    NEEDS_MANUAL_REVIEW,
    PROVIDER_NOT_FOUND,
    PROVIDER_SUCCEEDED,
    PROVIDER_UNKNOWN,
    RECON_ACTION_MARK_RECONCILED,
    RECON_ACTION_NO_CHANGE,
    RECON_ACTION_ROUTE_MANUAL_REVIEW,
    RECON_INTERNAL_SUCCEEDED_PROVIDER_MISSING,
    RECON_MATCHED_FAILURE,
    RECON_MATCHED_SUCCESS,
    RECON_NOT_READY,
    RECON_PROVIDER_SUCCEEDED_INTERNAL_NOT_RECORDED,
    RECON_UNKNOWN_PROVIDER_STATE,
    RECONCILED,
    SUCCEEDED,
)
from src.execution.execution_service import (
    get_execution_request_by_id,
    mark_execution_reconciled,
)
from src.providers.mock_billing_adapter import lookup_provider_state


def run_reconciliation(execution_request_id, simulated_provider_state=None):
    """
    Run reconciliation for an execution request.

    Args:
        execution_request_id (str): Execution request identifier.
        simulated_provider_state (str | None): Optional provider lookup override.

    Returns:
        dict: Stored reconciliation result.
    """
    execution_request = get_execution_request_by_id(execution_request_id)

    if execution_request is None:
        raise ValueError("Execution request not found.")

    provider_lookup = lookup_provider_state(
        execution_request=execution_request,
        simulated_provider_state=simulated_provider_state,
    )

    reconciliation_result = _evaluate_reconciliation(
        execution_request=execution_request,
        provider_lookup=provider_lookup,
    )

    reconciliation_id = f"REC-{uuid.uuid4().hex[:8].upper()}"

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO reconciliation_runs (
            reconciliation_id,
            execution_request_id,
            internal_status,
            provider_status,
            provider_object_id,
            result,
            mismatch_reason,
            action_taken
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            reconciliation_id,
            execution_request_id,
            execution_request["status"],
            provider_lookup["provider_status"],
            provider_lookup["provider_object_id"],
            reconciliation_result["result"],
            reconciliation_result["mismatch_reason"],
            reconciliation_result["action_taken"],
        ),
    )

    conn.commit()
    conn.close()

    _apply_reconciliation_action(
        execution_request=execution_request,
        action_taken=reconciliation_result["action_taken"],
    )

    return {
        "reconciliation_id": reconciliation_id,
        "execution_request_id": execution_request_id,
        "internal_status": execution_request["status"],
        "provider_status": provider_lookup["provider_status"],
        "provider_object_id": provider_lookup["provider_object_id"],
        "result": reconciliation_result["result"],
        "mismatch_reason": reconciliation_result["mismatch_reason"],
        "action_taken": reconciliation_result["action_taken"],
    }


def get_reconciliation_runs(execution_request_id):
    """
    Fetch reconciliation history for an execution request.

    Args:
        execution_request_id (str): Execution request identifier.

    Returns:
        list[dict]: Reconciliation runs.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            reconciliation_id,
            execution_request_id,
            internal_status,
            provider_status,
            provider_object_id,
            result,
            mismatch_reason,
            action_taken,
            created_at
        FROM reconciliation_runs
        WHERE execution_request_id = ?
        ORDER BY created_at DESC
        """,
        (execution_request_id,),
    )

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def _evaluate_reconciliation(execution_request, provider_lookup):
    """
    Compare internal execution state with provider source-of-truth state.
    """
    internal_status = execution_request["status"]
    provider_status = provider_lookup["provider_status"]

    if internal_status == RECONCILED:
        return {
            "result": RECON_MATCHED_SUCCESS,
            "mismatch_reason": "Execution request is already reconciled.",
            "action_taken": RECON_ACTION_NO_CHANGE,
        }

    if internal_status == SUCCEEDED and provider_status == PROVIDER_SUCCEEDED:
        return {
            "result": RECON_MATCHED_SUCCESS,
            "mismatch_reason": None,
            "action_taken": RECON_ACTION_MARK_RECONCILED,
        }

    if internal_status in [FAILED_TRANSIENT, FAILED_PERMANENT] and provider_status == PROVIDER_NOT_FOUND:
        return {
            "result": RECON_MATCHED_FAILURE,
            "mismatch_reason": None,
            "action_taken": RECON_ACTION_NO_CHANGE,
        }

    if internal_status != SUCCEEDED and provider_status == PROVIDER_SUCCEEDED:
        return {
            "result": RECON_PROVIDER_SUCCEEDED_INTERNAL_NOT_RECORDED,
            "mismatch_reason": (
                "Provider source of truth shows success, but internal execution "
                "status does not record a successful provider write."
            ),
            "action_taken": RECON_ACTION_ROUTE_MANUAL_REVIEW,
        }

    if internal_status == SUCCEEDED and provider_status == PROVIDER_NOT_FOUND:
        return {
            "result": RECON_INTERNAL_SUCCEEDED_PROVIDER_MISSING,
            "mismatch_reason": (
                "Internal state says execution succeeded, but provider source of "
                "truth does not show a matching object."
            ),
            "action_taken": RECON_ACTION_ROUTE_MANUAL_REVIEW,
        }

    if provider_status == PROVIDER_UNKNOWN or internal_status == NEEDS_MANUAL_REVIEW:
        return {
            "result": RECON_UNKNOWN_PROVIDER_STATE,
            "mismatch_reason": (
                "Provider state is unknown. This execution should remain in manual review "
                "until an operator verifies the source of truth."
            ),
            "action_taken": RECON_ACTION_ROUTE_MANUAL_REVIEW,
        }

    return {
        "result": RECON_NOT_READY,
        "mismatch_reason": (
            "Execution request is not in a terminal state suitable for reconciliation."
        ),
        "action_taken": RECON_ACTION_NO_CHANGE,
    }


def _apply_reconciliation_action(execution_request, action_taken):
    """
    Apply state changes resulting from reconciliation.
    """
    if action_taken == RECON_ACTION_MARK_RECONCILED:
        mark_execution_reconciled(execution_request["execution_request_id"])
        return

    if action_taken == RECON_ACTION_ROUTE_MANUAL_REVIEW:
        update_case_status(
            execution_request["case_id"],
            CASE_STATUS_NEEDS_MANUAL_REVIEW,
        )