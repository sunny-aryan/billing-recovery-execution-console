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
import uuid

from src.dependencies.dependency_modes import (
    DEPENDENCY_MODE_FORCED_MOCK,
    DEPENDENCY_MODE_LIVE,
    RUNTIME_RESULT_FAILED_SAFELY,
    RUNTIME_RESULT_FORCED_MOCK_USED,
    RUNTIME_RESULT_LIVE_SUCCESS,
    STRIPE_DEPENDENCY,
)
from src.execution.execution_rules import (
    ERROR_PERMANENT,
    ERROR_TRANSIENT,
    ERROR_UNKNOWN,
    PROVIDER_FAILED,
    PROVIDER_SUCCEEDED,
    PROVIDER_TIMEOUT,
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


def create_test_payment_intent(case, idempotency_key):
    """
    Create and confirm a Stripe test-mode PaymentIntent.

    This is a real Stripe test-mode API call. It creates a successful test payment
    using Stripe's test payment method pm_card_visa.

    Args:
        case (dict): Billing case record.
        idempotency_key (str): Idempotency key for Stripe POST request.

    Returns:
        dict: Stripe payment metadata.
    """
    configure_stripe_client()

    payment_intent = stripe.PaymentIntent.create(
        amount=int(case["amount_cents"]),
        currency=case["currency"].lower(),
        payment_method="pm_card_visa",
        confirm=True,
        automatic_payment_methods={
            "enabled": True,
            "allow_redirects": "never",
        },
        metadata={
            "case_id": case["case_id"],
            "invoice_id": case["invoice_id"],
            "purpose": "billing_recovery_test_payment",
        },
        idempotency_key=idempotency_key,
    )

    charge_id = None

    if getattr(payment_intent, "latest_charge", None):
        charge_id = payment_intent.latest_charge

    return {
        "payment_intent_id": payment_intent.id,
        "charge_id": charge_id,
        "amount_cents": payment_intent.amount,
        "currency": payment_intent.currency.upper(),
        "payment_status": payment_intent.status,
        "raw_status": payment_intent.status,
    }


def build_mock_test_payment(case):
    """
    Build deterministic mock test payment metadata without calling Stripe.

    Args:
        case (dict): Billing case record.

    Returns:
        dict: Mock payment metadata.
    """
    return {
        "payment_intent_id": f"pi_mock_{case['case_id'].lower()}",
        "charge_id": f"ch_mock_{case['case_id'].lower()}",
        "amount_cents": int(case["amount_cents"]),
        "currency": case["currency"],
        "payment_status": "succeeded",
        "raw_status": "mock_succeeded",
    }


def build_fallback_test_payment(case):
    """
    Build fallback payment metadata when live Stripe setup fails.

    Args:
        case (dict): Billing case record.

    Returns:
        dict: Fallback payment metadata.
    """
    fallback_id = uuid.uuid4().hex[:10]

    return {
        "payment_intent_id": f"pi_fallback_{fallback_id}",
        "charge_id": f"ch_fallback_{fallback_id}",
        "amount_cents": int(case["amount_cents"]),
        "currency": case["currency"],
        "payment_status": "fallback_created",
        "raw_status": "fallback_created",
    }

def execute_test_mode_refund(execution_request, stripe_test_payment):
    """
    Execute a real Stripe test-mode refund.

    Args:
        execution_request (dict): Durable execution request.
        stripe_test_payment (dict): Stored Stripe test payment metadata.

    Returns:
        dict: Provider-like response payload.
    """
    configure_stripe_client()

    refund = stripe.Refund.create(
        payment_intent=stripe_test_payment["payment_intent_id"],
        amount=int(execution_request["approved_amount_cents"]),
        metadata={
            "case_id": execution_request["case_id"],
            "execution_request_id": execution_request["execution_request_id"],
            "approval_id": execution_request["approval_id"],
            "source": "billing_recovery_execution_console",
        },
        idempotency_key=execution_request["idempotency_key"],
    )

    return {
        "provider_status": PROVIDER_SUCCEEDED,
        "provider_object_id": refund.id,
        "error_type": None,
        "error_code": None,
        "error_message": None,
        "response_payload": {
            "id": refund.id,
            "status": refund.status,
            "payment_intent": stripe_test_payment["payment_intent_id"],
            "charge": getattr(refund, "charge", None),
            "amount_cents": refund.amount,
            "currency": refund.currency.upper(),
            "idempotency_key": execution_request["idempotency_key"],
        },
    }


def build_mock_refund_response(execution_request):
    """
    Build deterministic mock refund response without calling Stripe.

    Args:
        execution_request (dict): Durable execution request.

    Returns:
        dict: Provider-like response payload.
    """
    provider_object_id = f"re_mock_{execution_request['execution_request_id'].lower()}"

    return {
        "provider_status": PROVIDER_SUCCEEDED,
        "provider_object_id": provider_object_id,
        "error_type": None,
        "error_code": None,
        "error_message": None,
        "response_payload": {
            "id": provider_object_id,
            "status": "succeeded",
            "payment_intent": "mock_payment_intent",
            "amount_cents": execution_request["approved_amount_cents"],
            "currency": execution_request["currency"],
            "idempotency_key": execution_request["idempotency_key"],
        },
    }


def build_stripe_refund_fallback_response(execution_request, error):
    """
    Build safe fallback response when Stripe refund execution fails.

    Args:
        execution_request (dict): Durable execution request.
        error (Exception): Stripe or runtime error.

    Returns:
        dict: Provider-like response payload.
    """
    error_message = str(error)
    error_code = _extract_stripe_error_code(error)
    error_type = _classify_stripe_error(error)

    if error_type == ERROR_TRANSIENT:
        provider_status = PROVIDER_FAILED
    elif error_type == ERROR_PERMANENT:
        provider_status = PROVIDER_FAILED
    else:
        provider_status = PROVIDER_TIMEOUT

    return {
        "provider_status": provider_status,
        "provider_object_id": None,
        "error_type": error_type,
        "error_code": error_code,
        "error_message": error_message,
        "response_payload": {
            "status": "failed_or_unknown",
            "reason": error_code,
            "message": error_message,
            "retryable": error_type == ERROR_TRANSIENT,
            "idempotency_key": execution_request["idempotency_key"],
        },
    }


def _classify_stripe_error(error):
    """
    Classify Stripe errors into internal error categories.
    """
    if isinstance(error, stripe.error.RateLimitError):
        return ERROR_TRANSIENT

    if isinstance(error, stripe.error.APIConnectionError):
        return ERROR_TRANSIENT

    if isinstance(error, stripe.error.APIError):
        return ERROR_TRANSIENT

    if isinstance(error, stripe.error.InvalidRequestError):
        return ERROR_PERMANENT

    if isinstance(error, stripe.error.AuthenticationError):
        return ERROR_PERMANENT

    if isinstance(error, stripe.error.PermissionError):
        return ERROR_PERMANENT

    return ERROR_UNKNOWN


def _extract_stripe_error_code(error):
    """
    Extract a useful error code from Stripe errors.
    """
    code = getattr(error, "code", None)

    if code:
        return code

    http_status = getattr(error, "http_status", None)

    if http_status:
        return f"stripe_http_{http_status}"

    return error.__class__.__name__