"""
Idempotency key generation for execution requests.

The same approved billing correction should always produce the same
idempotency key so retries, refreshes, and duplicate button clicks do not
create duplicate money-impacting execution.
"""


def generate_idempotency_key(
    case_id,
    approval_id,
    operation_type,
    approved_amount_cents,
):
    """
    Generate a deterministic idempotency key for a billing execution request.

    Args:
        case_id (str): Billing case identifier.
        approval_id (str): Human approval identifier.
        operation_type (str): Execution operation type.
        approved_amount_cents (int): Approved amount in minor units.

    Returns:
        str: Deterministic idempotency key.
    """
    normalized_operation = operation_type.strip().lower()

    return (
        f"billing_adjustment:"
        f"{case_id}:"
        f"{approval_id}:"
        f"{normalized_operation}:"
        f"{int(approved_amount_cents)}"
    )