"""
HTTP layer (controller / router).

Keep this thin: validate input → call service → return status codes.
No SQL or boto3 here.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from auth.cognito import get_current_user
from services.qr_service import (
    create_qr_code,
    delete_qr_code,
    generate_preview,
    get_qr_code,
    list_my_qr_codes,
)
from utils.rate_limit import client_ip, generate_limiter, write_limiter

router = APIRouter()


class PayloadRequest(BaseModel):
    """QR payload: https://..., mailto:, WIFI:, plain text, vCard, etc."""

    url: str = Field(..., min_length=1, max_length=4096)


class QrCodeResponse(BaseModel):
    id: str
    source_url: str
    s3_key: str
    user_id: str | None = None
    created_at: str
    download_url: str
    expires_in: int
    # Compat alias used by the web UI.
    qr_code_url: str


class GeneratePreviewResponse(BaseModel):
    source_url: str
    qr_code_url: str  # data:image/png;base64,... — not persisted


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/qr-codes", response_model=QrCodeResponse, status_code=201)
def create_qr(
    request: Request,
    body: PayloadRequest,
    user: dict[str, Any] = Depends(get_current_user),
):
    """Explicit save: S3 + DB, owned by the signed-in user."""
    write_limiter.hit(client_ip(request))
    return create_qr_code(body.url.strip(), user_id=user["sub"])


@router.get("/qr-codes", response_model=list[QrCodeResponse])
def list_qr(user: dict[str, Any] = Depends(get_current_user)):
    """List QR codes owned by the authenticated user."""
    return list_my_qr_codes(user_id=user["sub"])


@router.get("/qr-codes/{qr_id}", response_model=QrCodeResponse)
def read_qr(qr_id: str, user: dict[str, Any] = Depends(get_current_user)):
    """Fetch by id and re-issue a presigned URL (owner only)."""
    return get_qr_code(qr_id, user_id=user["sub"])


@router.delete("/qr-codes/{qr_id}", status_code=204)
def remove_qr(
    request: Request,
    qr_id: str,
    user: dict[str, Any] = Depends(get_current_user),
):
    """Delete a saved code (owner only)."""
    write_limiter.hit(client_ip(request))
    delete_qr_code(qr_id, user_id=user["sub"])


@router.post("/generate-qr/", response_model=GeneratePreviewResponse)
def generate_qr_preview(request: Request, body: PayloadRequest):
    """
    Preview only — returns a data-URL PNG. Does not save to S3 or Postgres.
    Use POST /qr-codes to persist. Rate-limited per client IP.
    """
    generate_limiter.hit(client_ip(request))
    try:
        return generate_preview(body.url.strip())
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="QR code generation failed") from exc
