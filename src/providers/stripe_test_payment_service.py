"""
Stripe test payment setup service.

This service prepares a refundable test payment for a billing correction case.

Modes:
- forced_mock: create deterministic mock payment metadata, no Stripe API call
- live: create a real Stripe test-mode PaymentIntent
- live failure: create deterministic fallback metadata and record fallback usage

This commit prepares Stripe refund execution but does not execute refunds yet.
"""

import uuid

from src.audit.audit_service import record_audit_event
from src.database import get_connection
from src.dependencies.dependency_modes import (
    DEPENDENCY_MODE_FORCED_MOCK,
    DEPENDENCY_MODE_LIVE,
    RUNTIME_RESULT_FALLBACK_USED,
    RUNTIME_RESULT_FORCED_MOCK_USED,
    RUNTIME_RESULT_LIVE_SUCCESS,
)
from src.providers.stripe_adapter import (
    build_fallback_test_payment,
    build_mock_test_payment,
    create_test_payment_intent,
)


def create_and_store_stripe_test_payment(case, dependency_mode):
    """
    Create or simulate a Stripe test payment and store it locally.

    Args:
        case (dict): Billing case record.
        dependency_mode (str): live or forced_mock.

    Returns:
        dict: Stored test payment metadata.
    """
    existing_payment = get_latest_stripe_test_payment(case["case_id"])

    if existing_payment is not None:
        return existing_payment, False

    test_payment_id = f"STP-{uuid.uuid4().hex[:8].upper()}"
    idempotency_key = _generate_test_payment_idempotency_key(
        case=case,
        test_payment_id=test_payment_id,
    )

    if dependency_mode == DEPENDENCY_MODE_FORCED_MOCK:
        payment_payload = build_mock_test_payment(case)
        runtime_result = RUNTIME_RESULT_FORCED_MOCK_USED
        source = "mock_stripe_test_payment"
        error_message = None

    elif dependency_mode == DEPENDENCY_MODE_LIVE:
        try:
            payment_payload = create_test_payment_intent(
                case=case,
                idempotency_key=idempotency_key,
            )
            runtime_result = RUNTIME_RESULT_LIVE_SUCCESS
            source = "stripe_test_mode"
            error_message = None
        except Exception as error:
            payment_payload = build_fallback_test_payment(case)
            runtime_result = RUNTIME_RESULT_FALLBACK_USED
            source = "stripe_test_payment_fallback"
            error_message = str(error)

    else:
        payment_payload = build_fallback_test_payment(case)
        runtime_result = RUNTIME_RESULT_FALLBACK_USED
        source = "stripe_test_payment_fallback"
        error_message = f"Unsupported dependency mode: {dependency_mode}"

    stored_payment = _store_stripe_test_payment(
        test_payment_id=test_payment_id,
        case=case,
        dependency_mode=dependency_mode,
        runtime_result=runtime_result,
        source=source,
        payment_payload=payment_payload,
        error_message=error_message,
    )

    record_audit_event(
        case_id=case["case_id"],
        entity_type="stripe_test_payment",
        entity_id=test_payment_id,
        event_type="stripe_test_payment_created",
        actor_type="system",
        actor_name="stripe_test_payment_service",
        details={
            "dependency_mode": dependency_mode,
            "runtime_result": runtime_result,
            "source": source,
            "payment_intent_id": payment_payload["payment_intent_id"],
            "charge_id": payment_payload["charge_id"],
            "amount_cents": payment_payload["amount_cents"],
            "currency": payment_payload["currency"],
            "payment_status": payment_payload["payment_status"],
            "error_message": error_message,
        },
    )

    return stored_payment, True


def get_latest_stripe_test_payment(case_id):
    """
    Fetch the latest Stripe test payment for a case.

    Args:
        case_id (str): Billing case identifier.

    Returns:
        dict | None: Stored test payment metadata.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            stripe_test_payment_id,
            case_id,
            dependency_mode,
            runtime_result,
            source,
            payment_intent_id,
            charge_id,
            amount_cents,
            currency,
            payment_status,
            error_message,
            created_at
        FROM stripe_test_payments
        WHERE case_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (case_id,),
    )

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return dict(row)


def _store_stripe_test_payment(
    test_payment_id,
    case,
    dependency_mode,
    runtime_result,
    source,
    payment_payload,
    error_message,
):
    """
    Store Stripe test payment metadata.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO stripe_test_payments (
            stripe_test_payment_id,
            case_id,
            dependency_mode,
            runtime_result,
            source,
            payment_intent_id,
            charge_id,
            amount_cents,
            currency,
            payment_status,
            error_message
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            test_payment_id,
            case["case_id"],
            dependency_mode,
            runtime_result,
            source,
            payment_payload["payment_intent_id"],
            payment_payload["charge_id"],
            int(payment_payload["amount_cents"]),
            payment_payload["currency"],
            payment_payload["payment_status"],
            error_message,
        ),
    )

    conn.commit()
    conn.close()

    return {
        "stripe_test_payment_id": test_payment_id,
        "case_id": case["case_id"],
        "dependency_mode": dependency_mode,
        "runtime_result": runtime_result,
        "source": source,
        "payment_intent_id": payment_payload["payment_intent_id"],
        "charge_id": payment_payload["charge_id"],
        "amount_cents": int(payment_payload["amount_cents"]),
        "currency": payment_payload["currency"],
        "payment_status": payment_payload["payment_status"],
        "error_message": error_message,
    }


def _generate_test_payment_idempotency_key(case, test_payment_id):
    """
    Generate idempotency key for one local Stripe test payment setup operation.

    The key includes the local stripe_test_payment_id so resetting the local DB
    and creating a new test payment does not accidentally reuse an old Stripe
    PaymentIntent from a previous demo run.
    """
    return (
        f"stripe_test_payment:"
        f"{test_payment_id}:"
        f"{case['case_id']}:"
        f"{case['invoice_id']}:"
        f"{int(case['amount_cents'])}:"
        f"{case['currency'].lower()}"
    )