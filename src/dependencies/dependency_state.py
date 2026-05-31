"""
Streamlit dependency mode state helpers.

These helpers keep external dependency demo controls consistent across the app.
"""

import streamlit as st

from src.dependencies.dependency_modes import (
    DEPENDENCY_MODE_FORCED_MOCK,
    DEPENDENCY_MODE_LIVE,
)


OPENAI_MODE_SESSION_KEY = "openai_dependency_mode"
STRIPE_MODE_SESSION_KEY = "stripe_dependency_mode"


def initialize_dependency_modes():
    """
    Initialize dependency mode values in Streamlit session state.
    """
    if OPENAI_MODE_SESSION_KEY not in st.session_state:
        st.session_state[OPENAI_MODE_SESSION_KEY] = DEPENDENCY_MODE_FORCED_MOCK

    if STRIPE_MODE_SESSION_KEY not in st.session_state:
        st.session_state[STRIPE_MODE_SESSION_KEY] = DEPENDENCY_MODE_FORCED_MOCK


def get_openai_mode():
    """
    Get the selected OpenAI dependency mode.
    """
    initialize_dependency_modes()
    return st.session_state[OPENAI_MODE_SESSION_KEY]


def get_stripe_mode():
    """
    Get the selected Stripe dependency mode.
    """
    initialize_dependency_modes()
    return st.session_state[STRIPE_MODE_SESSION_KEY]


def set_openai_mode(mode):
    """
    Set OpenAI dependency mode.
    """
    st.session_state[OPENAI_MODE_SESSION_KEY] = mode


def set_stripe_mode(mode):
    """
    Set Stripe dependency mode.
    """
    st.session_state[STRIPE_MODE_SESSION_KEY] = mode


def is_openai_forced_mock():
    """
    Return whether OpenAI is in forced mock mode.
    """
    return get_openai_mode() == DEPENDENCY_MODE_FORCED_MOCK


def is_stripe_forced_mock():
    """
    Return whether Stripe is in forced mock mode.
    """
    return get_stripe_mode() == DEPENDENCY_MODE_FORCED_MOCK


def is_openai_live():
    """
    Return whether OpenAI is in live mode.
    """
    return get_openai_mode() == DEPENDENCY_MODE_LIVE


def is_stripe_live():
    """
    Return whether Stripe is in live mode.
    """
    return get_stripe_mode() == DEPENDENCY_MODE_LIVE