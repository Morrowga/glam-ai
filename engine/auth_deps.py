"""
engine/auth_deps.py
────────────────────
FastAPI dependency: extracts + validates JWT from Authorization header.
Usage:
    from engine.auth_deps import get_current_user, require_verified_user, verify_public_token
    
    @app.get("/me")
    async def me(user = Depends(get_current_user)):
        ...

    @app.post("/generate")
    async def generate(user = Depends(require_verified_user)):
        ...

    @app.get("/brands")
    async def brands(_ = Depends(verify_public_token)):
        ...
"""

import os
from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError

from db.models import get_db, User
from engine.auth_utils import decode_access_token

_bearer = HTTPBearer()
_PUBLIC_TOKEN = os.getenv("PUBLIC_API_TOKEN")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validates Bearer JWT and returns the User row.
    Raises 401 on any token problem.
    Raises 401 if user no longer exists or is deactivated.
    """
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")
        if not user_id:
            raise JWTError("no sub")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def require_verified_user(user: User = Depends(get_current_user)) -> User:
    """
    Same as get_current_user but also requires email to be verified.
    Use on /generate, /generate-combo, and any paid feature.
    """
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please check your inbox.",
        )
    return user


async def verify_public_token(
    x_public_token: str = Header(..., alias="x-public-token"),
) -> None:
    """
    Lightweight protection for public-facing endpoints (brands, products, shades, upload).
    Not a user auth check — just prevents random scraping.

    Frontend sends:  x-public-token: <PUBLIC_API_TOKEN from .env>

    Add to backend .env:
        PUBLIC_API_TOKEN=some-long-random-string-here  (openssl rand -hex 32)

    Add to frontend .env.local:
        NEXT_PUBLIC_API_TOKEN=same-value
    """
    if not _PUBLIC_TOKEN:
        # Env var not set — skip check in dev
        return
    if x_public_token != _PUBLIC_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid public token",
        )