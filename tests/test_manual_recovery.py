import pytest

from src.approvals.approval_rules import APPROVED, BILLING_OPS_AGENT, CREDIT_NOTE
from src.approvals.approval_service import create_approval_decision
from src.cases.case_service import get_case_by_id
from src.execution.execution_rules import (
    MANUAL_ACTION_ATTACH_PROVIDER_REFERENCE,
    MANUAL_ACTION_CANCEL_EXECUTION,
    MANUAL_ACTION_MARK_RESOLVED,
    MANUALLY_RESOLVED,
    MOCK_TIMEOUT,
)
from src.execution.execution_service import (
    create_execution_request,
    execute_with_mock_provider,
    get_execution_request_by_id,
)
from src.policy.policy_service import evaluate_and_store_policy
from src.recovery.manual_recovery_service import (
    create_manual_recovery_action,
    get_manual_recovery_actions,
)


def _create_manual_review_execution(case_id="CASE-1003"):
    case = get_case_by_id(case_id)

    evaluate_and_store_policy(case)

    create_approval_decision(
        case_id=case_id,
        approver_name="Test Approver",
        approver_role=BILLING_OPS_AGENT,
        decision=APPROVED,
        approved_action=CREDIT_NOTE,
        approved_amount_cents=case["amount_cents"],
        rationale="Approved in automated test.",
    )

    execution_request, _ = create_execution_request(case)

    updated_request = execute_with_mock_provider(
        execution_request_id=execution_request["execution_request_id"],
        simulated_outcome=MOCK_TIMEOUT,
    )

    return updated_request


def test_manual_recovery_mark_resolved(test_db):
    execution_request = _create_manual_review_execution()

    recovery_action = create_manual_recovery_action(
        execution_request_id=execution_request["execution_request_id"],
        action_type=MANUAL_ACTION_MARK_RESOLVED,
        operator_name="Ops User",
        rationale="Verified externally and resolved manually.",
    )

    updated_request = get_execution_request_by_id(
        execution_request["execution_request_id"]
    )

    assert recovery_action["new_execution_status"] == MANUALLY_RESOLVED
    assert updated_request["status"] == MANUALLY_RESOLVED


def test_manual_recovery_attach_provider_reference(test_db):
    execution_request = _create_manual_review_execution()

    provider_reference_id = "mock_manual_ref_123"

    create_manual_recovery_action(
        execution_request_id=execution_request["execution_request_id"],
        action_type=MANUAL_ACTION_ATTACH_PROVIDER_REFERENCE,
        operator_name="Ops User",
        rationale="Found provider reference during manual lookup.",
        provider_reference_id=provider_reference_id,
    )

    updated_request = get_execution_request_by_id(
        execution_request["execution_request_id"]
    )

    assert updated_request["provider_object_id"] == provider_reference_id
    assert updated_request["status"] == MANUALLY_RESOLVED


def test_attach_provider_reference_requires_reference_id(test_db):
    execution_request = _create_manual_review_execution()

    with pytest.raises(ValueError):
        create_manual_recovery_action(
            execution_request_id=execution_request["execution_request_id"],
            action_type=MANUAL_ACTION_ATTACH_PROVIDER_REFERENCE,
            operator_name="Ops User",
            rationale="Provider reference missing.",
            provider_reference_id=None,
        )


def test_manual_recovery_requires_rationale(test_db):
    execution_request = _create_manual_review_execution()

    with pytest.raises(ValueError):
        create_manual_recovery_action(
            execution_request_id=execution_request["execution_request_id"],
            action_type=MANUAL_ACTION_CANCEL_EXECUTION,
            operator_name="Ops User",
            rationale="",
        )


def test_manual_recovery_history_is_recorded(test_db):
    execution_request = _create_manual_review_execution()

    create_manual_recovery_action(
        execution_request_id=execution_request["execution_request_id"],
        action_type=MANUAL_ACTION_MARK_RESOLVED,
        operator_name="Ops User",
        rationale="Verified externally and resolved manually.",
    )

    actions = get_manual_recovery_actions(execution_request["execution_request_id"])

    assert len(actions) == 1
    assert actions[0]["operator_name"] == "Ops User"