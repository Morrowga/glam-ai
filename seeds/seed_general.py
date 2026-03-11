"""
GlamAI — Master Seeder
Location: seeds/seed_general.py
Run: python seeds/seed_general.py

Disabled categories (pending skin tone classifier):
  - foundation, concealer → needs skin tone matching
  - contour               → too subtle on deep skin
"""

import asyncio, sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from db.models import init_db, AsyncSessionLocal, Category
from seeds.brands.seed_nyx import seed as seed_nyx
from seeds.seed_plans import seed_plans

CATEGORIES = [
    # ── LIPS ──────────────────────────────────────────────────────
    {"name": "Lipstick",    "slug": "lipstick",    "application_zone": "lips"},
    {"name": "Lip Gloss",   "slug": "lip-gloss",   "application_zone": "lips"},
    {"name": "Lip Liner",   "slug": "lip-liner",   "application_zone": "lips"},

    # ── EYES ──────────────────────────────────────────────────────
    {"name": "Eyeshadow",   "slug": "eyeshadow",   "application_zone": "eyes"},
    {"name": "Eyeliner",    "slug": "eyeliner",    "application_zone": "eyes"},
    {"name": "Mascara",     "slug": "mascara",     "application_zone": "eyes"},
    {"name": "Eyebrow",     "slug": "eyebrow",     "application_zone": "eyes"},

    # ── CHEEKS ────────────────────────────────────────────────────
    {"name": "Blush",       "slug": "blush",       "application_zone": "cheeks"},
    {"name": "Bronzer",     "slug": "bronzer",     "application_zone": "cheeks"},
    {"name": "Highlighter", "slug": "highlighter", "application_zone": "cheeks"},

    # ── DISABLED (re-enable after skin tone classifier) ───────────
    # {"name": "Foundation",  "slug": "foundation",  "application_zone": "face"},
    # {"name": "Concealer",   "slug": "concealer",   "application_zone": "face"},
    # {"name": "Contour",     "slug": "contour",     "application_zone": "cheeks"},
]


async def seed_categories():
    async with AsyncSessionLocal() as db:
        for c in CATEGORIES:
            result = await db.execute(select(Category).where(Category.slug == c["slug"]))
            cat = result.scalar_one_or_none()
            if not cat:
                cat = Category(name=c["name"], slug=c["slug"],
                               application_zone=c["application_zone"])
                db.add(cat)
                print(f"  + Category: {cat.name}")
            else:
                print(f"  ~ Category exists: {cat.name}")
        await db.commit()
        print(f"Categories seeded: {len(CATEGORIES)}")


async def seed_all():
    print("=" * 50)
    print("GlamAI Master Seeder")
    print("=" * 50)

    await init_db()
    
    print("\n[3/3] Seeding plans...")
    await seed_plans()
    
    print("\n[1/2] Seeding categories...")
    await seed_categories()

    print("\n[2/2] Seeding NYX Professional Makeup...")
    await seed_nyx()

    print("\n" + "=" * 50)
    print("All seeds complete!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(seed_all())