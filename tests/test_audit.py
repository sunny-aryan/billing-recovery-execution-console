from src.approvals.approval_rules import APPROVED, BILLING_OPS_AGENT, CREDIT_NOTE
from src.approvals.approval_service import create_approval_decision
from src.audit.audit_service import get_audit_events_for_case
from src.cases.case_service import get_case_by_id
from src.execution.execution_rules import MOCK_SUCCESS
from src.execution.execution_service import (
    create_execution_request,
    execute_with_mock_provider,
)
from src.policy.policy_service import evaluate_and_store_policy


def test_policy_approval_execution_and_attempt_create_audit_events(test_db):
    case_id = "CASE-1003"
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

    execute_with_mock_provider(
        execution_request_id=execution_request["execution_request_id"],
        simulated_outcome=MOCK_SUCCESS,
    )

    events = get_audit_events_for_case(case_id)
    event_types = [event["event_type"] for event in events]

    assert "policy_evaluated" in event_types
    assert "approval_decision_recorded" in event_types
    assert "execution_request_created" in event_types
    assert "provider_execution_attempt_recorded" in event_types