"""
seeds/seed_plans.py
"""

import asyncio, sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from db.models import init_db, AsyncSessionLocal, Plan

PLANS = [
    {
        "name":                  "Free",
        "plan_type":             "free",
        "credits":               1,
        "price_usd":             0.0,
        "price_mmk":             0.0,
        "is_subscription":       False,
        "min_credits":           None,
        "max_credits":           None,
        "price_per_credit":      None,
        "price_per_credit_mmk":  None,
    },
    {
        "name":                  "Basic",
        "plan_type":             "basic",
        "credits":               50,
        "price_usd":             8.0,
        "price_mmk":             8000.0,
        "is_subscription":       True,
        "min_credits":           None,
        "max_credits":           None,
        "price_per_credit":      0.16,
        "price_per_credit_mmk":  160.0,
    },
    {
        "name":                  "Glam",
        "plan_type":             "glam",
        "credits":               120,
        "price_usd":             15.0,
        "price_mmk":             15000.0,
        "is_subscription":       True,
        "min_credits":           None,
        "max_credits":           None,
        "price_per_credit":      0.125,
        "price_per_credit_mmk":  125.0,
    },
    {
        "name":                  "Pay As You Go",
        "plan_type":             "payg",
        "credits":               0,
        "price_usd":             0.0,
        "price_mmk":             0.0,
        "is_subscription":       False,
        "min_credits":           5,
        "max_credits":           200,
        "price_per_credit":      0.18,
        "price_per_credit_mmk":  180.0,
    },
]


async def seed_plans():
    await init_db()
    async with AsyncSessionLocal() as db:
        for p in PLANS:
            result = await db.execute(select(Plan).where(Plan.plan_type == p["plan_type"]))
            existing = result.scalar_one_or_none()
            if not existing:
                plan = Plan(**p)
                db.add(plan)
                print(f"  + Plan: {p['name']}")
            else:
                for field in ("credits", "price_usd", "price_mmk",
                              "price_per_credit", "price_per_credit_mmk"):
                    setattr(existing, field, p[field])
                print(f"  ~ Plan updated: {p['name']}")
        await db.commit()
    print("Plans seeded.")


if __name__ == "__main__":
    asyncio.run(seed_plans())