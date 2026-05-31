from src.approvals.approval_rules import APPROVED, BILLING_OPS_AGENT, REFUND
from src.approvals.approval_service import create_approval_decision
from src.cases.case_service import get_case_by_id
from src.dependencies.dependency_modes import (
    DEPENDENCY_MODE_FORCED_MOCK,
    DEPENDENCY_MODE_LIVE,
)
from src.execution.execution_rules import (
    RECON_MATCHED_SUCCESS,
    RECON_UNKNOWN_PROVIDER_STATE,
    SUCCEEDED,
)
from src.execution.execution_service import (
    create_execution_request,
    execute_with_stripe_provider,
)
from src.policy.policy_service import evaluate_and_store_policy
from src.providers.stripe_test_payment_service import create_and_store_stripe_test_payment
from src.reconciliation.reconciliation_service import run_reconciliation


def _prepare_stripe_refund_execution(case_id="CASE-1003"):
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

    updated_request = execute_with_stripe_provider(
        execution_request_id=execution_request["execution_request_id"],
        dependency_mode=DEPENDENCY_MODE_FORCED_MOCK,
    )

    return updated_request


def test_forced_mock_stripe_refund_reconciles_as_matched_success(test_db):
    execution_request = _prepare_stripe_refund_execution()

    assert execution_request["status"] == SUCCEEDED
    assert execution_request["provider_object_id"].startswith("re_mock_")

    result = run_reconciliation(
        execution_request_id=execution_request["execution_request_id"],
        dependency_mode=DEPENDENCY_MODE_FORCED_MOCK,
    )

    assert result["result"] == RECON_MATCHED_SUCCESS
    assert result["action_taken"] == "mark_reconciled"


def test_live_stripe_reconciliation_success_when_lookup_is_mocked(test_db, monkeypatch):
    execution_request = _prepare_stripe_refund_execution()

    def mock_lookup_success(execution_request):
        return {
            "provider_status": "succeeded",
            "provider_object_id": execution_request["provider_object_id"],
            "lookup_payload": {
                "id": execution_request["provider_object_id"],
                "status": "succeeded",
                "source": "mocked_live_stripe_lookup",
            },
        }

    monkeypatch.setattr(
        "src.reconciliation.reconciliation_service.lookup_stripe_refund_state",
        mock_lookup_success,
    )

    result = run_reconciliation(
        execution_request_id=execution_request["execution_request_id"],
        dependency_mode=DEPENDENCY_MODE_LIVE,
    )

    assert result["result"] == RECON_MATCHED_SUCCESS
    assert result["action_taken"] == "mark_reconciled"


def test_live_stripe_reconciliation_falls_back_to_unknown_when_lookup_fails(
    test_db,
    monkeypatch,
):
    execution_request = _prepare_stripe_refund_execution()

    def mock_lookup_failure(execution_request):
        raise RuntimeError("Simulated Stripe lookup failure")

    monkeypatch.setattr(
        "src.reconciliation.reconciliation_service.lookup_stripe_refund_state",
        mock_lookup_failure,
    )

    result = run_reconciliation(
        execution_request_id=execution_request["execution_request_id"],
        dependency_mode=DEPENDENCY_MODE_LIVE,
    )

    assert result["result"] == RECON_UNKNOWN_PROVIDER_STATE
    assert result["action_taken"] == "route_manual_review"