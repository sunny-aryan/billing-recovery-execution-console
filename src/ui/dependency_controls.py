import streamlit as st

from src.providers.stripe_adapter import build_stripe_runtime_context
from src.dependencies.dependency_modes import (
    DEPENDENCY_MODE_FORCED_MOCK,
    DEPENDENCY_MODE_LIVE,
    get_mode_description,
    get_mode_label,
)
from src.dependencies.dependency_state import (
    get_openai_mode,
    get_stripe_mode,
    set_openai_mode,
    set_stripe_mode,
)


def render_dependency_controls():
    """
    Render sidebar controls for external dependency modes.

    These controls make the demo resilient:
    - Live mode can call real external APIs in later commits.
    - Forced mock mode avoids external API calls for demo safety.
    """
    st.subheader("Dependency Controls")

    st.caption(
        "Choose whether external dependencies should use live APIs or forced mock behavior."
    )

    openai_mode = st.radio(
        "OpenAI mode",
        options=[DEPENDENCY_MODE_FORCED_MOCK, DEPENDENCY_MODE_LIVE],
        index=_get_mode_index(get_openai_mode()),
        format_func=get_mode_label,
        key="openai_mode_radio",
    )
    set_openai_mode(openai_mode)

    st.caption(get_mode_description("OpenAI", openai_mode))

    stripe_mode = st.radio(
        "Stripe mode",
        options=[DEPENDENCY_MODE_FORCED_MOCK, DEPENDENCY_MODE_LIVE],
        index=_get_mode_index(get_stripe_mode()),
        format_func=get_mode_label,
        key="stripe_mode_radio",
    )
    set_stripe_mode(stripe_mode)

    st.caption(get_mode_description("Stripe", stripe_mode))


def render_dependency_status_summary():
    """
    Render a compact dependency status summary for non-sidebar pages.
    """
    openai_mode = get_openai_mode()
    stripe_mode = get_stripe_mode()
    stripe_context = build_stripe_runtime_context(stripe_mode)

    col_1, col_2 = st.columns(2)

    with col_1:
        st.metric("OpenAI mode", get_mode_label(openai_mode))

        if openai_mode == DEPENDENCY_MODE_FORCED_MOCK:
            st.caption("OpenAI calls are disabled for demo safety.")
        else:
            st.caption("OpenAI live calls are enabled when credentials are configured.")

    with col_2:
        st.metric("Stripe mode", get_mode_label(stripe_mode))

        if stripe_mode == DEPENDENCY_MODE_FORCED_MOCK:
            st.caption("Stripe API calls are disabled for demo safety.")
        else:
            st.caption("Stripe test-mode API calls are enabled when configured.")

    with st.expander("Stripe provider readiness", expanded=False):
        col_a, col_b, col_c = st.columns(3)

        with col_a:
            st.metric("Runtime result", stripe_context.runtime_result)

        with col_b:
            st.metric("Source", stripe_context.source)

        with col_c:
            st.metric("Configured", "Yes" if stripe_context.is_configured else "No")

        st.write(stripe_context.message)

        if stripe_context.error_message:
            st.warning(stripe_context.error_message)

    st.caption(
        "Forced mock is user-selected demo behavior. Fallback is dependency-specific runtime recovery after a live call fails."
    )


def _get_mode_index(mode):
    """
    Return radio index for selected dependency mode.
    """
    if mode == DEPENDENCY_MODE_LIVE:
        return 1

    return 0