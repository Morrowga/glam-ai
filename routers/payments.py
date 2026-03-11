"""
routers/payments.py
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import get_db, Plan, UserSubscription, PurchaseRecord
from engine.auth_deps import require_verified_user
from engine.credits import get_credit_balance, grant_subscription_credits, grant_payg_credits
from db.models import User

router = APIRouter()


class SubscribeRequest(BaseModel):
    plan_type: str
    currency:  str = "USD"  # USD | MMK

    @field_validator("plan_type")
    @classmethod
    def validate_plan(cls, v: str) -> str:
        if v not in ("basic", "glam"):
            raise ValueError("plan_type must be 'basic' or 'glam'")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        if v not in ("USD", "MMK"):
            return "USD"
        return v


class TopupRequest(BaseModel):
    credits:  int
    currency: str = "USD"  # USD | MMK

    @field_validator("credits")
    @classmethod
    def validate_credits(cls, v: int) -> int:
        if v < 5 or v > 200:
            raise ValueError("credits must be between 5 and 200")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        if v not in ("USD", "MMK"):
            return "USD"
        return v


# ── GET /plans ────────────────────────────────────────────────────────────────

@router.get("/plans")
async def get_plans(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Plan).where(Plan.is_active == True))
    plans  = result.scalars().all()
    return [
        {
            "id":                    p.id,
            "name":                  p.name,
            "plan_type":             p.plan_type,
            "credits":               p.credits,
            "price_usd":             p.price_usd,
            "price_mmk":             p.price_mmk,
            "is_subscription":       p.is_subscription,
            "min_credits":           p.min_credits,
            "max_credits":           p.max_credits,
            "price_per_credit":      p.price_per_credit,
            "price_per_credit_mmk":  p.price_per_credit_mmk,
        }
        for p in plans
    ]


# ── GET /my-plan ──────────────────────────────────────────────────────────────

@router.get("/my-plan")
async def my_plan(
    user: User         = Depends(require_verified_user),
    db:   AsyncSession = Depends(get_db),
):
    balance = await get_credit_balance(user.id, db)
    return {"user_id": user.id, "email": user.email, **balance}


# ── POST /subscribe ───────────────────────────────────────────────────────────

@router.post("/subscribe")
async def subscribe(
    req:  SubscribeRequest,
    user: User           = Depends(require_verified_user),
    db:   AsyncSession   = Depends(get_db),
):
    result = await db.execute(select(UserSubscription).where(UserSubscription.user_id == user.id))
    sub = result.scalar_one_or_none()

    if sub:
        if sub.plan_type in ("basic", "glam") and sub.credits_remaining > 0:
            raise HTTPException(
                status_code=409,
                detail={
                    "code":              "credits_remaining",
                    "message":           f"You still have {sub.credits_remaining} credits on your {sub.plan_type} plan.",
                    "credits_remaining": sub.credits_remaining,
                    "current_plan":      sub.plan_type,
                }
            )

    result = await db.execute(select(Plan).where(Plan.plan_type == req.plan_type))
    plan   = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(404, "Plan not found")

    if req.currency == "MMK":
        amount_local = plan.price_mmk or plan.price_usd
    else:
        amount_local = plan.price_usd

    sub = await grant_subscription_credits(
        user_id=user.id, plan_type=req.plan_type, credits=plan.credits, db=db
    )

    db.add(PurchaseRecord(
        user_id           = user.id,
        plan_type         = req.plan_type,
        credits_purchased = plan.credits,
        amount_usd        = plan.price_usd,
        amount_local      = amount_local,
        currency          = req.currency,
        payment_intent_id = None,
        status            = "completed",
    ))
    await db.commit()

    return {
        "message":            f"{plan.name} plan activated.",
        "plan_type":          sub.plan_type,
        "credits_remaining":  sub.credits_remaining,
        "current_period_end": sub.current_period_end,
    }


# ── POST /topup ───────────────────────────────────────────────────────────────

@router.post("/topup")
async def topup(
    req:  TopupRequest,
    user: User         = Depends(require_verified_user),
    db:   AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Plan).where(Plan.plan_type == "payg"))
    plan   = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(404, "PAYG plan not found")

    amount_usd = round(req.credits * plan.price_per_credit, 2)

    if req.currency == "MMK":
        per          = plan.price_per_credit_mmk or plan.price_per_credit
        amount_local = round(req.credits * per, 2)
    else:
        amount_local = amount_usd

    sub = await grant_payg_credits(user_id=user.id, credits=req.credits, db=db)

    db.add(PurchaseRecord(
        user_id           = user.id,
        plan_type         = "payg",
        credits_purchased = req.credits,
        amount_usd        = amount_usd,
        amount_local      = amount_local,
        currency          = req.currency,
        payment_intent_id = None,
        status            = "completed",
    ))
    await db.commit()

    return {
        "message":         f"{req.credits} credits added.",
        "payg_credits":    sub.payg_credits,
        "payg_expires_at": sub.payg_expires_at,
        "amount_charged":  amount_local,
    }


# ── GET /history ──────────────────────────────────────────────────────────────

@router.get("/history")
async def purchase_history(
    user: User         = Depends(require_verified_user),
    db:   AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PurchaseRecord)
        .where(PurchaseRecord.user_id == user.id)
        .order_by(PurchaseRecord.created_at.desc())
    )
    records = result.scalars().all()
    return [
        {
            "id":                r.id,
            "plan_type":         r.plan_type,
            "credits_purchased": r.credits_purchased,
            "amount_usd":        r.amount_usd,
            "amount_local":      r.amount_local,
            "currency":          r.currency,
            "status":            r.status,
            "created_at":        r.created_at,
        }
        for r in records
    ]