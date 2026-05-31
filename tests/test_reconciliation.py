from src.approvals.approval_rules import APPROVED, BILLING_OPS_AGENT, CREDIT_NOTE
from src.approvals.approval_service import create_approval_decision
from src.cases.case_service import get_case_by_id
from src.execution.execution_rules import (
    MOCK_PERMANENT_FAILURE,
    MOCK_SUCCESS,
    MOCK_TIMEOUT,
    PROVIDER_NOT_FOUND,
    PROVIDER_SUCCEEDED,
    RECON_INTERNAL_SUCCEEDED_PROVIDER_MISSING,
    RECON_MATCHED_FAILURE,
    RECON_MATCHED_SUCCESS,
    RECON_PROVIDER_SUCCEEDED_INTERNAL_NOT_RECORDED,
    RECON_UNKNOWN_PROVIDER_STATE,
)
from src.execution.execution_service import (
    create_execution_request,
    execute_with_mock_provider,
)
from src.policy.policy_service import evaluate_and_store_policy
from src.reconciliation.reconciliation_service import run_reconciliation


def _create_execution_request_for_case(case_id="CASE-1003"):
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

    return execution_request


def test_successful_execution_reconciles_as_matched_success(test_db):
    execution_request = _create_execution_request_for_case()

    execute_with_mock_provider(
        execution_request_id=execution_request["execution_request_id"],
        simulated_outcome=MOCK_SUCCESS,
    )

    result = run_reconciliation(
        execution_request_id=execution_request["execution_request_id"],
    )

    assert result["result"] == RECON_MATCHED_SUCCESS
    assert result["action_taken"] == "mark_reconciled"


def test_failed_execution_reconciles_as_matched_failure(test_db):
    execution_request = _create_execution_request_for_case()

    execute_with_mock_provider(
        execution_request_id=execution_request["execution_request_id"],
        simulated_outcome=MOCK_PERMANENT_FAILURE,
    )

    result = run_reconciliation(
        execution_request_id=execution_request["execution_request_id"],
    )

    assert result["result"] == RECON_MATCHED_FAILURE
    assert result["action_taken"] == "no_change"


def test_timeout_reconciles_as_unknown_provider_state(test_db):
    execution_request = _create_execution_request_for_case()

    execute_with_mock_provider(
        execution_request_id=execution_request["execution_request_id"],
        simulated_outcome=MOCK_TIMEOUT,
    )

    result = run_reconciliation(
        execution_request_id=execution_request["execution_request_id"],
    )

    assert result["result"] == RECON_UNKNOWN_PROVIDER_STATE
    assert result["action_taken"] == "route_manual_review"


def test_provider_success_internal_not_recorded_mismatch_detected(test_db):
    execution_request = _create_execution_request_for_case()

    execute_with_mock_provider(
        execution_request_id=execution_request["execution_request_id"],
        simulated_outcome=MOCK_PERMANENT_FAILURE,
    )

    result = run_reconciliation(
        execution_request_id=execution_request["execution_request_id"],
        simulated_provider_state=PROVIDER_SUCCEEDED,
    )

    assert result["result"] == RECON_PROVIDER_SUCCEEDED_INTERNAL_NOT_RECORDED
    assert result["action_taken"] == "route_manual_review"


def test_internal_success_provider_missing_mismatch_detected(test_db):
    execution_request = _create_execution_request_for_case()

    execute_with_mock_provider(
        execution_request_id=execution_request["execution_request_id"],
        simulated_outcome=MOCK_SUCCESS,
    )

    result = run_reconciliation(
        execution_request_id=execution_request["execution_request_id"],
        simulated_provider_state=PROVIDER_NOT_FOUND,
    )

    assert result["result"] == RECON_INTERNAL_SUCCEEDED_PROVIDER_MISSING
    assert result["action_taken"] == "route_manual_review"