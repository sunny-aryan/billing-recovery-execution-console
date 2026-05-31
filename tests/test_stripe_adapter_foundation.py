from src.dependencies.dependency_modes import (
    DEPENDENCY_MODE_FORCED_MOCK,
    DEPENDENCY_MODE_LIVE,
    RUNTIME_RESULT_FAILED_SAFELY,
    RUNTIME_RESULT_FORCED_MOCK_USED,
    RUNTIME_RESULT_LIVE_SUCCESS,
)
from src.providers.stripe_adapter import (
    StripeBillingAdapter,
    build_stripe_runtime_context,
    is_stripe_configured,
)


def test_stripe_configured_requires_test_key():
    assert is_stripe_configured("sk_test_abc123") is True
    assert is_stripe_configured("sk_live_abc123") is False
    assert is_stripe_configured("") is False
    assert is_stripe_configured(None) is False


def test_stripe_adapter_reports_missing_key():
    adapter = StripeBillingAdapter(api_key="")

    status = adapter.get_configuration_status()

    assert status["is_configured"] is False
    assert status["safe_for_live_calls"] is False


def test_stripe_adapter_reports_live_key_as_invalid():
    adapter = StripeBillingAdapter(api_key="sk_live_abc123")

    status = adapter.get_configuration_status()

    assert status["is_configured"] is False
    assert status["safe_for_live_calls"] is False


def test_stripe_adapter_reports_test_key_as_configured():
    adapter = StripeBillingAdapter(api_key="sk_test_abc123")

    status = adapter.get_configuration_status()

    assert status["is_configured"] is True
    assert status["safe_for_live_calls"] is True


def test_forced_mock_runtime_context_does_not_require_stripe_key(monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)

    context = build_stripe_runtime_context(DEPENDENCY_MODE_FORCED_MOCK)

    assert context.runtime_result == RUNTIME_RESULT_FORCED_MOCK_USED
    assert context.source == "mock_provider"


def test_live_runtime_context_fails_safely_without_key(monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)

    context = build_stripe_runtime_context(DEPENDENCY_MODE_LIVE)

    assert context.runtime_result == RUNTIME_RESULT_FAILED_SAFELY
    assert context.is_configured is False


def test_live_runtime_context_succeeds_with_test_key(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_abc123")

    context = build_stripe_runtime_context(DEPENDENCY_MODE_LIVE)

    assert context.runtime_result == RUNTIME_RESULT_LIVE_SUCCESS
    assert context.is_configured is True
    assert context.source == "stripe_test_mode"