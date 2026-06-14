"""Streamlit auth UI + session helpers.

Password hashing/verification and the signup/login rules live in storage/ (framework
-free); this module only handles the Streamlit forms and ``st.session_state``. The
logged-in ``user_id`` gates every page.
"""

from __future__ import annotations

import streamlit as st

from app.services import get_session_factory
from storage.auth_service import AuthError, AuthService
from storage.db import session_scope
from storage.repository import Repository


def is_logged_in() -> bool:
    return st.session_state.get("user_id") is not None


def current_user_id() -> int | None:
    return st.session_state.get("user_id")


def current_username() -> str | None:
    return st.session_state.get("username")


def _set_user(user_id: int, username: str) -> None:
    st.session_state["user_id"] = user_id
    st.session_state["username"] = username


def logout() -> None:
    for key in ("user_id", "username", "current_spec"):
        st.session_state.pop(key, None)


def login_page() -> None:
    st.title("📈 Portfolio Platform")
    st.caption("Simulate, save, and track US stock/ETF portfolios. Educational use only.")

    login_tab, signup_tab = st.tabs(["Log in", "Sign up"])
    factory = get_session_factory()

    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in")
        if submitted:
            with session_scope(factory) as session:
                user = AuthService(Repository(session)).authenticate(username, password)
                authed = user is not None
                if authed:
                    _set_user(user.id, user.username)
            if authed:
                st.rerun()
            else:
                st.error("Invalid username or password.")

    with signup_tab:
        with st.form("signup_form"):
            new_username = st.text_input("Choose a username")
            new_password = st.text_input("Choose a password (min 8 chars)", type="password")
            created = st.form_submit_button("Create account")
        if created:
            try:
                with session_scope(factory) as session:
                    user = AuthService(Repository(session)).sign_up(new_username, new_password)
                    user_id, username = user.id, user.username
                _set_user(user_id, username)
                st.rerun()
            except AuthError as exc:
                st.error(str(exc))
