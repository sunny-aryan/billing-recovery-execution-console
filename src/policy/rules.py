"""
Policy rule constants for billing correction evaluation.

This file separates policy configuration from policy evaluation logic.
Future commits can evolve these values into versioned policy configs.
"""

# Supported MVP currency.
SUPPORTED_CURRENCY = "EUR"

# Amounts are stored in minor units.
# 10000 cents = EUR 100.00
MANAGER_APPROVAL_THRESHOLD_CENTS = 10000

# Cases with these issue types should not proceed to automated approval/execution.
BLOCKED_ISSUE_TYPES = {
    "currency_mismatch",
}

# Cases with these issue types require more investigation before approval.
DUPLICATE_REVIEW_ISSUE_TYPES = {
    "possible_duplicate_correction",
}

# Issue types that are generally eligible if no blocking rules are triggered.
STANDARD_ELIGIBLE_ISSUE_TYPES = {
    "duplicate_charge",
    "wrong_plan_price",
    "discount_not_applied",
    "goodwill_credit",
}

# Policy outcomes.
ELIGIBLE_FOR_APPROVAL = "eligible_for_approval"
REQUIRES_MANAGER_APPROVAL = "requires_manager_approval"
NEEDS_MORE_REVIEW = "needs_more_review"
BLOCKED = "blocked"

# Risk levels.
LOW_RISK = "low"
MEDIUM_RISK = "medium"
HIGH_RISK = "high"

# Rule identifiers.
RULE_UNSUPPORTED_CURRENCY = "unsupported_currency"
RULE_BLOCKED_ISSUE_TYPE = "blocked_issue_type"
RULE_DUPLICATE_REVIEW_REQUIRED = "duplicate_review_required"
RULE_MANAGER_APPROVAL_REQUIRED = "manager_approval_required"
RULE_STANDARD_ELIGIBLE = "standard_eligible_issue_type"
RULE_UNKNOWN_ISSUE_TYPE = "unknown_issue_type"