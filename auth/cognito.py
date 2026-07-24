"""
Verify Cognito JWTs (ID or access token) using the pool's JWKS.

Env (from Secrets Manager → ESO → qrify-cognito):
  COGNITO_REGION, COGNITO_USER_POOL_ID, COGNITO_CLIENT_ID, COGNITO_ISSUER
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

_bearer = HTTPBearer(auto_error=False)


@lru_cache
def _settings() -> dict[str, str]:
    region = os.getenv("COGNITO_REGION", "us-east-2")
    pool_id = os.getenv("COGNITO_USER_POOL_ID", "")
    client_id = os.getenv("COGNITO_CLIENT_ID", "")
    issuer = os.getenv("COGNITO_ISSUER") or (
        f"https://cognito-idp.{region}.amazonaws.com/{pool_id}" if pool_id else ""
    )
    return {
        "region": region,
        "pool_id": pool_id,
        "client_id": client_id,
        "issuer": issuer,
        "jwks_url": f"{issuer}/.well-known/jwks.json" if issuer else "",
    }


@lru_cache
def _jwks_client() -> PyJWKClient:
    url = _settings()["jwks_url"]
    if not url:
        raise RuntimeError("Cognito is not configured (missing COGNITO_USER_POOL_ID / ISSUER)")
    return PyJWKClient(url)


def verify_token(token: str) -> dict[str, Any]:
    """Validate signature + issuer + audience/client, return claims."""
    cfg = _settings()
    if not cfg["issuer"] or not cfg["client_id"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth is not configured on this API",
        )

    try:
        signing_key = _jwks_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=cfg["issuer"],
            options={
                "verify_aud": False,  # ID token has aud; access token uses client_id
                "require": ["exp", "iss", "sub"],
            },
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    token_use = claims.get("token_use")
    if token_use == "id":
        if claims.get("aud") != cfg["client_id"]:
            raise HTTPException(status_code=401, detail="Token audience mismatch")
    elif token_use == "access":
        if claims.get("client_id") != cfg["client_id"]:
            raise HTTPException(status_code=401, detail="Token client mismatch")
    else:
        # Still accept if aud or client_id matches (defensive).
        if claims.get("aud") != cfg["client_id"] and claims.get("client_id") != cfg["client_id"]:
            raise HTTPException(status_code=401, detail="Token not issued for this app")

    return claims


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict[str, Any]:
    """FastAPI dependency: requires Authorization: Bearer <cognito jwt>."""
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    claims = verify_token(creds.credentials)
    return {
        "sub": claims["sub"],
        "email": claims.get("email"),
        "username": claims.get("username") or claims.get("cognito:username"),
        "claims": claims,
    }
