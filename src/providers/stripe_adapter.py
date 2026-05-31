"""
Stripe provider adapter foundation.

Commit 15 only adds Stripe configuration and provider-boundary plumbing.
It intentionally does not create PaymentIntents, Charges, Refunds, or call
Stripe APIs yet.

Future commits will add:
- Stripe test payment setup
- Stripe test-mode refund execution
- Stripe refund reconciliation
"""

import os

import stripe

from src.dependencies.dependency_modes import (
    DEPENDENCY_MODE_FORCED_MOCK,
    DEPENDENCY_MODE_LIVE,
    RUNTIME_RESULT_FAILED_SAFELY,
    RUNTIME_RESULT_FORCED_MOCK_USED,
    RUNTIME_RESULT_LIVE_SUCCESS,
    STRIPE_DEPENDENCY,
)
from src.providers.base import ProviderAdapter, ProviderRuntimeContext


STRIPE_TEST_KEY_PREFIX = "sk_test_"


class StripeBillingAdapter(ProviderAdapter):
    """
    Stripe test-mode provider adapter.

    This adapter will eventually execute real Stripe test-mode refund operations.
    For now, it only validates local configuration and reports provider readiness.
    """

    provider_name = "stripe_test_mode"

    def __init__(self, api_key=None):
        self.api_key = api_key or get_stripe_secret_key()

    def is_configured(self):
        """
        Return whether Stripe has a plausible test secret key.
        """
        return is_stripe_configured(self.api_key)

    def get_configuration_status(self):
        """
        Return configuration status for UI display and diagnostics.
        """
        if not self.api_key:
            return {
                "provider": self.provider_name,
                "is_configured": False,
                "message": "Stripe secret key is not configured.",
                "safe_for_live_calls": False,
            }

        if not self.api_key.startswith(STRIPE_TEST_KEY_PREFIX):
            return {
                "provider": self.provider_name,
                "is_configured": False,
                "message": "Configured Stripe key does not look like a test-mode secret key.",
                "safe_for_live_calls": False,
            }

        return {
            "provider": self.provider_name,
            "is_configured": True,
            "message": "Stripe test-mode secret key is configured.",
            "safe_for_live_calls": True,
        }


def get_stripe_secret_key():
    """
    Read Stripe secret key from environment.

    The app should load .env in local development before this is called.
    """
    return os.getenv("STRIPE_SECRET_KEY", "").strip()


def is_stripe_configured(api_key=None):
    """
    Return whether Stripe has a plausible test-mode secret key.
    """
    key = api_key if api_key is not None else get_stripe_secret_key()

    return bool(key and key.startswith(STRIPE_TEST_KEY_PREFIX))


def configure_stripe_client(api_key=None):
    """
    Configure Stripe SDK with the provided or environment secret key.

    This does not call Stripe. It only sets local SDK configuration.
    """
    key = api_key if api_key is not None else get_stripe_secret_key()

    if not is_stripe_configured(key):
        raise ValueError(
            "Stripe test-mode secret key is missing or invalid. "
            "Expected a key starting with sk_test_."
        )

    stripe.api_key = key

    return stripe


def build_stripe_runtime_context(dependency_mode):
    """
    Build a Stripe runtime context without making an external API call.

    Args:
        dependency_mode (str): live or forced_mock.

    Returns:
        ProviderRuntimeContext: Stripe dependency status.
    """
    adapter = StripeBillingAdapter()
    status = adapter.get_configuration_status()

    if dependency_mode == DEPENDENCY_MODE_FORCED_MOCK:
        return ProviderRuntimeContext(
            dependency=STRIPE_DEPENDENCY,
            dependency_mode=dependency_mode,
            runtime_result=RUNTIME_RESULT_FORCED_MOCK_USED,
            source="mock_provider",
            is_configured=status["is_configured"],
            message=(
                "Stripe is in forced mock mode. No Stripe API call will be made."
            ),
            error_message=None,
        )

    if dependency_mode == DEPENDENCY_MODE_LIVE and status["is_configured"]:
        return ProviderRuntimeContext(
            dependency=STRIPE_DEPENDENCY,
            dependency_mode=dependency_mode,
            runtime_result=RUNTIME_RESULT_LIVE_SUCCESS,
            source="stripe_test_mode",
            is_configured=True,
            message=(
                "Stripe is configured for live test-mode behavior. "
                "Future Stripe operations can use the test-mode adapter."
            ),
            error_message=None,
        )

    if dependency_mode == DEPENDENCY_MODE_LIVE and not status["is_configured"]:
        return ProviderRuntimeContext(
            dependency=STRIPE_DEPENDENCY,
            dependency_mode=dependency_mode,
            runtime_result=RUNTIME_RESULT_FAILED_SAFELY,
            source="configuration_check",
            is_configured=False,
            message=(
                "Stripe live mode was selected, but Stripe is not configured. "
                "Future Stripe operations should fail safely or fall back according to operation-specific rules."
            ),
            error_message=status["message"],
        )

    return ProviderRuntimeContext(
        dependency=STRIPE_DEPENDENCY,
        dependency_mode=dependency_mode,
        runtime_result=RUNTIME_RESULT_FAILED_SAFELY,
        source="configuration_check",
        is_configured=status["is_configured"],
        message="Unsupported Stripe dependency mode.",
        error_message=f"Unsupported dependency mode: {dependency_mode}",
    )