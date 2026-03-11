"""
engine/credits.py
──────────────────
Credit management helpers.
Used by:
  - routers/auth.py     → grant 1 free credit on registration
  - worker.py           → deduct 1 credit after successful generation
  - routers/payments.py → grant credits after purchase
"""

from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from db.models import UserSubscription


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _get_subscription(user_id: str, db: AsyncSession) -> UserSubscription:
    result = await db.execute(
        select(UserSubscription).where(UserSubscription.user_id == user_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription record not found")
    return sub


# ── Public functions ──────────────────────────────────────────────────────────

async def create_free_subscription(user_id: str, db: AsyncSession) -> UserSubscription:
    """
    Called once on registration — gives user 1 free credit.
    """
    sub = UserSubscription(
        user_id           = user_id,
        plan_type         = "free",
        credits_total     = 1,
        credits_used      = 0,
        credits_remaining = 1,
        payg_credits      = 0,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return sub


async def get_credit_balance(user_id: str, db: AsyncSession) -> dict:
    """
    Returns current credit state for a user.
    Subscription credits are checked first, then PAYG.
    """
    sub = await _get_subscription(user_id, db)

    # Check if PAYG credits are expired
    payg_available = sub.payg_credits
    if sub.payg_expires_at:
        now = datetime.now(timezone.utc)
        expires = sub.payg_expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if now > expires:
            payg_available = 0

    return {
        "plan_type":          sub.plan_type,
        "credits_remaining":  sub.credits_remaining,
        "payg_credits":       payg_available,
        "total_available":    sub.credits_remaining + payg_available,
        "current_period_end": sub.current_period_end,
        "payg_expires_at":    sub.payg_expires_at,
    }


async def check_has_credits(user_id: str, db: AsyncSession) -> bool:
    """
    Returns True if user has at least 1 credit available.
    Checks subscription credits first, then PAYG.
    """
    balance = await get_credit_balance(user_id, db)
    return balance["total_available"] > 0


async def deduct_credit(user_id: str, db: AsyncSession) -> None:
    """
    Deducts 1 credit after a successful generation.
    Subscription credits are used first, then PAYG.
    Called from worker.py after job completes.
    """
    sub = await _get_subscription(user_id, db)

    # Use subscription credits first
    if sub.credits_remaining > 0:
        sub.credits_remaining -= 1
        sub.credits_used      += 1
        await db.commit()
        return

    # Fall back to PAYG credits
    now = datetime.now(timezone.utc)
    payg_expires = sub.payg_expires_at
    if payg_expires and payg_expires.tzinfo is None:
        payg_expires = payg_expires.replace(tzinfo=timezone.utc)

    if sub.payg_credits > 0 and (payg_expires is None or now <= payg_expires):
        sub.payg_credits -= 1
        await db.commit()
        return

    # No credits available — should have been caught before job was queued
    raise HTTPException(status_code=402, detail="No credits available")


async def grant_subscription_credits(
    user_id:   str,
    plan_type: str,
    credits:   int,
    db:        AsyncSession,
) -> UserSubscription:
    """
    Called after a Basic or Glam subscription purchase.
    Resets the monthly credit pool and sets period dates.
    """
    sub = await _get_subscription(user_id, db)
    now = datetime.now(timezone.utc)

    sub.plan_type             = plan_type
    sub.credits_total         = credits
    sub.credits_used          = 0
    sub.credits_remaining     = credits
    sub.current_period_start  = now
    sub.current_period_end    = now + timedelta(days=30)

    await db.commit()
    await db.refresh(sub)
    return sub


async def grant_payg_credits(
    user_id: str,
    credits: int,
    db:      AsyncSession,
) -> UserSubscription:
    """
    Called after a Pay As You Go purchase.
    Adds credits on top of existing PAYG balance, resets 2-month expiry.
    """
    sub = await _get_subscription(user_id, db)
    now = datetime.now(timezone.utc)

    # Stack on top of existing unexpired PAYG credits
    existing_payg = sub.payg_credits
    if sub.payg_expires_at:
        expires = sub.payg_expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if now > expires:
            existing_payg = 0  # expired, don't stack

    sub.payg_credits    = existing_payg + credits
    sub.payg_expires_at = now + timedelta(days=60)  # 2 months

    await db.commit()
    await db.refresh(sub)
    return sub