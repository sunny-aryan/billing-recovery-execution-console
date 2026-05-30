"""
Approval service for human billing correction decisions.

Responsibilities:
- validate whether a case can be approved
- enforce role requirements based on deterministic policy results
- persist approval or rejection decisions
- update case lifecycle status after approval or rejection
"""

import uuid

from src.approvals.approval_rules import (
    APPROVED,
    BILLING_OPS_AGENT,
    FINANCE_MANAGER,
    REJECTED,
    STATUS_APPROVED,
    STATUS_REJECTED,
)
from src.cases.case_service import update_case_status
from src.audit.audit_service import record_audit_event
from src.database import get_connection
from src.policy.policy_service import get_latest_policy_evaluation
from src.policy.rules import (
    BLOCKED,
    ELIGIBLE_FOR_APPROVAL,
    NEEDS_MORE_REVIEW,
    REQUIRES_MANAGER_APPROVAL,
)


def can_case_be_approved(case_id, approver_role=None):
    """
    Determine whether a case can move to human approval.

    Args:
        case_id (str): Billing case identifier.
        approver_role (str | None): Optional approver role for role-specific validation.

    Returns:
        tuple[bool, str, dict | None]: allowed, reason, latest_policy_evaluation
    """
    latest_policy = get_latest_policy_evaluation(case_id)

    if latest_policy is None:
        return (
            False,
            "Policy evaluation must be completed before approval.",
            None,
        )

    outcome = latest_policy["outcome"]

    if outcome == BLOCKED:
        return (
            False,
            "Approval is blocked because deterministic policy marked this case as blocked.",
            latest_policy,
        )

    if outcome == NEEDS_MORE_REVIEW:
        return (
            False,
            "Approval is blocked until additional review is completed.",
            latest_policy,
        )

    if outcome == REQUIRES_MANAGER_APPROVAL:
        if approver_role is None:
            return (
                True,
                "This case requires finance manager approval.",
                latest_policy,
            )

        if approver_role != FINANCE_MANAGER:
            return (
                False,
                "This case requires finance manager approval because the amount exceeds the agent approval threshold.",
                latest_policy,
            )

        return (
            True,
            "Finance manager approval is allowed for this policy outcome.",
            latest_policy,
        )

    if outcome == ELIGIBLE_FOR_APPROVAL:
        if approver_role in [None, BILLING_OPS_AGENT, FINANCE_MANAGER]:
            return (
                True,
                "This case is eligible for human approval.",
                latest_policy,
            )

    return (
        False,
        "This case is not eligible for approval under the current policy outcome.",
        latest_policy,
    )


def create_approval_decision(
    case_id,
    approver_name,
    approver_role,
    decision,
    approved_action,
    approved_amount_cents,
    rationale,
):
    """
    Persist a human approval or rejection decision.

    Args:
        case_id (str): Billing case identifier.
        approver_name (str): Human approver name.
        approver_role (str): Human approver role.
        decision (str): approved or rejected.
        approved_action (str): refund, credit_note, or hold_for_manual_review.
        approved_amount_cents (int): Approved amount in minor units.
        rationale (str): Human decision rationale.

    Returns:
        dict: Created approval decision.

    Raises:
        ValueError: If approval is not allowed or required fields are invalid.
    """
    _validate_required_fields(
        approver_name=approver_name,
        approver_role=approver_role,
        decision=decision,
        approved_action=approved_action,
        approved_amount_cents=approved_amount_cents,
        rationale=rationale,
    )

    allowed, reason, latest_policy = can_case_be_approved(case_id, approver_role)

    if not allowed:
        raise ValueError(reason)

    approval_id = f"APP-{uuid.uuid4().hex[:8].upper()}"

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO approvals (
            approval_id,
            case_id,
            policy_evaluation_id,
            approver_name,
            approver_role,
            decision,
            approved_action,
            approved_amount_cents,
            rationale
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            approval_id,
            case_id,
            latest_policy["evaluation_id"],
            approver_name.strip(),
            approver_role,
            decision,
            approved_action,
            approved_amount_cents,
            rationale.strip(),
        ),
    )

    conn.commit()
    conn.close()

    if decision == APPROVED:
        update_case_status(case_id, STATUS_APPROVED)
    elif decision == REJECTED:
        update_case_status(case_id, STATUS_REJECTED)

    record_audit_event(
        case_id=case_id,
        entity_type="approval",
        entity_id=approval_id,
        event_type="approval_decision_recorded",
        actor_type="human",
        actor_name=approver_name.strip(),
        details={
            "approver_role": approver_role,
            "decision": decision,
            "approved_action": approved_action,
            "approved_amount_cents": approved_amount_cents,
            "policy_evaluation_id": latest_policy["evaluation_id"],
            "rationale": rationale.strip(),
        },
    )

    return {
        "approval_id": approval_id,
        "case_id": case_id,
        "policy_evaluation_id": latest_policy["evaluation_id"],
        "approver_name": approver_name.strip(),
        "approver_role": approver_role,
        "decision": decision,
        "approved_action": approved_action,
        "approved_amount_cents": approved_amount_cents,
        "rationale": rationale.strip(),
    }


def get_latest_approval(case_id):
    """
    Fetch the latest approval decision for a case.

    Args:
        case_id (str): Billing case identifier.

    Returns:
        dict | None: Latest approval decision, or None if no approval exists.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            approval_id,
            case_id,
            policy_evaluation_id,
            approver_name,
            approver_role,
            decision,
            approved_action,
            approved_amount_cents,
            rationale,
            created_at
        FROM approvals
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


def _validate_required_fields(
    approver_name,
    approver_role,
    decision,
    approved_action,
    approved_amount_cents,
    rationale,
):
    """
    Validate required approval fields before persisting a decision.
    """
    if not approver_name or not approver_name.strip():
        raise ValueError("Approver name is required.")

    if not approver_role:
        raise ValueError("Approver role is required.")

    if decision not in [APPROVED, REJECTED]:
        raise ValueError("Decision must be approved or rejected.")

    if not approved_action:
        raise ValueError("Approved action is required.")

    if approved_amount_cents is None or approved_amount_cents < 0:
        raise ValueError("Approved amount must be zero or greater.")

    if not rationale or not rationale.strip():
        raise ValueError("Approval rationale is required.")