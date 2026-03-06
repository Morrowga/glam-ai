from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from db.models import init_db, get_db, Brand, Category, Product, Shade, GenerationJob, ReferenceImage
from engine.prompt_engine import build_prompt, build_combined_prompt, sort_shade_ids_by_zone_order, CATEGORY_ZONE
from engine.generator import generate_with_image_edit, generate_combo
from contextlib import asynccontextmanager
from datetime import datetime
import shutil, uuid
from pathlib import Path

UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
Path("./results").mkdir(exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="GlamAI API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── BRANDS ────────────────────────────────────────────────────────

@app.get("/brands")
async def get_brands(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Brand).where(Brand.is_active == True))
    brands = result.scalars().all()
    return [{"id": b.id, "name": b.name, "slug": b.slug, "tier": b.tier, "country": b.country} for b in brands]

@app.get("/brands/{brand_slug}/categories")
async def get_brand_categories(brand_slug: str, db: AsyncSession = Depends(get_db)):
    brand = await db.execute(select(Brand).where(Brand.slug == brand_slug))
    brand = brand.scalar_one_or_none()
    if not brand:
        raise HTTPException(404, "Brand not found")
    result = await db.execute(
        select(Category).join(Product).where(Product.brand_id == brand.id).distinct()
    )
    cats = result.scalars().all()
    return [{"id": c.id, "name": c.name, "slug": c.slug, "zone": c.application_zone} for c in cats]

@app.get("/brands/{brand_slug}/{category_slug}/products")
async def get_products(brand_slug: str, category_slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Product)
        .join(Brand).join(Category)
        .where(Brand.slug == brand_slug, Category.slug == category_slug, Product.is_active == True)
    )
    products = result.scalars().all()
    return [{"id": p.id, "name": p.name, "slug": p.slug} for p in products]

@app.get("/products/{product_id}/shades")
async def get_shades(product_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Shade).where(Shade.product_id == product_id, Shade.is_active == True)
    )
    shades = result.scalars().all()
    return [{"id": s.id, "name": s.name, "hex_color": s.hex_color, "finish_type": s.finish_type, "coverage": s.coverage} for s in shades]


# ── UPLOAD ────────────────────────────────────────────────────────

@app.post("/upload")
async def upload_photo(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())[:8]
    ext = file.filename.split(".")[-1]
    save_path = UPLOAD_DIR / f"{file_id}.{ext}"
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"upload_path": str(save_path.resolve()), "file_id": file_id}


# ── SINGLE GENERATION ─────────────────────────────────────────────

class GenerateRequest(BaseModel):
    shade_id:           str
    upload_path:        str
    detected_skin_tone: str = "medium"


@app.post("/generate")
async def generate(req: GenerateRequest, db: AsyncSession = Depends(get_db)):
    row = await db.execute(
        select(Shade, Product, Brand, Category)
        .join(Product, Shade.product_id == Product.id)
        .join(Brand,   Product.brand_id == Brand.id)
        .join(Category, Product.category_id == Category.id)
        .where(Shade.id == req.shade_id)
    )
    row = row.first()
    if not row:
        raise HTTPException(404, "Shade not found")

    shade, product, brand, category = row

    refs_result = await db.execute(
        select(ReferenceImage)
        .where(ReferenceImage.shade_id == shade.id, ReferenceImage.source == "swatch")
        .limit(1)
    )
    reference_paths = [r.image_path for r in refs_result.scalars().all()]

    prompt = build_prompt(
        category_slug=category.slug,
        product_data={
            "category_slug": category.slug,
            "brand_name":    brand.name,
            "product_name":  product.name,
            "shade_name":    shade.name,
        },
        detected_skin_tone=req.detected_skin_tone,
    )

    job = GenerationJob(
        session_id  = str(uuid.uuid4()),
        chain_order = 0,
        shade_id    = shade.id,
        upload_path = req.upload_path,
        input_path  = req.upload_path,
        prompt_used = prompt,
        status      = "processing",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    try:
        result = await generate_with_image_edit(
            user_photo_path = req.upload_path,
            prompt          = prompt,
            job_id          = job.id,
            category_slug   = category.slug,
            reference_paths = reference_paths,
        )
        job.result_path     = result["result_path"]
        job.status          = "complete"
        job.generation_time = result["generation_time"]
        job.completed_at    = datetime.utcnow()

    except Exception as e:
        job.status        = "failed"
        job.error_message = str(e)
        await db.commit()
        raise HTTPException(500, f"Generation failed: {e}")

    await db.commit()

    return {
        "job_id":          job.id,
        "result_path":     job.result_path,
        "generation_time": job.generation_time,
        "references_used": result.get("references_used", 0),
        "category":        category.slug,
        "shade":           shade.name,
        "product":         product.name,
        "brand":           brand.name,
        "prompt_used":     prompt,
    }


# ── JOBS ──────────────────────────────────────────────────────────

@app.get("/jobs/{job_id}")
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GenerationJob).where(GenerationJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")
    return {
        "id":              job.id,
        "status":          job.status,
        "result_path":     job.result_path,
        "generation_time": job.generation_time,
        "error":           job.error_message,
    }


# ── COMBO GENERATION ──────────────────────────────────────────────

class GenerateComboRequest(BaseModel):
    shade_ids:          list[str]
    upload_path:        str
    detected_skin_tone: str = "medium"


@app.post("/generate-combo")
async def generate_combo_endpoint(req: GenerateComboRequest, db: AsyncSession = Depends(get_db)):

    if len(req.shade_ids) < 2:
        raise HTTPException(400, "Use /generate for a single shade. /generate-combo requires 2+ shades.")
    if len(req.shade_ids) > 4:
        raise HTTPException(400, "Maximum 4 shades per combo request.")

    # ── 1. Load all shades ────────────────────────────────────────
    shade_rows = []
    for shade_id in req.shade_ids:
        row = await db.execute(
            select(Shade, Product, Brand, Category)
            .join(Product,  Shade.product_id   == Product.id)
            .join(Brand,    Product.brand_id    == Brand.id)
            .join(Category, Product.category_id == Category.id)
            .where(Shade.id == shade_id)
        )
        row = row.first()
        if not row:
            raise HTTPException(404, f"Shade not found: {shade_id}")
        shade_rows.append(row)

    # ── 2. Validate same zone ─────────────────────────────────────
    zones = set(CATEGORY_ZONE.get(row[3].slug, "unknown") for row in shade_rows)
    if len(zones) > 1:
        raise HTTPException(400, f"All shades must be in the same zone. Got: {zones}")

    # ── 3. Sort by application order ─────────────────────────────
    category_slugs = [row[3].slug for row in shade_rows]
    ordered_slugs  = sort_shade_ids_by_zone_order(category_slugs)
    slug_to_row    = {row[3].slug: row for row in shade_rows}
    ordered_rows   = [slug_to_row[slug] for slug in ordered_slugs if slug in slug_to_row]

    if not ordered_rows:
        raise HTTPException(400, "Could not order shades — check category slugs.")

    # ── 4. Collect ref images (1 per shade, max 3 total) ─────────
    all_reference_paths = []
    for shade, product, brand, category in ordered_rows:
        if len(all_reference_paths) >= 3:
            break
        refs_result = await db.execute(
            select(ReferenceImage)
            .where(ReferenceImage.shade_id == shade.id, ReferenceImage.source == "swatch")
            .limit(1)
        )
        all_reference_paths.extend([r.image_path for r in refs_result.scalars().all()])

    # ── 5. Build combined prompt ──────────────────────────────────
    prompt_steps = []
    for shade, product, brand, category in ordered_rows:
        prompt_steps.append({
            "category_slug": category.slug,
            "product_data":  {
                "brand_name":  brand.name,
                "shade_name":  shade.name,
            },
        })

    combined_prompt = build_combined_prompt(
        steps              = prompt_steps,
        detected_skin_tone = req.detected_skin_tone,
    )

    # ── 6. Create job ─────────────────────────────────────────────
    session_id    = str(uuid.uuid4())
    primary_shade = ordered_rows[0][0]

    job = GenerationJob(
        session_id  = session_id,
        chain_order = 0,
        shade_id    = primary_shade.id,
        upload_path = req.upload_path,
        input_path  = req.upload_path,
        prompt_used = combined_prompt,
        status      = "processing",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # ── 7. Single call with refs ──────────────────────────────────
    try:
        result = await generate_combo(
            user_photo_path = req.upload_path,
            steps           = [{"combined_prompt": combined_prompt, "reference_paths": all_reference_paths}],
            job_id          = job.id,
        )
        job.result_path     = result["result_path"]
        job.status          = "complete"
        job.generation_time = result["generation_time"]
        job.completed_at    = datetime.utcnow()

    except Exception as e:
        job.status        = "failed"
        job.error_message = str(e)
        await db.commit()
        raise HTTPException(500, f"Combo generation failed: {e}")

    await db.commit()

    return {
        "job_id":          job.id,
        "session_id":      session_id,
        "zone":            list(zones)[0],
        "result_path":     job.result_path,
        "generation_time": job.generation_time,
        "references_used": result.get("references_used", 0),
        "reference_paths": all_reference_paths,
        "calls_made":      result.get("calls_made", 1),
        "prompt_used":     combined_prompt,
        "shades_applied":  [
            {"category": cat.slug, "shade": shade.name, "product": product.name}
            for shade, product, brand, cat in ordered_rows
        ],
    }