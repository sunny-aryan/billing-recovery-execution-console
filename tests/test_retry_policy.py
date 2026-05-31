from src.execution.execution_rules import (
    FAILED_PERMANENT,
    FAILED_TRANSIENT,
    NEEDS_MANUAL_REVIEW,
    SUCCEEDED,
)
from src.execution.retry_policy import evaluate_retry_eligibility


def test_transient_failure_is_retryable_before_max_attempts():
    execution_request = {"status": FAILED_TRANSIENT}

    result = evaluate_retry_eligibility(
        execution_request=execution_request,
        attempt_count=1,
    )

    assert result["is_retryable"] is True
    assert result["attempts_remaining"] == 2


def test_transient_failure_not_retryable_after_max_attempts():
    execution_request = {"status": FAILED_TRANSIENT}

    result = evaluate_retry_eligibility(
        execution_request=execution_request,
        attempt_count=3,
    )

    assert result["is_retryable"] is False
    assert result["attempts_remaining"] == 0


def test_permanent_failure_is_not_retryable():
    execution_request = {"status": FAILED_PERMANENT}

    result = evaluate_retry_eligibility(
        execution_request=execution_request,
        attempt_count=1,
    )

    assert result["is_retryable"] is False


def test_success_is_not_retryable():
    execution_request = {"status": SUCCEEDED}

    result = evaluate_retry_eligibility(
        execution_request=execution_request,
        attempt_count=1,
    )

    assert result["is_retryable"] is False


def test_needs_manual_review_is_not_retryable():
    execution_request = {"status": NEEDS_MANUAL_REVIEW}

    result = evaluate_retry_eligibility(
        execution_request=execution_request,
        attempt_count=1,
    )

    assert result["is_retryable"] is False