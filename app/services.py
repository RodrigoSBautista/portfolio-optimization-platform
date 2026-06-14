"""Streamlit-side service helpers: cached DB factory, price service, price fetch.

Thin glue only — all business logic stays in core/, data/, storage/.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from data.cache import ParquetPriceCache
from data.prices import PriceService
from storage.db import create_db_engine, make_session_factory
from storage.models import Base


@st.cache_resource
def get_session_factory():
    engine = create_db_engine()
    # Dev convenience so the app runs out of the box; Alembic owns real migrations.
    Base.metadata.create_all(engine)
    return make_session_factory(engine)


@st.cache_resource
def get_price_service() -> PriceService:
    return PriceService(cache=ParquetPriceCache())


@st.cache_data(show_spinner="Fetching prices…")
def fetch_prices(tickers: tuple[str, ...], start: date, end: date | None) -> pd.DataFrame:
    """Cached adjusted-close fetch. Tickers passed as a tuple so the key is hashable."""
    return get_price_service().get_adjusted_close(list(tickers), start, end)
