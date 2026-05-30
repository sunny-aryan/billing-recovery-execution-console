"""
Execution constants for billing correction execution requests.

Commit 5 introduces durable execution requests, but does not yet call
external providers. Provider execution will be added in a later commit.
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

# Case status after an execution request is created.
CASE_STATUS_EXECUTION_PENDING = "execution_pending"