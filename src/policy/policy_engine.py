"""
Deterministic policy engine for billing correction evaluation.

The policy engine decides whether a billing correction can move toward
human approval. It does not approve the correction and it does not execute
money-impacting actions.

AI may later help summarize context, but this engine remains deterministic.
"""

from src.policy.rules import (
    BLOCKED,
    BLOCKED_ISSUE_TYPES,
    DUPLICATE_REVIEW_ISSUE_TYPES,
    ELIGIBLE_FOR_APPROVAL,
    HIGH_RISK,
    LOW_RISK,
    MANAGER_APPROVAL_THRESHOLD_CENTS,
    MEDIUM_RISK,
    NEEDS_MORE_REVIEW,
    REQUIRES_MANAGER_APPROVAL,
    RULE_BLOCKED_ISSUE_TYPE,
    RULE_DUPLICATE_REVIEW_REQUIRED,
    RULE_MANAGER_APPROVAL_REQUIRED,
    RULE_STANDARD_ELIGIBLE,
    RULE_UNKNOWN_ISSUE_TYPE,
    RULE_UNSUPPORTED_CURRENCY,
    STANDARD_ELIGIBLE_ISSUE_TYPES,
    SUPPORTED_CURRENCY,
)


def evaluate_policy(case):
    """
    Evaluate a billing correction case against deterministic policy rules.

    Args:
        case (dict): Billing case record.

    Returns:
        dict: Structured policy evaluation result.
    """
    issue_type = case["issue_type"]
    currency = case["currency"]
    amount_cents = int(case["amount_cents"])

    rules_triggered = []

    if currency != SUPPORTED_CURRENCY:
        rules_triggered.append(RULE_UNSUPPORTED_CURRENCY)

        return _build_result(
            outcome=BLOCKED,
            risk_level=HIGH_RISK,
            requires_manager_approval=False,
            is_blocked=True,
            primary_reason=(
                f"Automated correction is blocked because the billing currency "
                f"is {currency}, while the MVP supports only {SUPPORTED_CURRENCY}."
            ),
            rules_triggered=rules_triggered,
        )

    if issue_type in BLOCKED_ISSUE_TYPES:
        rules_triggered.append(RULE_BLOCKED_ISSUE_TYPE)

        return _build_result(
            outcome=BLOCKED,
            risk_level=HIGH_RISK,
            requires_manager_approval=False,
            is_blocked=True,
            primary_reason=(
                "This issue type is blocked from automated approval because it may "
                "require billing configuration or contract review before correction."
            ),
            rules_triggered=rules_triggered,
        )

    if issue_type in DUPLICATE_REVIEW_ISSUE_TYPES:
        rules_triggered.append(RULE_DUPLICATE_REVIEW_REQUIRED)

        return _build_result(
            outcome=NEEDS_MORE_REVIEW,
            risk_level=MEDIUM_RISK,
            requires_manager_approval=False,
            is_blocked=False,
            primary_reason=(
                "This case may already have received a previous correction. "
                "More review is required before approval to avoid duplicate credit or refund execution."
            ),
            rules_triggered=rules_triggered,
        )

    if issue_type not in STANDARD_ELIGIBLE_ISSUE_TYPES:
        rules_triggered.append(RULE_UNKNOWN_ISSUE_TYPE)

        return _build_result(
            outcome=NEEDS_MORE_REVIEW,
            risk_level=MEDIUM_RISK,
            requires_manager_approval=False,
            is_blocked=False,
            primary_reason=(
                "This issue type is not recognized by the current policy rules. "
                "Manual review is required before approval."
            ),
            rules_triggered=rules_triggered,
        )

    rules_triggered.append(RULE_STANDARD_ELIGIBLE)

    if amount_cents > MANAGER_APPROVAL_THRESHOLD_CENTS:
        rules_triggered.append(RULE_MANAGER_APPROVAL_REQUIRED)

        return _build_result(
            outcome=REQUIRES_MANAGER_APPROVAL,
            risk_level=MEDIUM_RISK,
            requires_manager_approval=True,
            is_blocked=False,
            primary_reason=(
                "Correction is eligible to move forward, but the amount exceeds "
                "the agent approval threshold and requires finance manager approval."
            ),
            rules_triggered=rules_triggered,
        )

    return _build_result(
        outcome=ELIGIBLE_FOR_APPROVAL,
        risk_level=LOW_RISK,
        requires_manager_approval=False,
        is_blocked=False,
        primary_reason=(
            "Correction is eligible to move forward for human approval under the current policy rules."
        ),
        rules_triggered=rules_triggered,
    )


def _build_result(
    outcome,
    risk_level,
    requires_manager_approval,
    is_blocked,
    primary_reason,
    rules_triggered,
):
    """
    Build a consistent policy result payload.

    Args:
        outcome (str): Policy outcome.
        risk_level (str): Risk level.
        requires_manager_approval (bool): Whether manager approval is required.
        is_blocked (bool): Whether the correction is blocked.
        primary_reason (str): Human-readable explanation.
        rules_triggered (list[str]): Rule identifiers triggered during evaluation.

    Returns:
        dict: Policy evaluation payload.
    """
    return {
        "outcome": outcome,
        "risk_level": risk_level,
        "requires_manager_approval": requires_manager_approval,
        "is_blocked": is_blocked,
        "primary_reason": primary_reason,
        "rules_triggered": rules_triggered,
    }