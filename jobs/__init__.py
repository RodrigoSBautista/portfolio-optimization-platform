"""Jobs layer: scheduled tasks.

Phase 1: a local, idempotent daily refresh that writes portfolio valuations.
Production: invoked by a GitHub Actions cron against the hosted database.
"""
