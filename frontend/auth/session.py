import streamlit as st


def init_session():
    """Initialize all auth-related session keys."""
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("user", None)           # dict: name, email, picture
    st.session_state.setdefault("access_token", None)


def login(user: dict, access_token: str):
    """Mark the session as authenticated."""
    st.session_state["authenticated"] = True
    st.session_state["user"]          = user
    st.session_state["access_token"]  = access_token


def logout():
    """Clear the session."""
    st.session_state["authenticated"] = False
    st.session_state["user"]          = None
    st.session_state["access_token"]  = None


def is_authenticated() -> bool:
    return st.session_state.get("authenticated", False)


def current_user() -> dict | None:
    return st.session_state.get("user")