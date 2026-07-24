"""
QR use-cases: create (S3 + DB) and fetch by id (DB + fresh presign).

This is the "service" layer — no FastAPI types here, so it's easy to test
and easy to explain in an interview.
"""

from __future__ import annotations

from io import BytesIO
from uuid import UUID, uuid4

import qrcode
from fastapi import HTTPException

from db import qr_codes as qr_repo
from utils.s3_utils import PRESIGN_EXPIRES, presign_get, upload_png


def create_qr_code(source_url: str) -> dict:
    """
    1) Generate PNG
    2) Upload to S3 under a unique key
    3) Insert metadata row
    4) Return row + a fresh download_url
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
        )
    except Exception as exc:
        # Image may already be in S3; for a demo we leave it (orphan cleanup is a later topic).
        raise HTTPException(status_code=503, detail="Failed to save QR metadata") from exc

    return _with_download_url(row)


def get_qr_code(qr_id: str) -> dict:
    """Look up metadata by id and mint a NEW presigned URL (old ones may have expired)."""
    try:
        parsed = UUID(qr_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="id must be a UUID") from exc

    row = qr_repo.get_qr_code_by_id(parsed)
    if row is None:
        raise HTTPException(status_code=404, detail="QR code not found")

    return _with_download_url(row)


def _render_png(source_url: str) -> BytesIO:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(source_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = BytesIO()
    img.save(buf, format="PNG")
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
