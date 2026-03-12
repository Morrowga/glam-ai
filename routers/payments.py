"""
routers/payments.py

Stripe flow (International / USD):
  1. POST /payments/stripe/create-checkout  → returns { checkout_url, session_id }
  2. User pays on Stripe-hosted page
  3. Stripe webhook → POST /payments/stripe/webhook → grants credits
  4. Frontend polls GET /payments/stripe/session/{session_id} to confirm

Local flow (Myanmar / MMK) — unchanged:
  POST /payments/subscribe  (basic / glam)
  POST /payments/topup      (payg)
"""

import os
import stripe
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import get_db, Plan, UserSubscription, PurchaseRecord, User
from engine.auth_deps import require_verified_user
from engine.credits import (
    get_credit_balance,
    grant_subscription_credits,
    grant_payg_credits,
)

router = APIRouter()

# ── Stripe init ───────────────────────────────────────────────────────────────
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")          # sk_test_...
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")  # whsec_...
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


# ── Request models ────────────────────────────────────────────────────────────

class SubscribeRequest(BaseModel):
    plan_type: str
    currency:  str = "USD"

    @field_validator("plan_type")
    @classmethod
    def validate_plan(cls, v: str) -> str:
        if v not in ("basic", "glam"):
            raise ValueError("plan_type must be 'basic' or 'glam'")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        return v if v in ("USD", "MMK") else "USD"


class TopupRequest(BaseModel):
    credits:  int
    currency: str = "USD"

    @field_validator("credits")
    @classmethod
    def validate_credits(cls, v: int) -> int:
        if v < 5 or v > 200:
            raise ValueError("credits must be between 5 and 200")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        return v if v in ("USD", "MMK") else "USD"


class StripeCheckoutRequest(BaseModel):
    plan_type: str   # basic | glam | payg
    credits:   int = 0  # only for payg

    @field_validator("plan_type")
    @classmethod
    def validate_plan(cls, v: str) -> str:
        if v not in ("basic", "glam", "payg"):
            raise ValueError("Invalid plan_type")
        return v


# ── GET /plans ────────────────────────────────────────────────────────────────

@router.get("/plans")
async def get_plans(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Plan).where(Plan.is_active == True))
    plans  = result.scalars().all()
    return [
        {
            "id":                   p.id,
            "name":                 p.name,
            "plan_type":            p.plan_type,
            "credits":              p.credits,
            "price_usd":            p.price_usd,
            "price_mmk":            p.price_mmk,
            "is_subscription":      p.is_subscription,
            "min_credits":          p.min_credits,
            "max_credits":          p.max_credits,
            "price_per_credit":     p.price_per_credit,
            "price_per_credit_mmk": p.price_per_credit_mmk,
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


# ═══════════════════════════════════════════════════════════════════════════════
#  STRIPE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/stripe/create-checkout")
async def create_stripe_checkout(
    req:  StripeCheckoutRequest,
    user: User           = Depends(require_verified_user),
    db:   AsyncSession   = Depends(get_db),
):
    """
    Creates a Stripe Checkout Session and returns the hosted URL.
    Frontend redirects the user to checkout_url.
    Credits are granted ONLY after webhook confirmation.
    """
    if not stripe.api_key:
        raise HTTPException(500, "Stripe is not configured")

    # ── Resolve plan details ──────────────────────────────────────────────────
    plan_type = req.plan_type
    plan_q    = await db.execute(select(Plan).where(Plan.plan_type == plan_type))
    plan      = plan_q.scalar_one_or_none()
    if not plan:
        raise HTTPException(404, "Plan not found")

    # ── Check existing credits before subscription switch ─────────────────────
    if plan_type in ("basic", "glam"):
        sub_q = await db.execute(
            select(UserSubscription).where(UserSubscription.user_id == user.id)
        )
        sub = sub_q.scalar_one_or_none()
        if sub and sub.plan_type in ("basic", "glam") and sub.credits_remaining > 0:
            raise HTTPException(
                status_code=409,
                detail={
                    "code":              "credits_remaining",
                    "message":           f"You still have {sub.credits_remaining} credits on your {sub.plan_type} plan.",
                    "credits_remaining": sub.credits_remaining,
                    "current_plan":      sub.plan_type,
                },
            )

    # ── Calculate amount in cents ─────────────────────────────────────────────
    if plan_type == "payg":
        credits    = req.credits if 5 <= req.credits <= 200 else 20
        amount_usd = round(credits * (plan.price_per_credit or 0.15), 2)
    else:
        credits    = plan.credits
        amount_usd = plan.price_usd

    amount_cents = int(round(amount_usd * 100))

    # ── Build line item description ───────────────────────────────────────────
    if plan_type == "payg":
        product_name = f"GlamAI {credits} Credits (Pay As You Go)"
        description  = f"{credits} AI try-on credits · valid 60 days"
    elif plan_type == "basic":
        product_name = "GlamAI Basic Plan"
        description  = "50 credits / month · all categories unlocked"
    else:
        product_name = "GlamAI Glam Plan"
        description  = "120 credits / month · priority processing"

    # ── Metadata passed through to webhook ────────────────────────────────────
    metadata = {
        "user_id":   user.id,
        "plan_type": plan_type,
        "credits":   str(credits),
        "email":     user.email,
    }

    # ── Create Stripe Checkout Session ────────────────────────────────────────
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            customer_email=user.email,
            line_items=[
                {
                    "price_data": {
                        "currency":     "usd",
                        "unit_amount":  amount_cents,
                        "product_data": {
                            "name":        product_name,
                            "description": description,
                        },
                    },
                    "quantity": 1,
                }
            ],
            metadata=metadata,
            success_url=f"{FRONTEND_URL}/billing/payment-success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/billing/make-payment?plan={plan_type}&cancelled=1",
        )
    except stripe.error.StripeError as e:
        raise HTTPException(500, f"Stripe error: {str(e)}")

    return {
        "checkout_url": session.url,
        "session_id":   session.id,
    }


@router.get("/stripe/session/{session_id}")
async def get_stripe_session(
    session_id: str,
    user: User  = Depends(require_verified_user),
):
    """
    Frontend polls this after redirect from Stripe to confirm payment status.
    Returns payment_status so frontend can show success/failure UI.
    """
    if not stripe.api_key:
        raise HTTPException(500, "Stripe is not configured")

    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except stripe.error.StripeError as e:
        raise HTTPException(404, f"Session not found: {str(e)}")

    # Security: make sure the session belongs to this user
    if session.metadata.get("user_id") != user.id:
        raise HTTPException(403, "Session does not belong to this user")

    return {
        "session_id":     session.id,
        "payment_status": session.payment_status,  # paid | unpaid | no_payment_required
        "plan_type":      session.metadata.get("plan_type"),
        "credits":        session.metadata.get("credits"),
        "amount_total":   session.amount_total,     # in cents
    }


@router.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    db: AsyncSession      = Depends(get_db),
):
    """
    Stripe calls this after payment is confirmed.
    This is the ONLY place credits get granted for Stripe payments.

    To test locally:
        stripe listen --forward-to localhost:8087/payments/stripe/webhook
    """
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(500, "Webhook secret not configured")

    raw_body = await request.body()

    # ── Verify webhook signature ──────────────────────────────────────────────
    try:
        event = stripe.Webhook.construct_event(
            payload=raw_body,
            sig_header=stripe_signature,
            secret=STRIPE_WEBHOOK_SECRET,
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Invalid webhook signature")
    except Exception as e:
        raise HTTPException(400, f"Webhook error: {str(e)}")

    # ── Handle both checkout and direct payment intent ───────────────────────
    if event["type"] == "payment_intent.succeeded":
        intent   = event["data"]["object"]
        metadata = intent.get("metadata", {})

        user_id   = metadata.get("user_id")
        plan_type = metadata.get("plan_type")
        credits   = int(metadata.get("credits", 0))
        email     = metadata.get("email", "")

        if not user_id or not plan_type or not credits:
            return {"status": "ignored"}

        payment_intent_id = intent.get("id")
        existing = await db.execute(
            select(PurchaseRecord).where(
                PurchaseRecord.payment_intent_id == payment_intent_id
            )
        )
        if existing.scalar_one_or_none():
            return {"status": "already_processed"}

        amount_usd = round(intent.get("amount_received", 0) / 100, 2)

        try:
            if plan_type == "payg":
                await grant_payg_credits(user_id=user_id, credits=credits, db=db)
            else:
                await grant_subscription_credits(
                    user_id=user_id, plan_type=plan_type, credits=credits, db=db
                )
        except Exception as e:
            print(f"❌ Credit grant failed for user {user_id}: {e}")
            raise HTTPException(500, "Credit grant failed")

        db.add(PurchaseRecord(
            user_id           = user_id,
            plan_type         = plan_type,
            credits_purchased = credits,
            amount_usd        = amount_usd,
            amount_local      = amount_usd,
            currency          = "USD",
            payment_intent_id = payment_intent_id,
            status            = "completed",
        ))
        await db.commit()
        print(f"✅ PaymentIntent processed: {email} · {plan_type} · {credits} credits · ${amount_usd}")

    if event["type"] == "checkout.session.completed":
        session  = event["data"]["object"]
        metadata = session.get("metadata", {})

        user_id   = metadata.get("user_id")
        plan_type = metadata.get("plan_type")
        credits   = int(metadata.get("credits", 0))
        email     = metadata.get("email", "")

        if not user_id or not plan_type or not credits:
            # Malformed metadata — log and return 200 so Stripe doesn't retry
            print(f"⚠️  Webhook missing metadata: {metadata}")
            return {"status": "ignored"}

        # Check payment was actually paid
        if session.get("payment_status") != "paid":
            return {"status": "not_paid"}

        # Idempotency: skip if we already processed this session
        payment_intent_id = session.get("payment_intent") or session.get("id")
        existing = await db.execute(
            select(PurchaseRecord).where(
                PurchaseRecord.payment_intent_id == payment_intent_id
            )
        )
        if existing.scalar_one_or_none():
            print(f"ℹ️  Already processed session {payment_intent_id}")
            return {"status": "already_processed"}

        amount_cents = session.get("amount_total", 0)
        amount_usd   = round(amount_cents / 100, 2)

        # ── Grant credits ─────────────────────────────────────────────────────
        try:
            if plan_type == "payg":
                sub = await grant_payg_credits(user_id=user_id, credits=credits, db=db)
            else:
                sub = await grant_subscription_credits(
                    user_id=user_id, plan_type=plan_type, credits=credits, db=db
                )
        except Exception as e:
            print(f"❌ Credit grant failed for user {user_id}: {e}")
            raise HTTPException(500, "Credit grant failed")

        # ── Save purchase record ──────────────────────────────────────────────
        db.add(PurchaseRecord(
            user_id           = user_id,
            plan_type         = plan_type,
            credits_purchased = credits,
            amount_usd        = amount_usd,
            amount_local      = amount_usd,
            currency          = "USD",
            payment_intent_id = payment_intent_id,
            status            = "completed",
        ))
        await db.commit()

        print(f"✅ Stripe payment processed: {email} · {plan_type} · {credits} credits · ${amount_usd}")

    return {"status": "ok"}


# ═══════════════════════════════════════════════════════════════════════════════
#  LOCAL PAYMENT ENDPOINTS (MMK — unchanged)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/subscribe")
async def subscribe(
    req:  SubscribeRequest,
    user: User           = Depends(require_verified_user),
    db:   AsyncSession   = Depends(get_db),
):
    """Local MMK subscription — grants credits directly (no payment gateway)."""
    result = await db.execute(
        select(UserSubscription).where(UserSubscription.user_id == user.id)
    )
    sub = result.scalar_one_or_none()

    if sub and sub.plan_type in ("basic", "glam") and sub.credits_remaining > 0:
        raise HTTPException(
            status_code=409,
            detail={
                "code":              "credits_remaining",
                "message":           f"You still have {sub.credits_remaining} credits on your {sub.plan_type} plan.",
                "credits_remaining": sub.credits_remaining,
                "current_plan":      sub.plan_type,
            },
        )

    plan_q = await db.execute(select(Plan).where(Plan.plan_type == req.plan_type))
    plan   = plan_q.scalar_one_or_none()
    if not plan:
        raise HTTPException(404, "Plan not found")

    amount_local = plan.price_mmk or plan.price_usd

    sub = await grant_subscription_credits(
        user_id=user.id, plan_type=req.plan_type, credits=plan.credits, db=db
    )
    db.add(PurchaseRecord(
        user_id           = user.id,
        plan_type         = req.plan_type,
        credits_purchased = plan.credits,
        amount_usd        = plan.price_usd,
        amount_local      = amount_local,
        currency          = "MMK",
        payment_intent_id = None,
        status            = "pending",   # pending until manually confirmed
    ))
    await db.commit()

    return {
        "message":            f"{plan.name} plan activated.",
        "plan_type":          sub.plan_type,
        "credits_remaining":  sub.credits_remaining,
        "current_period_end": sub.current_period_end,
    }


@router.post("/topup")
async def topup(
    req:  TopupRequest,
    user: User         = Depends(require_verified_user),
    db:   AsyncSession = Depends(get_db),
):
    """Local MMK topup — grants credits directly."""
    plan_q = await db.execute(select(Plan).where(Plan.plan_type == "payg"))
    plan   = plan_q.scalar_one_or_none()
    if not plan:
        raise HTTPException(404, "PAYG plan not found")

    amount_usd = round(req.credits * plan.price_per_credit, 2)
    per        = plan.price_per_credit_mmk or plan.price_per_credit
    amount_local = round(req.credits * per, 2)

    sub = await grant_payg_credits(user_id=user.id, credits=req.credits, db=db)

    db.add(PurchaseRecord(
        user_id           = user.id,
        plan_type         = "payg",
        credits_purchased = req.credits,
        amount_usd        = amount_usd,
        amount_local      = amount_local,
        currency          = "MMK",
        payment_intent_id = None,
        status            = "pending",   # pending until manually confirmed
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


# ── POST /stripe/create-payment-intent ───────────────────────────────────────

@router.post("/stripe/create-payment-intent")
async def create_payment_intent(
    req:  StripeCheckoutRequest,
    user: User           = Depends(require_verified_user),
    db:   AsyncSession   = Depends(get_db),
):
    """
    Creates a Stripe PaymentIntent for embedded Stripe Elements UI.
    Returns { client_secret, payment_intent_id, amount_cents }
    Frontend uses client_secret with @stripe/stripe-js to render card form.
    """
    if not stripe.api_key:
        raise HTTPException(500, "Stripe is not configured")

    plan_type = req.plan_type
    plan_q    = await db.execute(select(Plan).where(Plan.plan_type == plan_type))
    plan      = plan_q.scalar_one_or_none()
    if not plan:
        raise HTTPException(404, "Plan not found")

    # Check existing credits before subscription switch
    if plan_type in ("basic", "glam"):
        sub_q = await db.execute(
            select(UserSubscription).where(UserSubscription.user_id == user.id)
        )
        sub = sub_q.scalar_one_or_none()
        if sub and sub.plan_type in ("basic", "glam") and sub.credits_remaining > 0:
            raise HTTPException(
                status_code=409,
                detail={
                    "code":              "credits_remaining",
                    "message":           f"You still have {sub.credits_remaining} credits on your {sub.plan_type} plan.",
                    "credits_remaining": sub.credits_remaining,
                    "current_plan":      sub.plan_type,
                },
            )

    if plan_type == "payg":
        credits    = req.credits if 5 <= req.credits <= 200 else 20
        amount_usd = round(credits * (plan.price_per_credit or 0.15), 2)
    else:
        credits    = plan.credits
        amount_usd = plan.price_usd

    amount_cents = int(round(amount_usd * 100))

    metadata = {
        "user_id":   user.id,
        "plan_type": plan_type,
        "credits":   str(credits),
        "email":     user.email,
    }

    try:
        intent = stripe.PaymentIntent.create(
            amount               = amount_cents,
            currency             = "usd",
            receipt_email        = user.email,
            metadata             = metadata,
            automatic_payment_methods = {"enabled": True},
        )
    except stripe.error.StripeError as e:
        raise HTTPException(500, f"Stripe error: {str(e)}")

    return {
        "client_secret":     intent.client_secret,
        "payment_intent_id": intent.id,
        "amount_cents":      amount_cents,
        "amount_usd":        amount_usd,
        "credits":           credits,
    }


# ── POST /stripe/confirm-payment ─────────────────────────────────────────────

class ConfirmPaymentRequest(BaseModel):
    payment_intent_id: str

@router.post("/stripe/confirm-payment")
async def confirm_payment(
    req:  ConfirmPaymentRequest,
    user: User           = Depends(require_verified_user),
    db:   AsyncSession   = Depends(get_db),
):
    """
    Called by frontend after stripe.confirmPayment() succeeds in embedded flow.
    Retrieves the PaymentIntent from Stripe, verifies it's paid, grants credits.
    Idempotent — safe to call multiple times.
    """
    if not stripe.api_key:
        raise HTTPException(500, "Stripe is not configured")

    try:
        intent = stripe.PaymentIntent.retrieve(req.payment_intent_id)
    except stripe.error.StripeError as e:
        raise HTTPException(400, f"Stripe error: {str(e)}")

    if intent["status"] != "succeeded":
        raise HTTPException(400, f"Payment not completed. Status: {intent['status']}")

    metadata  = intent.get("metadata", {})
    user_id   = metadata.get("user_id")
    plan_type = metadata.get("plan_type")
    credits   = int(metadata.get("credits", 0))

    # Security: make sure this payment belongs to the requesting user
    if str(user_id) != str(user.id):
        raise HTTPException(403, "Payment does not belong to this user")

    # Idempotency check
    existing = await db.execute(
        select(PurchaseRecord).where(
            PurchaseRecord.payment_intent_id == req.payment_intent_id
        )
    )
    if existing.scalar_one_or_none():
        return { "status": "already_processed", "credits": credits }

    amount_usd = round(intent.get("amount_received", 0) / 100, 2)

    try:
        if plan_type == "payg":
            await grant_payg_credits(user_id=user_id, credits=credits, db=db)
        else:
            await grant_subscription_credits(
                user_id=user_id, plan_type=plan_type, credits=credits, db=db
            )
    except Exception as e:
        raise HTTPException(500, f"Credit grant failed: {str(e)}")

    db.add(PurchaseRecord(
        user_id           = user_id,
        plan_type         = plan_type,
        credits_purchased = credits,
        amount_usd        = amount_usd,
        amount_local      = amount_usd,
        currency          = "USD",
        payment_intent_id = req.payment_intent_id,
        status            = "completed",
    ))
    await db.commit()

    return { "status": "success", "credits": credits, "plan_type": plan_type }