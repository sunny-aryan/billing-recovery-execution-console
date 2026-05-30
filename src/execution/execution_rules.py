"""
Execution constants for billing correction execution requests and attempts.
"""

# Execution request statuses.
EXECUTION_PENDING = "execution_pending"
PROCESSING = "processing"
SUCCEEDED = "succeeded"
FAILED_TRANSIENT = "failed_transient"
FAILED_PERMANENT = "failed_permanent"
NEEDS_MANUAL_REVIEW = "needs_manual_review"
RECONCILED = "reconciled"
CANCELLED = "cancelled"

EXECUTION_REQUEST_STATUSES = [
    EXECUTION_PENDING,
    PROCESSING,
    SUCCEEDED,
    FAILED_TRANSIENT,
    FAILED_PERMANENT,
    NEEDS_MANUAL_REVIEW,
    RECONCILED,
    CANCELLED,
]

# Providers.
MOCK_BILLING_PROVIDER = "mock_billing_provider"
STRIPE_TEST_MODE = "stripe_test_mode"

SUPPORTED_PROVIDERS = [
    MOCK_BILLING_PROVIDER,
    STRIPE_TEST_MODE,
]

# Operation types.
REFUND = "refund"
CREDIT_NOTE = "credit_note"
HOLD_FOR_MANUAL_REVIEW = "hold_for_manual_review"

SUPPORTED_OPERATION_TYPES = [
    REFUND,
    CREDIT_NOTE,
    HOLD_FOR_MANUAL_REVIEW,
]

# Mock provider outcomes.
MOCK_SUCCESS = "success"
MOCK_TRANSIENT_FAILURE = "transient_failure"
MOCK_PERMANENT_FAILURE = "permanent_failure"
MOCK_TIMEOUT = "timeout"

MOCK_PROVIDER_OUTCOMES = [
    MOCK_SUCCESS,
    MOCK_TRANSIENT_FAILURE,
    MOCK_PERMANENT_FAILURE,
    MOCK_TIMEOUT,
]

# Provider statuses.
PROVIDER_SUCCEEDED = "succeeded"
PROVIDER_FAILED = "failed"
PROVIDER_TIMEOUT = "timeout"

# Error types.
ERROR_TRANSIENT = "transient"
ERROR_PERMANENT = "permanent"
ERROR_UNKNOWN = "unknown"

# Case statuses after execution.
CASE_STATUS_EXECUTION_PENDING = "execution_pending"
CASE_STATUS_PROCESSING = "processing"
CASE_STATUS_SUCCEEDED = "succeeded"
CASE_STATUS_FAILED = "failed"
CASE_STATUS_NEEDS_MANUAL_REVIEW = "needs_manual_review"