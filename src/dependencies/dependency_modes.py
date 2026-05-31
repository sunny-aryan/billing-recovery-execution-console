"""
Shared dependency mode constants and helpers.

External dependencies can run in live mode or forced mock mode.

Important distinction:
- forced_mock is a user-selected demo mode
- fallback_used is a runtime result after a live call fails

This file defines the shared mode vocabulary, but each dependency still owns
its own runtime behavior and fallback logic.
"""

# User-selected dependency modes.
DEPENDENCY_MODE_LIVE = "live"
DEPENDENCY_MODE_FORCED_MOCK = "forced_mock"

DEPENDENCY_MODES = [
    DEPENDENCY_MODE_LIVE,
    DEPENDENCY_MODE_FORCED_MOCK,
]

# Runtime results, to be used by later commits.
RUNTIME_RESULT_LIVE_SUCCESS = "live_success"
RUNTIME_RESULT_FORCED_MOCK_USED = "forced_mock_used"
RUNTIME_RESULT_FALLBACK_USED = "fallback_used"
RUNTIME_RESULT_FAILED_SAFELY = "failed_safely"

OPENAI_DEPENDENCY = "openai"
STRIPE_DEPENDENCY = "stripe"


def get_mode_label(mode):
    """
    Return a human-readable label for a dependency mode.
    """
    if mode == DEPENDENCY_MODE_LIVE:
        return "Live external API"

    if mode == DEPENDENCY_MODE_FORCED_MOCK:
        return "Forced mock / demo mode"

    return "Unknown mode"


def get_mode_description(dependency_name, mode):
    """
    Return a user-facing explanation for a dependency mode.
    """
    if mode == DEPENDENCY_MODE_LIVE:
        return (
            f"{dependency_name} is configured for live API behavior. "
            "If a future live call fails, the dependency-specific service should fall back safely."
        )

    if mode == DEPENDENCY_MODE_FORCED_MOCK:
        return (
            f"{dependency_name} is configured for forced mock behavior. "
            "No external API call should be made for this dependency."
        )

    return f"{dependency_name} mode is unknown."