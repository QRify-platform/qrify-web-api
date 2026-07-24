"""
HTTP layer (controller / router).

Keep this thin: validate input → call service → return status codes.
No SQL or boto3 here.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl

from auth.cognito import get_current_user
from services.qr_service import create_qr_code, get_qr_code, list_my_qr_codes

router = APIRouter()


class CreateQrRequest(BaseModel):
    url: HttpUrl


class QrCodeResponse(BaseModel):
    id: str
    source_url: str
    s3_key: str
    user_id: str | None = None
    created_at: str
    download_url: str
    expires_in: int
    qr_code_url: str  # alias of download_url for the current web UI


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/qr-codes", response_model=QrCodeResponse, status_code=201)
def create_qr(body: CreateQrRequest, user: dict[str, Any] = Depends(get_current_user)):
    """Preferred REST create: JSON body, returns durable id + temporary download_url."""
    return create_qr_code(str(body.url), user_id=user["sub"])


@router.get("/qr-codes", response_model=list[QrCodeResponse])
def list_qr(user: dict[str, Any] = Depends(get_current_user)):
    """List QR codes owned by the authenticated user."""
    return list_my_qr_codes(user_id=user["sub"])


@router.get("/qr-codes/{qr_id}", response_model=QrCodeResponse)
def read_qr(qr_id: str, user: dict[str, Any] = Depends(get_current_user)):
    """Fetch by id and re-issue a presigned URL (owner only)."""
    return get_qr_code(qr_id, user_id=user["sub"])


@router.post("/generate-qr/", response_model=QrCodeResponse)
def generate_qr_compat(
    url: HttpUrl,
    user: dict[str, Any] = Depends(get_current_user),
):
    """
    Legacy endpoint used by qrify-web (query param ?url=...).
    Same behavior as POST /qr-codes — kept so we don't break the UI.
    """
    try:
        return create_qr_code(str(url), user_id=user["sub"])
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="QR code generation failed") from exc
