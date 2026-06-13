"""Data layer: market-data fetching and caching.

Wraps the market-data source (yfinance) behind a thin, swappable interface and
caches dividend-adjusted prices to parquet. Data robustness — delisted tickers,
non-overlapping histories, market holidays — is handled here, never in core/.
"""
