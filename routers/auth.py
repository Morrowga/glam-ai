"""
routers/auth.py
────────────────
Mount in main.py with:
    from routers.auth import router as auth_router
    app.include_router(auth_router, prefix="/auth", tags=["auth"])

Endpoints:
    POST   /auth/register
    POST   /auth/verify-email          (token as query param)
    POST   /auth/login
    GET    /auth/me
    POST   /auth/resend-verification   (optional convenience)
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import get_db, User, EmailVerificationToken
from engine.auth_utils import (
    hash_password,
    verify_password,
    create_access_token,
    generate_verification_token,
)
from engine.auth_email import send_verification_email
from engine.auth_deps import get_current_user
from engine.credits import create_free_subscription,get_credit_balance

router = APIRouter()

VERIFICATION_TOKEN_EXPIRE_HOURS = 24


# ── Schemas ───────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email:        EmailStr
    password:     str
    display_name: str | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"


class UserResponse(BaseModel):
    id:                str
    email:             str
    display_name:      str | None
    is_verified:       bool
    created_at:        datetime
    plan_type:         str
    credits_remaining: int
    payg_credits:      int
    total_available:   int


# ── Helpers ───────────────────────────────────────────────────────────────────

def _token_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=VERIFICATION_TOKEN_EXPIRE_HOURS)


async def _create_and_send_verification(user: User, db: AsyncSession, bg: BackgroundTasks):
    token_str = generate_verification_token()
    vt = EmailVerificationToken(
        user_id    = user.id,
        token      = token_str,
        expires_at = _token_expiry(),
    )
    db.add(vt)
    await db.commit()
    # Send email in background so the HTTP response is instant
    bg.add_task(send_verification_email, user.email, token_str)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    req: RegisterRequest,
    bg:  BackgroundTasks,
    db:  AsyncSession = Depends(get_db),
):
    # Duplicate email check
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email        = req.email,
        password_hash = hash_password(req.password),
        display_name = req.display_name,
        is_verified  = False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    await create_free_subscription(user.id, db)
    await _create_and_send_verification(user, db, bg)

    return {
        "message": "Account created. Please check your email to verify your account.",
        "user_id": user.id,
    }


@router.post("/verify-email")
async def verify_email(
    token: str = Query(..., description="Verification token from email link"),
    db:    AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token == token,
            EmailVerificationToken.used  == False,
        )
    )
    vt = result.scalar_one_or_none()

    if not vt:
        raise HTTPException(status_code=400, detail="Invalid or already-used verification token")

    # Check expiry
    now = datetime.now(timezone.utc)
    expires = vt.expires_at
    # Make timezone-aware if stored as naive UTC
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

    if now > expires:
        raise HTTPException(status_code=400, detail="Verification token expired. Request a new one.")

    # Mark verified
    vt.used = True
    user_result = await db.execute(select(User).where(User.id == vt.user_id))
    user = user_result.scalar_one_or_none()
    if user:
        user.is_verified = True

    await db.commit()
    return {"message": "Email verified successfully. You can now log in."}


@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    db:  AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == req.email, User.is_active == True))
    user = result.scalar_one_or_none()

    # Same error message for wrong email OR wrong password — avoids user enumeration
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Email not verified. Please check your inbox or request a new verification email.",
        )

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    token = create_access_token(user_id=user.id, email=user.email)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def me(
    user: User         = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    balance = await get_credit_balance(user.id, db)
    return UserResponse(
        id                = user.id,
        email             = user.email,
        display_name      = user.display_name,
        is_verified       = user.is_verified,
        created_at        = user.created_at,
        plan_type         = balance["plan_type"],
        credits_remaining = balance["credits_remaining"],
        payg_credits      = balance["payg_credits"],
        total_available   = balance["total_available"],
    )


@router.post("/resend-verification")
async def resend_verification(
    req: LoginRequest,
    bg:  BackgroundTasks,
    db:  AsyncSession = Depends(get_db),
):
    """
    Lets a user request a fresh verification email.
    Requires email + password to prevent abuse.
    """
    result = await db.execute(select(User).where(User.email == req.email, User.is_active == True))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if user.is_verified:
        return {"message": "Email already verified."}

    await _create_and_send_verification(user, db, bg)
    return {"message": "Verification email resent. Please check your inbox."}