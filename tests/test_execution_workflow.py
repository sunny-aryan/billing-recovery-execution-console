from src.approvals.approval_rules import APPROVED, BILLING_OPS_AGENT, CREDIT_NOTE
from src.approvals.approval_service import create_approval_decision
from src.cases.case_service import get_case_by_id
from src.execution.execution_rules import (
    FAILED_PERMANENT,
    FAILED_TRANSIENT,
    MOCK_PERMANENT_FAILURE,
    MOCK_SUCCESS,
    MOCK_TIMEOUT,
    MOCK_TRANSIENT_FAILURE,
    NEEDS_MANUAL_REVIEW,
    SUCCEEDED,
)
from src.execution.execution_service import (
    create_execution_request,
    execute_with_mock_provider,
    get_execution_attempt_count,
    get_execution_attempts,
    retry_with_mock_provider,
)
from src.policy.policy_service import evaluate_and_store_policy


def _approve_case(case_id):
    case = get_case_by_id(case_id)

    evaluate_and_store_policy(case)

    return create_approval_decision(
        case_id=case_id,
        approver_name="Test Approver",
        approver_role=BILLING_OPS_AGENT,
        decision=APPROVED,
        approved_action=CREDIT_NOTE,
        approved_amount_cents=case["amount_cents"],
        rationale="Approved in automated test.",
    )


def test_execution_request_created_after_approval(test_db):
    _approve_case("CASE-1003")
    case = get_case_by_id("CASE-1003")

    execution_request, created_new = create_execution_request(case)

    assert created_new is True
    assert execution_request["case_id"] == "CASE-1003"
    assert execution_request["status"] == "execution_pending"
    assert execution_request["idempotency_key"] is not None


def test_duplicate_execution_request_prevented_for_same_approval(test_db):
    _approve_case("CASE-1003")
    case = get_case_by_id("CASE-1003")

    first_request, first_created = create_execution_request(case)
    second_request, second_created = create_execution_request(case)

    assert first_created is True
    assert second_created is False
    assert first_request["execution_request_id"] == second_request["execution_request_id"]
    assert first_request["idempotency_key"] == second_request["idempotency_key"]


def test_mock_success_marks_execution_succeeded(test_db):
    _approve_case("CASE-1003")
    case = get_case_by_id("CASE-1003")
    execution_request, _ = create_execution_request(case)

    updated_request = execute_with_mock_provider(
        execution_request_id=execution_request["execution_request_id"],
        simulated_outcome=MOCK_SUCCESS,
    )

    assert updated_request["status"] == SUCCEEDED
    assert updated_request["provider_object_id"] is not None
    assert get_execution_attempt_count(execution_request["execution_request_id"]) == 1


def test_mock_transient_failure_marks_execution_failed_transient(test_db):
    _approve_case("CASE-1003")
    case = get_case_by_id("CASE-1003")
    execution_request, _ = create_execution_request(case)

    updated_request = execute_with_mock_provider(
        execution_request_id=execution_request["execution_request_id"],
        simulated_outcome=MOCK_TRANSIENT_FAILURE,
    )

    assert updated_request["status"] == FAILED_TRANSIENT

    attempts = get_execution_attempts(execution_request["execution_request_id"])

    assert len(attempts) == 1
    assert attempts[0]["error_type"] == "transient"


def test_mock_permanent_failure_marks_execution_failed_permanent(test_db):
    _approve_case("CASE-1003")
    case = get_case_by_id("CASE-1003")
    execution_request, _ = create_execution_request(case)

    updated_request = execute_with_mock_provider(
        execution_request_id=execution_request["execution_request_id"],
        simulated_outcome=MOCK_PERMANENT_FAILURE,
    )

    assert updated_request["status"] == FAILED_PERMANENT


def test_mock_timeout_marks_execution_needs_manual_review(test_db):
    _approve_case("CASE-1003")
    case = get_case_by_id("CASE-1003")
    execution_request, _ = create_execution_request(case)

    updated_request = execute_with_mock_provider(
        execution_request_id=execution_request["execution_request_id"],
        simulated_outcome=MOCK_TIMEOUT,
    )

    assert updated_request["status"] == NEEDS_MANUAL_REVIEW


def test_retry_success_after_transient_failure(test_db):
    _approve_case("CASE-1003")
    case = get_case_by_id("CASE-1003")
    execution_request, _ = create_execution_request(case)

    execute_with_mock_provider(
        execution_request_id=execution_request["execution_request_id"],
        simulated_outcome=MOCK_TRANSIENT_FAILURE,
    )

    updated_request = retry_with_mock_provider(
        execution_request_id=execution_request["execution_request_id"],
        simulated_outcome=MOCK_SUCCESS,
    )

    assert updated_request["status"] == SUCCEEDED
    assert get_execution_attempt_count(execution_request["execution_request_id"]) == 2