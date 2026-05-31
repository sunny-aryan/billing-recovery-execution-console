"""
Provider adapter base definitions.

The execution system should depend on provider-shaped behavior, not directly
on one external provider's SDK.

Mock provider:
- used for deterministic success/failure/timeout demos

Stripe provider:
- used for real test-mode external API writes in later commits
"""

from dataclasses import dataclass


@dataclass
class ProviderRuntimeContext:
    """
    Describes how a provider dependency behaved for a specific operation.

    dependency_mode:
        User-selected mode, such as live or forced_mock.

    runtime_result:
        Runtime result, such as live_success, forced_mock_used, fallback_used,
        or failed_safely.

    source:
        Actual source used, such as stripe_test_mode, mock_provider, or configuration_check.
    """

    dependency: str
    dependency_mode: str
    runtime_result: str
    source: str
    is_configured: bool
    message: str
    error_message: str | None = None


class ProviderAdapter:
    """
    Minimal provider adapter contract.

    Future provider adapters should implement execution and reconciliation
    behavior behind this boundary.
    """

    provider_name = "base_provider"

    def is_configured(self):
        """
        Return whether this provider has enough configuration to run live calls.
        """
        raise NotImplementedError

    def get_configuration_status(self):
        """
        Return provider configuration status for UI/debugging.
        """
        raise NotImplementedError