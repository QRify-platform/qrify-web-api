"""Postgres connection pool."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

_pool: ConnectionPool | None = None

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS qr_codes (
    id          UUID PRIMARY KEY,
    source_url  TEXT NOT NULL,
    s3_key      TEXT NOT NULL UNIQUE,
    user_id     TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

MIGRATE_SQL = [
    "ALTER TABLE qr_codes ADD COLUMN IF NOT EXISTS user_id TEXT",
    "CREATE INDEX IF NOT EXISTS idx_qr_codes_user_id ON qr_codes (user_id)",
]


def init_db() -> None:
    global _pool
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not set. "
            "In cluster it comes from the qrify-web-api-db secret (ESO)."
        )

    _pool = ConnectionPool(
        conninfo=database_url,
        min_size=1,
        max_size=5,
        kwargs={"row_factory": dict_row},
        open=True,
    )
    with _pool.connection() as conn:
        conn.execute(SCHEMA_SQL)
        for stmt in MIGRATE_SQL:
            conn.execute(stmt)
        conn.commit()


def close_db() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def get_connection() -> Iterator:
    if _pool is None:
        raise RuntimeError("Database pool is not initialized")
    with _pool.connection() as conn:
        yield conn
