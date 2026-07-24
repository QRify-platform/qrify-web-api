"""
QR use-cases: preview (no persistence), save (S3 + DB), and fetch by id.

This is the "service" layer — no FastAPI types here, so it's easy to test
and easy to explain in an interview.
"""

from __future__ import annotations

import base64
from io import BytesIO
from uuid import UUID, uuid4

import qrcode
from fastapi import HTTPException

from db import qr_codes as qr_repo
from utils.s3_utils import PRESIGN_EXPIRES, delete_object, presign_get, upload_png


def generate_preview(source_url: str) -> dict:
    """
    Render a PNG and return it as a data URL.
    Does not touch S3 or Postgres — save is a separate explicit step.
    """
    png = _render_png(source_url)
    b64 = base64.standard_b64encode(png.getvalue()).decode("ascii")
    return {
        "source_url": source_url,
        "qr_code_url": f"data:image/png;base64,{b64}",
    }


def create_qr_code(source_url: str, *, user_id: str) -> dict:
    """
    Persist a QR: render → S3 → DB row owned by Cognito sub.
    """
    qr_id = uuid4()
    s3_key = f"qr_codes/{qr_id}.png"

    png = _render_png(source_url)
    try:
        upload_png(png, s3_key)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Failed to upload QR image to S3") from exc

    try:
        row = qr_repo.insert_qr_code(
            qr_id=qr_id,
            source_url=source_url,
            s3_key=s3_key,
            user_id=user_id,
        )
    except Exception as exc:
        # Image may already be in S3; for a demo we leave it (orphan cleanup is a later topic).
        raise HTTPException(status_code=503, detail="Failed to save QR metadata") from exc

    return _with_download_url(row)


def get_qr_code(qr_id: str, *, user_id: str) -> dict:
    """Look up metadata by id; only the owner can read."""
    try:
        parsed = UUID(qr_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="id must be a UUID") from exc

    row = qr_repo.get_qr_code_by_id(parsed)
    if row is None:
        raise HTTPException(status_code=404, detail="QR code not found")

    if row.get("user_id") and row["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not your QR code")

    return _with_download_url(row)


def list_my_qr_codes(*, user_id: str) -> list[dict]:
    rows = qr_repo.list_qr_codes_for_user(user_id)
    return [_with_download_url(row) for row in rows]


def delete_qr_code(qr_id: str, *, user_id: str) -> None:
    """Owner-only delete: remove DB row, then best-effort delete S3 object."""
    try:
        parsed = UUID(qr_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="id must be a UUID") from exc

    existing = qr_repo.get_qr_code_by_id(parsed)
    if existing is None:
        raise HTTPException(status_code=404, detail="QR code not found")
    if existing.get("user_id") and existing["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not your QR code")

    deleted = qr_repo.delete_qr_code_for_user(parsed, user_id)
    if deleted is None:
        raise HTTPException(status_code=404, detail="QR code not found")

    try:
        delete_object(deleted["s3_key"])
    except Exception:
        # Row is gone; orphaned S3 object is acceptable for this demo.
        pass


def _render_png(source_url: str) -> BytesIO:
    # High module size + tight quiet zone so the PNG stays crisp when displayed large.
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=16,
        border=2,
    )
    qr.add_data(source_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#07080b", back_color="#ffffff").convert("RGB")

    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf


def _with_download_url(row: dict) -> dict:
    try:
        download_url = presign_get(row["s3_key"])
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Failed to create download URL") from exc

    return {
        **row,
        "download_url": download_url,
        "expires_in": PRESIGN_EXPIRES,
        # Compat for the existing Next.js UI (still reads qr_code_url).
        "qr_code_url": download_url,
    }
