"""
Execution constants for billing correction execution requests, attempts, retries,
reconciliation, and manual recovery.
"""

# Execution request statuses.
EXECUTION_PENDING = "execution_pending"
PROCESSING = "processing"
RETRYING = "retrying"
SUCCEEDED = "succeeded"
FAILED_TRANSIENT = "failed_transient"
FAILED_PERMANENT = "failed_permanent"
NEEDS_MANUAL_REVIEW = "needs_manual_review"
RECONCILED = "reconciled"
MANUALLY_RESOLVED = "manually_resolved"
CANCELLED = "cancelled"

EXECUTION_REQUEST_STATUSES = [
    EXECUTION_PENDING,
    PROCESSING,
    RETRYING,
    SUCCEEDED,
    FAILED_TRANSIENT,
    FAILED_PERMANENT,
    NEEDS_MANUAL_REVIEW,
    RECONCILED,
    MANUALLY_RESOLVED,
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
PROVIDER_NOT_FOUND = "not_found"
PROVIDER_UNKNOWN = "unknown"

# Error types.
ERROR_TRANSIENT = "transient"
ERROR_PERMANENT = "permanent"
ERROR_UNKNOWN = "unknown"

# Retry policy.
MAX_RETRY_ATTEMPTS = 3

RETRY_ELIGIBLE_STATUSES = [
    FAILED_TRANSIENT,
]

RETRY_BLOCKED_STATUSES = [
    SUCCEEDED,
    FAILED_PERMANENT,
    NEEDS_MANUAL_REVIEW,
    RECONCILED,
    MANUALLY_RESOLVED,
    CANCELLED,
]

# Reconciliation results.
RECON_MATCHED_SUCCESS = "matched_success"
RECON_MATCHED_FAILURE = "matched_failure"
RECON_PROVIDER_SUCCEEDED_INTERNAL_NOT_RECORDED = "provider_succeeded_internal_not_recorded"
RECON_INTERNAL_SUCCEEDED_PROVIDER_MISSING = "internal_succeeded_provider_missing"
RECON_UNKNOWN_PROVIDER_STATE = "unknown_provider_state"
RECON_NOT_READY = "not_ready_for_reconciliation"

# Reconciliation actions.
RECON_ACTION_MARK_RECONCILED = "mark_reconciled"
RECON_ACTION_ROUTE_MANUAL_REVIEW = "route_manual_review"
RECON_ACTION_NO_CHANGE = "no_change"

# Manual recovery actions.
MANUAL_ACTION_MARK_RESOLVED = "mark_manually_resolved"
MANUAL_ACTION_CANCEL_EXECUTION = "cancel_execution"
MANUAL_ACTION_ATTACH_PROVIDER_REFERENCE = "attach_provider_reference"
MANUAL_ACTION_REOPEN_FOR_INVESTIGATION = "reopen_for_investigation"

MANUAL_RECOVERY_ACTIONS = [
    MANUAL_ACTION_MARK_RESOLVED,
    MANUAL_ACTION_CANCEL_EXECUTION,
    MANUAL_ACTION_ATTACH_PROVIDER_REFERENCE,
    MANUAL_ACTION_REOPEN_FOR_INVESTIGATION,
]

MANUAL_RECOVERY_ELIGIBLE_STATUSES = [
    FAILED_TRANSIENT,
    FAILED_PERMANENT,
    NEEDS_MANUAL_REVIEW,
]

# Case statuses after execution/reconciliation/manual recovery.
CASE_STATUS_EXECUTION_PENDING = "execution_pending"
CASE_STATUS_PROCESSING = "processing"
CASE_STATUS_RETRYING = "retrying"
CASE_STATUS_SUCCEEDED = "succeeded"
CASE_STATUS_FAILED = "failed"
CASE_STATUS_NEEDS_MANUAL_REVIEW = "needs_manual_review"
CASE_STATUS_RECONCILED = "reconciled"
CASE_STATUS_MANUALLY_RESOLVED = "manually_resolved"
CASE_STATUS_CANCELLED = "cancelled"
CASE_STATUS_UNDER_REVIEW = "under_review"