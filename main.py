from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from db.models import init_db, get_db, Brand, Category, Product, Shade, GenerationJob, ReferenceImage
from engine.prompt_engine import build_prompt, build_combined_prompt, sort_shade_ids_by_zone_order, CATEGORY_ZONE
from engine.face_validator import validate_photo
from contextlib import asynccontextmanager
import shutil, uuid
from pathlib import Path
from routers.auth import router as auth_router
from routers.payments import router as payments_router

UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
Path("./results").mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="GlamAI API", lifespan=lifespan)
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/results", StaticFiles(directory="results"), name="results")
app.include_router(payments_router, prefix="/payments", tags=["payments"])

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
    # Save file first
    file_id   = str(uuid.uuid4())[:8]
    ext       = file.filename.split(".")[-1]
    save_path = UPLOAD_DIR / f"{file_id}.{ext}"

    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Validate photo
    validation = await validate_photo(str(save_path.resolve()))

    if not validation["pass"]:
        # Delete rejected photo — no point keeping it
        save_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=422,
            detail={
                "message":    validation["reject_reason"],
                "validation": validation["details"],
            }
        )

    return {
        "upload_path": str(save_path.resolve()),
        "file_id":     file_id,
        "validation":  validation["details"],
    }


# ── SINGLE GENERATION ─────────────────────────────────────────────

class GenerateRequest(BaseModel):
    shade_id:           str
    upload_path:        str
    detected_skin_tone: str = "medium"


@app.post("/generate")
async def generate(req: GenerateRequest, db: AsyncSession = Depends(get_db)):
    row = await db.execute(
        select(Shade, Product, Brand, Category)
        .join(Product,  Shade.product_id    == Product.id)
        .join(Brand,    Product.brand_id    == Brand.id)
        .join(Category, Product.category_id == Category.id)
        .where(Shade.id == req.shade_id)
    )
    row = row.first()
    if not row:
        raise HTTPException(404, "Shade not found")

    shade, product, brand, category = row

    prompt = build_prompt(
        category_slug      = category.slug,
        product_data       = {
            "category_slug": category.slug,
            "brand_name":    brand.name,
            "product_name":  product.name,
            "shade_name":    shade.name,
        },
        detected_skin_tone = req.detected_skin_tone,
    )

    job = GenerationJob(
        session_id  = str(uuid.uuid4()),
        chain_order = 0,
        shade_id    = shade.id,
        upload_path = req.upload_path,
        input_path  = req.upload_path,
        prompt_used = prompt,
        status      = "pending",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    return {
        "job_id":  job.id,
        "status":  "pending",
        "message": "Job queued. Poll GET /jobs/{job_id} for result.",
    }


# ── JOBS ──────────────────────────────────────────────────────────

@app.get("/jobs/{job_id}")
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GenerationJob).where(GenerationJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")
    return {
        "job_id":          job.id,
        "status":          job.status,
        "result_path":     job.result_path if job.status == "complete" else None,
        "generation_time": job.generation_time,
        "error":           job.error_message if job.status == "failed" else None,
        "session_id":      job.session_id,
        "chain_order":     job.chain_order,
        "completed_at":    job.completed_at,
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
            .join(Product,  Shade.product_id    == Product.id)
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

    # ── 3. Sort by application order ──────────────────────────────
    category_slugs = [row[3].slug for row in shade_rows]
    ordered_slugs  = sort_shade_ids_by_zone_order(category_slugs)
    slug_to_row    = {row[3].slug: row for row in shade_rows}
    ordered_rows   = [slug_to_row[slug] for slug in ordered_slugs if slug in slug_to_row]

    if not ordered_rows:
        raise HTTPException(400, "Could not order shades — check category slugs.")

    # ── 4. Build combined prompt ──────────────────────────────────
    prompt_steps = []
    for shade, product, brand, category in ordered_rows:
        prompt_steps.append({
            "category_slug": category.slug,
            "product_data":  {
                "brand_name": brand.name,
                "shade_name": shade.name,
            },
        })

    combined_prompt = build_combined_prompt(
        steps              = prompt_steps,
        detected_skin_tone = req.detected_skin_tone,
    )

    # ── 5. Create job ─────────────────────────────────────────────
    session_id    = str(uuid.uuid4())
    primary_shade = ordered_rows[0][0]

    job = GenerationJob(
        session_id  = session_id,
        chain_order = 0,
        shade_id    = primary_shade.id,
        upload_path = req.upload_path,
        input_path  = req.upload_path,
        prompt_used = combined_prompt,
        status      = "pending",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    return {
        "job_id":         job.id,
        "status":         "pending",
        "message":        "Job queued. Poll GET /jobs/{job_id} for result.",
        "zone":           list(zones)[0],
        "session_id":     session_id,
        "shades_applied": [
            {"category": cat.slug, "shade": shade.name, "product": product.name}
            for shade, product, brand, cat in ordered_rows
        ],
    }