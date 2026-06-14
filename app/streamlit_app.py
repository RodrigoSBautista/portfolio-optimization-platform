"""Streamlit entry point: auth gate + sidebar navigation.

Run with:  uv run streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# `streamlit run app/streamlit_app.py` puts this file's dir (app/) on sys.path, not
# the project root — so make the top-level packages importable before importing them.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from app.auth import current_username, is_logged_in, login_page, logout
from app.views.builder import builder_page
from app.views.compare import compare_page
from app.views.simulation import simulation_page
from app.views.tracking import tracking_page
from core.constants import NOT_FINANCIAL_ADVICE

st.set_page_config(page_title="Portfolio Platform", page_icon="📈", layout="wide")

if not is_logged_in():
    login_page()
    st.stop()

PAGES = {
    "🧱 Build a portfolio": builder_page,
    "📈 Growth simulation": simulation_page,
    "⚖️ Compare portfolios": compare_page,
    "📊 Tracking dashboard": tracking_page,
}

with st.sidebar:
    st.markdown(f"👤 **{current_username()}**")
    if st.button("Log out"):
        logout()
        st.rerun()
    st.divider()
    selection = st.radio("Navigate", list(PAGES))
    st.divider()
    st.caption(NOT_FINANCIAL_ADVICE)

PAGES[selection]()
