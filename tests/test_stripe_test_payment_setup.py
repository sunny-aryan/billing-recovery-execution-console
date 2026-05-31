from src.cases.case_service import get_case_by_id
from src.dependencies.dependency_modes import (
    DEPENDENCY_MODE_FORCED_MOCK,
    DEPENDENCY_MODE_LIVE,
    RUNTIME_RESULT_FALLBACK_USED,
    RUNTIME_RESULT_FORCED_MOCK_USED,
    RUNTIME_RESULT_LIVE_SUCCESS,
)
from src.providers.stripe_test_payment_service import (
    create_and_store_stripe_test_payment,
    get_latest_stripe_test_payment,
)


def test_forced_mock_stripe_test_payment_is_stored(test_db):
    case = get_case_by_id("CASE-1003")

    payment, created_new = create_and_store_stripe_test_payment(
        case=case,
        dependency_mode=DEPENDENCY_MODE_FORCED_MOCK,
    )

    assert created_new is True
    assert payment["case_id"] == "CASE-1003"
    assert payment["runtime_result"] == RUNTIME_RESULT_FORCED_MOCK_USED
    assert payment["source"] == "mock_stripe_test_payment"
    assert payment["payment_intent_id"].startswith("pi_mock_")


def test_duplicate_stripe_test_payment_is_prevented(test_db):
    case = get_case_by_id("CASE-1003")

    first_payment, first_created = create_and_store_stripe_test_payment(
        case=case,
        dependency_mode=DEPENDENCY_MODE_FORCED_MOCK,
    )

    second_payment, second_created = create_and_store_stripe_test_payment(
        case=case,
        dependency_mode=DEPENDENCY_MODE_FORCED_MOCK,
    )

    assert first_created is True
    assert second_created is False
    assert first_payment["stripe_test_payment_id"] == second_payment["stripe_test_payment_id"]


def test_latest_stripe_test_payment_can_be_fetched(test_db):
    case = get_case_by_id("CASE-1003")

    create_and_store_stripe_test_payment(
        case=case,
        dependency_mode=DEPENDENCY_MODE_FORCED_MOCK,
    )

    latest = get_latest_stripe_test_payment("CASE-1003")

    assert latest is not None
    assert latest["case_id"] == "CASE-1003"
    assert latest["charge_id"]


def test_live_mode_falls_back_when_stripe_payment_setup_fails(test_db, monkeypatch):
    case = get_case_by_id("CASE-1003")

    def mock_stripe_failure(case, idempotency_key):
        raise RuntimeError("Simulated Stripe setup failure")

    monkeypatch.setattr(
        "src.providers.stripe_test_payment_service.create_test_payment_intent",
        mock_stripe_failure,
    )

    payment, created_new = create_and_store_stripe_test_payment(
        case=case,
        dependency_mode=DEPENDENCY_MODE_LIVE,
    )

    assert created_new is True
    assert payment["runtime_result"] == RUNTIME_RESULT_FALLBACK_USED
    assert payment["source"] == "stripe_test_payment_fallback"
    assert "Simulated Stripe setup failure" in payment["error_message"]


def test_live_mode_success_when_stripe_setup_is_mocked_successfully(
    test_db,
    monkeypatch,
):
    case = get_case_by_id("CASE-1003")

    def mock_stripe_success(case, idempotency_key):
        return {
            "payment_intent_id": "pi_test_success",
            "charge_id": "ch_test_success",
            "amount_cents": case["amount_cents"],
            "currency": case["currency"],
            "payment_status": "succeeded",
            "raw_status": "succeeded",
        }

    monkeypatch.setattr(
        "src.providers.stripe_test_payment_service.create_test_payment_intent",
        mock_stripe_success,
    )

    payment, created_new = create_and_store_stripe_test_payment(
        case=case,
        dependency_mode=DEPENDENCY_MODE_LIVE,
    )

    assert created_new is True
    assert payment["runtime_result"] == RUNTIME_RESULT_LIVE_SUCCESS
    assert payment["source"] == "stripe_test_mode"
    assert payment["payment_intent_id"] == "pi_test_success"