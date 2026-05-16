"""
seeds/seed_from_csv.py
──────────────────────
Bulk seed brands, products, and shades from CSV files.

Usage:
    venv/bin/python seeds/seed_from_csv.py              # seeds all 3 files
    venv/bin/python seeds/seed_from_csv.py --file brands
    venv/bin/python seeds/seed_from_csv.py --file products
    venv/bin/python seeds/seed_from_csv.py --file shades

CSV files must be in: seeds/csv/
    seeds/csv/brands.csv
    seeds/csv/products.csv
    seeds/csv/shades.csv
"""

import asyncio, sys, os, argparse, csv
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from sqlalchemy import select
from db.models import init_db, AsyncSessionLocal, Brand, Category, Product, Shade

CSV_DIR = Path(__file__).parent / "csv"


# ── Helpers ───────────────────────────────────────────────────────────────────

def read_csv(filename: str) -> list[dict]:
    path = CSV_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def clean(row: dict) -> dict:
    """Strip whitespace from all values."""
    return {k: v.strip() for k, v in row.items()}


# ── Seed brands ───────────────────────────────────────────────────────────────

async def seed_brands():
    rows = read_csv("brands.csv")
    async with AsyncSessionLocal() as db:
        added = 0
        for r in rows:
            r = clean(r)
            result = await db.execute(select(Brand).where(Brand.slug == r["slug"]))
            brand = result.scalar_one_or_none()
            if not brand:
                db.add(Brand(
                    name      = r["name"],
                    slug      = r["slug"],
                    country   = r.get("country", ""),
                    tier      = r.get("tier", ""),
                    is_active = r.get("active", "true").lower() != "false",
                ))
                print(f"  + Brand: {r['name']}")
                added += 1
            else:
                # Update fields if changed
                brand.name    = r["name"]
                brand.country = r.get("country", brand.country)
                brand.tier    = r.get("tier", brand.tier)
                print(f"  ~ Brand exists: {r['name']}")
        await db.commit()
        print(f"Brands: {added} added, {len(rows) - added} already existed\n")


# ── Seed products ─────────────────────────────────────────────────────────────

async def seed_products():
    rows = read_csv("products.csv")
    async with AsyncSessionLocal() as db:
        added = 0
        for r in rows:
            r = clean(r)

            # Look up brand
            brand_result = await db.execute(select(Brand).where(Brand.slug == r["brand_slug"]))
            brand = brand_result.scalar_one_or_none()
            if not brand:
                print(f"  ✗ Brand not found: '{r['brand_slug']}' — skipping {r['slug']}")
                continue

            # Look up category
            cat_result = await db.execute(select(Category).where(Category.slug == r["category_slug"]))
            cat = cat_result.scalar_one_or_none()
            if not cat:
                print(f"  ✗ Category not found: '{r['category_slug']}' — skipping {r['slug']}")
                continue

            result = await db.execute(select(Product).where(Product.slug == r["slug"]))
            product = result.scalar_one_or_none()
            if not product:
                db.add(Product(
                    name        = r["name"],
                    slug        = r["slug"],
                    brand_id    = brand.id,
                    category_id = cat.id,
                    is_active   = r.get("active", "true").lower() != "false",
                ))
                print(f"  + Product: {r['name']} [{r['brand_slug']} / {r['category_slug']}]")
                added += 1
            else:
                product.name      = r["name"]
                product.is_active = r.get("active", "true").lower() != "false"
                print(f"  ~ Product exists: {r['name']}")
        await db.commit()
        print(f"Products: {added} added, {len(rows) - added} already existed\n")


# ── Seed shades ───────────────────────────────────────────────────────────────

async def seed_shades():
    rows = read_csv("shades.csv")
    async with AsyncSessionLocal() as db:
        added = 0
        for r in rows:
            r = clean(r)

            # Look up product
            prod_result = await db.execute(select(Product).where(Product.slug == r["product_slug"]))
            product = prod_result.scalar_one_or_none()
            if not product:
                print(f"  ✗ Product not found: '{r['product_slug']}' — skipping shade '{r['name']}'")
                continue

            result = await db.execute(
                select(Shade).where(
                    Shade.product_id == product.id,
                    Shade.name       == r["name"],
                )
            )
            shade = result.scalar_one_or_none()
            if not shade:
                db.add(Shade(
                    product_id        = product.id,
                    name              = r["name"],
                    hex_color         = r.get("hex", ""),
                    finish_type       = r.get("finish", ""),
                    coverage          = r.get("coverage", ""),
                    prompt_supplement = r.get("description", ""),
                    is_active         = r.get("active", "true").lower() != "false",
                ))
                print(f"  + Shade: {r['name']} [{r['product_slug']}]")
                added += 1
            else:
                # Update if changed
                shade.hex_color         = r.get("hex", shade.hex_color)
                shade.finish_type       = r.get("finish", shade.finish_type)
                shade.coverage          = r.get("coverage", shade.coverage)
                shade.prompt_supplement = r.get("description", shade.prompt_supplement)
                shade.is_active         = r.get("active", "true").lower() != "false"
                print(f"  ~ Shade exists: {r['name']}")
        await db.commit()
        print(f"Shades: {added} added, {len(rows) - added} already existed\n")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main(file: str = None):
    await init_db()
    CSV_DIR.mkdir(parents=True, exist_ok=True)

    if file == "brands" or file is None:
        print("── Seeding brands ──────────────────────")
        await seed_brands()

    if file == "products" or file is None:
        print("── Seeding products ────────────────────")
        await seed_products()

    if file == "shades" or file is None:
        print("── Seeding shades ──────────────────────")
        await seed_shades()

    print("Done!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", choices=["brands", "products", "shades"], default=None,
                        help="Which CSV to seed. Omit to seed all.")
    args = parser.parse_args()
    asyncio.run(main(args.file))