"""
GlamAI Reference Image Seeder
==============================
You provide the images. This script seeds them into the DB.

Folder structure convention:
  references/
    {brand_slug}/
      {product_slug}/
        {shade_slug}/
          swatch.jpg       <- product color swatch
          on_skin.jpg      <- swatch on skin
          model.jpg        <- person wearing it
          (any image files)<- all get seeded

Shade slug: lowercase, spaces to hyphens
  "Siren" -> "siren"
  "Nude Pink" -> "nude-pink"

Run:
  python brands/seed_references.py
  python brands/seed_references.py --brand nyx --product nyx-matte-lipstick
"""

import asyncio, sys, os, argparse
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from sqlalchemy import select
from db.models import init_db, AsyncSessionLocal, Brand, Product, Shade, ReferenceImage

REFERENCES_DIR = Path("./references")
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def shade_to_slug(name: str) -> str:
    return name.lower().strip().replace(" ", "-").replace("'", "").replace("/", "-")


async def seed(brand_slug: str = None, product_slug: str = None):
    await init_db()

    async with AsyncSessionLocal() as db:
        total = 0

        if brand_slug:
            brand_dirs = [REFERENCES_DIR / brand_slug]
        else:
            brand_dirs = [d for d in REFERENCES_DIR.iterdir() if d.is_dir()]

        for brand_dir in brand_dirs:
            if not brand_dir.exists():
                print(f"Warning: Brand folder not found: {brand_dir}")
                continue

            result = await db.execute(select(Brand).where(Brand.slug == brand_dir.name))
            brand = result.scalar_one_or_none()
            if not brand:
                print(f"Warning: Brand '{brand_dir.name}' not in DB, skipping")
                continue

            print(f"\nBrand: {brand.name}")

            if product_slug:
                product_dirs = [brand_dir / product_slug]
            else:
                product_dirs = [d for d in brand_dir.iterdir() if d.is_dir()]

            for product_dir in product_dirs:
                if not product_dir.exists():
                    print(f"  Warning: Product folder not found: {product_dir}")
                    continue

                result = await db.execute(select(Product).where(Product.slug == product_dir.name))
                product = result.scalar_one_or_none()
                if not product:
                    print(f"  Warning: Product '{product_dir.name}' not in DB, skipping")
                    continue

                print(f"  Product: {product.name}")

                result = await db.execute(select(Shade).where(Shade.product_id == product.id))
                shades = result.scalars().all()
                shade_map = {shade_to_slug(s.name): s for s in shades}

                for shade_dir in sorted(product_dir.iterdir()):
                    if not shade_dir.is_dir():
                        continue

                    shade = shade_map.get(shade_dir.name)
                    if not shade:
                        print(f"    Warning: Shade '{shade_dir.name}' not in DB")
                        print(f"    Available slugs: {list(shade_map.keys())}")
                        continue

                    print(f"    Shade: {shade.name}")

                    image_files = [
                        f for f in sorted(shade_dir.iterdir())
                        if f.suffix.lower() in SUPPORTED_EXTENSIONS
                    ]

                    if not image_files:
                        print(f"      Warning: No images in {shade_dir}")
                        continue

                    for img_path in image_files:
                        stem = img_path.stem.lower()

                        # Source type from filename
                        if "swatch" in stem:
                            source = "swatch"
                        elif "skin" in stem:
                            source = "on_skin"
                        elif "model" in stem:
                            source = "model"
                        else:
                            source = stem

                        # Skin tone from filename
                        skin_tone = None
                        for tone in ["fair", "light", "medium", "tan", "deep", "rich"]:
                            if tone in stem:
                                skin_tone = tone
                                break

                        # Skip duplicates
                        result = await db.execute(
                            select(ReferenceImage).where(
                                ReferenceImage.shade_id == shade.id,
                                ReferenceImage.image_path == str(img_path),
                            )
                        )
                        if result.scalar_one_or_none():
                            print(f"      Already seeded: {img_path.name}")
                            continue

                        ref = ReferenceImage(
                            shade_id=shade.id,
                            skin_tone=skin_tone,
                            image_path=str(img_path),
                            source=source,
                        )
                        db.add(ref)
                        total += 1
                        print(f"      + {img_path.name} [{source}] skin_tone={skin_tone or 'any'}")

                    await db.commit()

        print(f"\nDone! Seeded {total} reference images.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--brand",   default=None, help="Brand slug e.g. nyx")
    parser.add_argument("--product", default=None, help="Product slug e.g. nyx-matte-lipstick")
    args = parser.parse_args()
    asyncio.run(seed(args.brand, args.product))