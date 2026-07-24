"""CRUD helpers for the qr_codes table (no HTTP / S3 here)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from db.connection import get_connection


def insert_qr_code(
    *,
    qr_id: UUID,
    source_url: str,
    s3_key: str,
    user_id: str,
) -> dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute(
            """
            INSERT INTO qr_codes (id, source_url, s3_key, user_id)
            VALUES (%s, %s, %s, %s)
            RETURNING id, source_url, s3_key, user_id, created_at
            """,
            (str(qr_id), source_url, s3_key, user_id),
        ).fetchone()
        conn.commit()
    return _normalize(row)


def get_qr_code_by_id(qr_id: UUID) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, source_url, s3_key, user_id, created_at
            FROM qr_codes
            WHERE id = %s
            """,
            (str(qr_id),),
        ).fetchone()
    return _normalize(row) if row else None


def list_qr_codes_for_user(user_id: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, source_url, s3_key, user_id, created_at
            FROM qr_codes
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (user_id,),
        ).fetchall()
    return [_normalize(row) for row in rows]


def _normalize(row: dict[str, Any]) -> dict[str, Any]:
    """Make UUID / datetime JSON-friendly for responses."""
    created: datetime = row["created_at"]
    return {
        "id": str(row["id"]),
        "source_url": row["source_url"],
        "s3_key": row["s3_key"],
        "user_id": row.get("user_id"),
        "created_at": created.isoformat(),
    }
