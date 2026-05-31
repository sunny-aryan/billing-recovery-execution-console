from src.execution.idempotency import generate_idempotency_key


def test_idempotency_key_is_deterministic():
    key_1 = generate_idempotency_key(
        case_id="CASE-1001",
        approval_id="APP-123",
        operation_type="refund",
        approved_amount_cents=12000,
    )

    key_2 = generate_idempotency_key(
        case_id="CASE-1001",
        approval_id="APP-123",
        operation_type="refund",
        approved_amount_cents=12000,
    )

    assert key_1 == key_2


def test_idempotency_key_changes_when_approval_changes():
    key_1 = generate_idempotency_key(
        case_id="CASE-1001",
        approval_id="APP-123",
        operation_type="refund",
        approved_amount_cents=12000,
    )

    key_2 = generate_idempotency_key(
        case_id="CASE-1001",
        approval_id="APP-456",
        operation_type="refund",
        approved_amount_cents=12000,
    )

    assert key_1 != key_2


def test_idempotency_key_normalizes_operation_type():
    key = generate_idempotency_key(
        case_id="CASE-1001",
        approval_id="APP-123",
        operation_type=" Refund ",
        approved_amount_cents=12000,
    )

    assert key == "billing_adjustment:CASE-1001:APP-123:refund:12000"