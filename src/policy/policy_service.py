"""
Policy service for evaluating and persisting deterministic billing correction policy results.

Responsibilities:
- call the policy engine
- store policy evaluation results
- fetch the latest policy evaluation for a case
- update the billing case lifecycle status based on policy outcome
"""

import json
import uuid

from src.database import get_connection
from src.cases.case_service import update_case_status
from src.audit.audit_service import record_audit_event
from src.policy.policy_engine import evaluate_policy
from src.policy.rules import (
    BLOCKED,
    ELIGIBLE_FOR_APPROVAL,
    NEEDS_MORE_REVIEW,
    REQUIRES_MANAGER_APPROVAL,
)


def evaluate_and_store_policy(case):
    """
    Evaluate a billing case and persist the policy result.

    Args:
        case (dict): Billing case record.

    Returns:
        dict: Persisted policy evaluation result.
    """
    policy_result = evaluate_policy(case)
    evaluation_id = f"POL-{uuid.uuid4().hex[:8].upper()}"

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO policy_evaluations (
            evaluation_id,
            case_id,
            outcome,
            risk_level,
            requires_manager_approval,
            is_blocked,
            primary_reason,
            rules_triggered_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            evaluation_id,
            case["case_id"],
            policy_result["outcome"],
            policy_result["risk_level"],
            int(policy_result["requires_manager_approval"]),
            int(policy_result["is_blocked"]),
            policy_result["primary_reason"],
            json.dumps(policy_result["rules_triggered"]),
        ),
    )

    conn.commit()
    conn.close()

    next_status = _get_case_status_for_policy_outcome(policy_result["outcome"])
    update_case_status(case["case_id"], next_status)

    record_audit_event(
        case_id=case["case_id"],
        entity_type="policy_evaluation",
        entity_id=evaluation_id,
        event_type="policy_evaluated",
        actor_type="system",
        actor_name="policy_engine",
        details={
            "outcome": policy_result["outcome"],
            "risk_level": policy_result["risk_level"],
            "requires_manager_approval": policy_result["requires_manager_approval"],
            "is_blocked": policy_result["is_blocked"],
            "rules_triggered": policy_result["rules_triggered"],
            "case_status_after": next_status,
        },
    )    

    return {
        "evaluation_id": evaluation_id,
        "case_id": case["case_id"],
        **policy_result,
    }


def get_latest_policy_evaluation(case_id):
    """
    Fetch the latest policy evaluation for a billing case.

    Args:
        case_id (str): Billing case identifier.

    Returns:
        dict | None: Latest policy evaluation result, or None if no evaluation exists.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            evaluation_id,
            case_id,
            outcome,
            risk_level,
            requires_manager_approval,
            is_blocked,
            primary_reason,
            rules_triggered_json,
            created_at
        FROM policy_evaluations
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

    evaluation = dict(row)

    evaluation["requires_manager_approval"] = bool(
        evaluation["requires_manager_approval"]
    )
    evaluation["is_blocked"] = bool(evaluation["is_blocked"])
    evaluation["rules_triggered"] = json.loads(
        evaluation.pop("rules_triggered_json")
    )

    return evaluation


def _get_case_status_for_policy_outcome(outcome):
    """
    Map policy outcome to the next billing case lifecycle status.

    Args:
        outcome (str): Policy evaluation outcome.

    Returns:
        str: Case status after policy evaluation.
    """
    if outcome == ELIGIBLE_FOR_APPROVAL:
        return "pending_approval"

    if outcome == REQUIRES_MANAGER_APPROVAL:
        return "pending_approval"

    if outcome == NEEDS_MORE_REVIEW:
        return "under_review"

    if outcome == BLOCKED:
        return "blocked"

    return "under_review"