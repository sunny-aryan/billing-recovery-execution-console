"""
Retry policy for execution requests.

The retry policy decides whether a failed execution request can be retried.
Only transient failures are retryable. Permanent failures, successful executions,
and unknown provider states should not be retried automatically.
"""

from src.execution.execution_rules import (
    FAILED_TRANSIENT,
    MAX_RETRY_ATTEMPTS,
    RETRY_BLOCKED_STATUSES,
)


def evaluate_retry_eligibility(execution_request, attempt_count):
    """
    Evaluate whether an execution request is eligible for retry.

    Args:
        execution_request (dict): Execution request record.
        attempt_count (int): Number of attempts already recorded.

    Returns:
        dict: Retry eligibility result.
    """
    status = execution_request["status"]

    if status == FAILED_TRANSIENT and attempt_count < MAX_RETRY_ATTEMPTS:
        return {
            "is_retryable": True,
            "reason": (
                "Execution failed with a transient provider error and is eligible "
                "for retry under the current retry policy."
            ),
            "attempts_remaining": MAX_RETRY_ATTEMPTS - attempt_count,
        }

    if status == FAILED_TRANSIENT and attempt_count >= MAX_RETRY_ATTEMPTS:
        return {
            "is_retryable": False,
            "reason": (
                "Maximum retry attempts have been reached. This execution should move "
                "to manual review instead of being retried again."
            ),
            "attempts_remaining": 0,
        }

    if status in RETRY_BLOCKED_STATUSES:
        return {
            "is_retryable": False,
            "reason": f"Execution is not retryable from status: {status}.",
            "attempts_remaining": 0,
        }

    return {
        "is_retryable": False,
        "reason": (
            "Execution is not currently in a retryable state. Only transient failures "
            "can be retried."
        ),
        "attempts_remaining": 0,
    }