"""FastAPI backend exposing core/ over REST.

A second UI surface alongside the Streamlit ``app/`` package: both reuse the same
framework-free modules (``core/``, ``data/``, ``storage/``) and stay isolated from
each other. No finance/ML math lives here — only HTTP wiring.
"""
