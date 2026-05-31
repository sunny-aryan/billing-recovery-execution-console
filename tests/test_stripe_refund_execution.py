from src.approvals.approval_rules import APPROVED, BILLING_OPS_AGENT, REFUND
from src.approvals.approval_service import create_approval_decision
from src.cases.case_service import get_case_by_id
from src.dependencies.dependency_modes import (
    DEPENDENCY_MODE_FORCED_MOCK,
    DEPENDENCY_MODE_LIVE,
)
from src.execution.execution_rules import (
    FAILED_TRANSIENT,
    SUCCEEDED,
)
from src.execution.execution_service import (
    create_execution_request,
    execute_with_stripe_provider,
    get_execution_attempt_count,
    get_execution_attempts,
)
from src.policy.policy_service import evaluate_and_store_policy
from src.providers.stripe_test_payment_service import create_and_store_stripe_test_payment


def _prepare_case_for_stripe_refund(case_id="CASE-1003"):
    case = get_case_by_id(case_id)

    evaluate_and_store_policy(case)

    create_approval_decision(
        case_id=case_id,
        approver_name="Test Approver",
        approver_role=BILLING_OPS_AGENT,
        decision=APPROVED,
        approved_action=REFUND,
        approved_amount_cents=case["amount_cents"],
        rationale="Approved in automated test.",
    )

    create_and_store_stripe_test_payment(
        case=case,
        dependency_mode=DEPENDENCY_MODE_FORCED_MOCK,
    )

    execution_request, _ = create_execution_request(case)

    return execution_request


def test_forced_mock_stripe_refund_succeeds(test_db):
    execution_request = _prepare_case_for_stripe_refund()

    updated_request = execute_with_stripe_provider(
        execution_request_id=execution_request["execution_request_id"],
        dependency_mode=DEPENDENCY_MODE_FORCED_MOCK,
    )

    assert updated_request["status"] == SUCCEEDED
    assert updated_request["provider_object_id"].startswith("re_mock_")
    assert get_execution_attempt_count(execution_request["execution_request_id"]) == 1


def test_stripe_refund_requires_test_payment(test_db):
    case = get_case_by_id("CASE-1003")

    evaluate_and_store_policy(case)

    create_approval_decision(
        case_id="CASE-1003",
        approver_name="Test Approver",
        approver_role=BILLING_OPS_AGENT,
        decision=APPROVED,
        approved_action=REFUND,
        approved_amount_cents=case["amount_cents"],
        rationale="Approved in automated test.",
    )

    execution_request, _ = create_execution_request(case)

    try:
        execute_with_stripe_provider(
            execution_request_id=execution_request["execution_request_id"],
            dependency_mode=DEPENDENCY_MODE_FORCED_MOCK,
        )
        assert False, "Expected ValueError"
    except ValueError as error:
        assert "Stripe test payment must be created" in str(error)


def test_live_stripe_refund_falls_back_to_transient_failure(test_db, monkeypatch):
    execution_request = _prepare_case_for_stripe_refund()

    def mock_stripe_refund_failure(execution_request, stripe_test_payment):
        raise RuntimeError("Simulated Stripe refund failure")

    monkeypatch.setattr(
        "src.execution.execution_service.execute_test_mode_refund",
        mock_stripe_refund_failure,
    )

    updated_request = execute_with_stripe_provider(
        execution_request_id=execution_request["execution_request_id"],
        dependency_mode=DEPENDENCY_MODE_LIVE,
    )

    assert updated_request["status"] in [FAILED_TRANSIENT, "needs_manual_review"]

    attempts = get_execution_attempts(execution_request["execution_request_id"])

    assert len(attempts) == 1
    assert attempts[0]["provider"] == "stripe_test_mode"
    assert attempts[0]["error_message"]


def test_live_stripe_refund_success_when_mocked(test_db, monkeypatch):
    execution_request = _prepare_case_for_stripe_refund()

    def mock_stripe_refund_success(execution_request, stripe_test_payment):
        return {
            "provider_status": "succeeded",
            "provider_object_id": "re_test_success",
            "error_type": None,
            "error_code": None,
            "error_message": None,
            "response_payload": {
                "id": "re_test_success",
                "status": "succeeded",
                "payment_intent": stripe_test_payment["payment_intent_id"],
                "amount_cents": execution_request["approved_amount_cents"],
                "currency": execution_request["currency"],
                "idempotency_key": execution_request["idempotency_key"],
            },
        }

    monkeypatch.setattr(
        "src.execution.execution_service.execute_test_mode_refund",
        mock_stripe_refund_success,
    )

    updated_request = execute_with_stripe_provider(
        execution_request_id=execution_request["execution_request_id"],
        dependency_mode=DEPENDENCY_MODE_LIVE,
    )

    assert updated_request["status"] == SUCCEEDED
    assert updated_request["provider_object_id"] == "re_test_success"