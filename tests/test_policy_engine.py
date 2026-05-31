from src.cases.case_service import get_case_by_id
from src.policy.policy_engine import evaluate_policy
from src.policy.rules import (
    BLOCKED,
    ELIGIBLE_FOR_APPROVAL,
    NEEDS_MORE_REVIEW,
    REQUIRES_MANAGER_APPROVAL,
)


def test_duplicate_charge_above_threshold_requires_manager_approval(test_db):
    case = get_case_by_id("CASE-1001")

    result = evaluate_policy(case)

    assert result["outcome"] == REQUIRES_MANAGER_APPROVAL
    assert result["requires_manager_approval"] is True
    assert result["is_blocked"] is False


def test_discount_not_applied_below_threshold_is_eligible(test_db):
    case = get_case_by_id("CASE-1003")

    result = evaluate_policy(case)

    assert result["outcome"] == ELIGIBLE_FOR_APPROVAL
    assert result["requires_manager_approval"] is False
    assert result["is_blocked"] is False


def test_possible_duplicate_correction_needs_more_review(test_db):
    case = get_case_by_id("CASE-1005")

    result = evaluate_policy(case)

    assert result["outcome"] == NEEDS_MORE_REVIEW
    assert result["is_blocked"] is False


def test_currency_mismatch_is_blocked(test_db):
    case = get_case_by_id("CASE-1006")

    result = evaluate_policy(case)

    assert result["outcome"] == BLOCKED
    assert result["is_blocked"] is True