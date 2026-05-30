"""
Mock billing provider adapter.

This adapter simulates external provider execution outcomes without calling
a real billing API. It lets the product demonstrate success, transient failure,
permanent failure, and timeout paths deterministically.
"""

import uuid

from src.execution.execution_rules import (
    ERROR_PERMANENT,
    ERROR_TRANSIENT,
    ERROR_UNKNOWN,
    MOCK_PERMANENT_FAILURE,
    MOCK_SUCCESS,
    MOCK_TIMEOUT,
    MOCK_TRANSIENT_FAILURE,
    PROVIDER_FAILED,
    PROVIDER_SUCCEEDED,
    PROVIDER_TIMEOUT,
)


def execute_billing_operation(execution_request, simulated_outcome):
    """
    Simulate a billing provider write.

    Args:
        execution_request (dict): Durable execution request.
        simulated_outcome (str): Controlled mock provider outcome.

    Returns:
        dict: Provider-like response payload.
    """
    if simulated_outcome == MOCK_SUCCESS:
        provider_object_id = f"mock_refund_{uuid.uuid4().hex[:10]}"

        return {
            "provider_status": PROVIDER_SUCCEEDED,
            "provider_object_id": provider_object_id,
            "error_type": None,
            "error_code": None,
            "error_message": None,
            "response_payload": {
                "id": provider_object_id,
                "status": "succeeded",
                "operation_type": execution_request["operation_type"],
                "amount_cents": execution_request["approved_amount_cents"],
                "currency": execution_request["currency"],
                "idempotency_key": execution_request["idempotency_key"],
            },
        }

    if simulated_outcome == MOCK_TRANSIENT_FAILURE:
        return {
            "provider_status": PROVIDER_FAILED,
            "provider_object_id": None,
            "error_type": ERROR_TRANSIENT,
            "error_code": "provider_temporary_unavailable",
            "error_message": "Mock provider is temporarily unavailable. This failure may be retried later.",
            "response_payload": {
                "status": "failed",
                "reason": "temporary_unavailable",
                "retryable": True,
            },
        }

    if simulated_outcome == MOCK_PERMANENT_FAILURE:
        return {
            "provider_status": PROVIDER_FAILED,
            "provider_object_id": None,
            "error_type": ERROR_PERMANENT,
            "error_code": "invalid_billing_target",
            "error_message": "Mock provider rejected the request because the billing target is invalid.",
            "response_payload": {
                "status": "failed",
                "reason": "invalid_billing_target",
                "retryable": False,
            },
        }

    if simulated_outcome == MOCK_TIMEOUT:
        return {
            "provider_status": PROVIDER_TIMEOUT,
            "provider_object_id": None,
            "error_type": ERROR_UNKNOWN,
            "error_code": "provider_timeout",
            "error_message": "Mock provider timed out. The external result is unknown and requires reconciliation or manual review.",
            "response_payload": {
                "status": "unknown",
                "reason": "timeout",
                "retryable": False,
            },
        }

    return {
        "provider_status": PROVIDER_FAILED,
        "provider_object_id": None,
        "error_type": ERROR_PERMANENT,
        "error_code": "unsupported_mock_outcome",
        "error_message": f"Unsupported mock outcome: {simulated_outcome}",
        "response_payload": {
            "status": "failed",
            "reason": "unsupported_mock_outcome",
            "retryable": False,
        },
    }