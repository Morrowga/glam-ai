"""
engine/auth_utils.py
────────────────────
JWT creation / verification  +  bcrypt password helpers.
No side-effects on import — safe to use anywhere.
"""

import os, secrets
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from jose import JWTError, jwt
from passlib.context import CryptContext

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
JWT_SECRET    = os.getenv("JWT_SECRET", "CHANGE_ME_IN_PRODUCTION")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 * 7))  # 7 days default

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12, truncate_error=False)


# ── Password ──────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(user_id: str, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub":   user_id,
        "email": email,
        "exp":   expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Returns payload dict on success.
    Raises JWTError (from python-jose) on invalid / expired token.
    Caller is responsible for catching and converting to HTTP 401.
    """
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


# ── Email verification token ──────────────────────────────────────────────────

def generate_verification_token() -> str:
    """
    URL-safe 48-byte token → 64 hex chars.
    Stored in DB, sent as query param in verification email.
    """
    return secrets.token_hex(32)