"""
Approval constants and role rules for billing correction decisions.

This file separates approval workflow configuration from approval service logic.
"""

# Approval decisions.
APPROVED = "approved"
REJECTED = "rejected"

APPROVAL_DECISIONS = [
    APPROVED,
    REJECTED,
]

# Approver roles.
BILLING_OPS_AGENT = "billing_ops_agent"
FINANCE_MANAGER = "finance_manager"

APPROVER_ROLES = [
    BILLING_OPS_AGENT,
    FINANCE_MANAGER,
]

# Approved action types.
REFUND = "refund"
CREDIT_NOTE = "credit_note"
HOLD_FOR_MANUAL_REVIEW = "hold_for_manual_review"

APPROVED_ACTIONS = [
    REFUND,
    CREDIT_NOTE,
    HOLD_FOR_MANUAL_REVIEW,
]

# Case statuses after approval decision.
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"