"""Storage layer: SQLAlchemy models + repository (SQLite now, PostgreSQL later).

All reads/writes go through the repository, which always scopes queries by
``user_id`` so each user can only ever see their own data.
"""
