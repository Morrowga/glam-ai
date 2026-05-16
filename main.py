from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from db.models import init_db, get_db, Brand, Category, Product, Shade, GenerationJob, GenerationJobItem, ReferenceImage, User
import secrets
from engine.prompt_engine import (
    build_prompt,
    build_combined_prompt,
    build_multizone_prompt,
    sort_shade_ids_by_zone_order,
    sort_rows_by_multizone_order,
    CATEGORY_ZONE,
)
from routers.look_prep import router as look_prep_router
from engine.face_validator import validate_photo
from engine.skin_analyzer import analyze_skin_tone
from engine.auth_deps import get_current_user, verify_public_token
from engine.credits import check_has_credits, deduct_credit
from contextlib import asynccontextmanager
import shutil, uuid, os, asyncio
from pathlib import Path
from routers.auth import router as auth_router
from routers.payments import router as payments_router
from worker import process_jobs
from shared_state import cancelled_jobs

UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
Path("./results").mkdir(exist_ok=True)
Path("./media/brands").mkdir(parents=True, exist_ok=True)
Path("./media/products").mkdir(parents=True, exist_ok=True)

BASE_URL = os.getenv("BASE_URL", "http://localhost:8087")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    asyncio.create_task(process_jobs())
    print("✅ Worker started")
    yield

app = FastAPI(title="GlamAI API", lifespan=lifespan)
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/results", StaticFiles(directory="results"), name="results")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/media",   StaticFiles(directory="media"),   name="media")
app.include_router(payments_router, prefix="/payments", tags=["payments"])
app.include_router(look_prep_router, prefix="/look-prep", tags=["look-prep"])



# ── ZONE HELPER ───────────────────────────────────────────────────

def _strip_zone(zone: str) -> str:
    return zone.rstrip("s") if zone else zone


# ── BRANDS ────────────────────────────────────────────────────────

@app.get("/brands")
async def get_brands(db: AsyncSession = Depends(get_db), _: None = Depends(verify_public_token)):
    result = await db.execute(select(Brand).where(Brand.is_active == True))
    brands = result.scalars().all()
    return [
        {
            "id":      b.id,
            "name":    b.name,
            "slug":    b.slug,
            "tier":    b.tier,
            "country": b.country,
            "logo":    f"{BASE_URL}/media/brands/{b.slug}.jpg",
        }
        for b in brands
    ]


@app.get("/brands/{brand_slug}/categories")
async def get_brand_categories(brand_slug: str, db: AsyncSession = Depends(get_db), _: None = Depends(verify_public_token)):
    brand = await db.execute(select(Brand).where(Brand.slug == brand_slug))
    brand = brand.scalar_one_or_none()
    if not brand:
        raise HTTPException(404, "Brand not found")
    result = await db.execute(
        select(Category).join(Product).where(Product.brand_id == brand.id).distinct()
    )
    cats = result.scalars().all()
    return [
        {
            "id":   c.id,
            "name": c.name,
            "slug": c.slug,
            "zone": _strip_zone(c.application_zone),
        }
        for c in cats
    ]


@app.get("/brands/{brand_slug}/{category_slug}/products")
async def get_products(brand_slug: str, category_slug: str, db: AsyncSession = Depends(get_db), _: None = Depends(verify_public_token)):
    result = await db.execute(
        select(Product, Brand, Category)
        .join(Brand,    Product.brand_id    == Brand.id)
        .join(Category, Product.category_id == Category.id)
        .where(
            Brand.slug    == brand_slug,
            Category.slug == category_slug,
            Product.is_active == True,
        )
    )
    rows = result.all()
    return [
        {
            "id":         p.id,
            "name":       p.name,
            "slug":       p.slug,
            "brandId":    b.id,
            "categoryId": c.id,
            "zone":       _strip_zone(c.application_zone),
            "image":      f"{BASE_URL}/media/products/{p.slug}.jpg",
        }
        for p, b, c in rows
    ]


@app.get("/products/{product_id}/shades")
async def get_shades(product_id: str, db: AsyncSession = Depends(get_db), _: None = Depends(verify_public_token)):
    result = await db.execute(
        select(Shade).where(Shade.product_id == product_id, Shade.is_active == True)
    )
    shades = result.scalars().all()
    return [
        {
            "id":        s.id,
            "name":      s.name,
            "hex":       s.hex_color,
            "productId": s.product_id,
            "finish":    s.finish_type,
            "coverage":  s.coverage,
        }
        for s in shades
    ]


# ── UPLOAD ────────────────────────────────────────────────────────

@app.post("/upload")
async def upload_photo(file: UploadFile = File(...), _: None = Depends(verify_public_token)):
    file_id   = str(uuid.uuid4())[:8]
    ext       = file.filename.split(".")[-1]
    save_path = UPLOAD_DIR / f"{file_id}.{ext}"
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    validation = await validate_photo(str(save_path.resolve()))
    if not validation["pass"]:
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
        "skin_tone":   validation.get("skin_tone", "medium"),
        "validation":  validation["details"],
    }


# ── CHEEKS ZONE LIMIT ─────────────────────────────────────────────

def _validate_cheeks(shade_rows: list) -> None:
    cheek_rows = [r for r in shade_rows if CATEGORY_ZONE.get(r[3].slug) == "cheeks"]
    if len(cheek_rows) > 1:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Only one cheeks product allowed per generation. "
                f"You selected: {[r[3].slug for r in cheek_rows]}. "
                f"Choose either blush, bronzer, or highlighter."
            ),
        )


# ── UNIFIED GENERATE ──────────────────────────────────────────────

class GenerateItem(BaseModel):
    productId: str
    shadeId:   str

class GenerateRequest(BaseModel):
    upload_path:        str
    zone:               str
    items:              list[GenerateItem]
    detected_skin_tone: str = "medium"


@app.post("/generate")
async def generate(
    req:          GenerateRequest,
    current_user: User           = Depends(get_current_user),
    db:           AsyncSession   = Depends(get_db),
):
    has_credits = await check_has_credits(current_user.id, db)
    if not has_credits:
        raise HTTPException(402, "No credits available. Please top up to continue.")

    if not Path(req.upload_path).exists():
        raise HTTPException(422, "Upload file not found. Please upload your photo first.")

    if len(req.items) == 0:
        raise HTTPException(400, "At least one item required.")
    if len(req.items) > 8:
        raise HTTPException(400, "Maximum 8 items per request.")

    # Load all shades
    shade_rows = []
    for item in req.items:
        row = await db.execute(
            select(Shade, Product, Brand, Category)
            .join(Product,  Shade.product_id    == Product.id)
            .join(Brand,    Product.brand_id    == Brand.id)
            .join(Category, Product.category_id == Category.id)
            .where(Shade.id == item.shadeId)
        )
        row = row.first()
        if not row:
            raise HTTPException(404, f"Shade not found: {item.shadeId}")
        shade_rows.append(row)

    # Cheeks: max 1 product
    _validate_cheeks(shade_rows)

    # Detect zones
    zones        = set(CATEGORY_ZONE.get(row[3].slug, "unknown") for row in shade_rows)
    is_multizone = len(zones) > 1
    session_id   = str(uuid.uuid4())

    # Build prompt
    if is_multizone:
        ordered_rows = sort_rows_by_multizone_order(shade_rows)
        prompt       = build_multizone_prompt(
            rows               = ordered_rows,
            detected_skin_tone = req.detected_skin_tone,
        )
        zone_value = "multi"
    else:
        zone_value     = _strip_zone(list(zones)[0])
        category_slugs = [row[3].slug for row in shade_rows]
        ordered_slugs  = sort_shade_ids_by_zone_order(category_slugs)
        slug_to_row    = {row[3].slug: row for row in shade_rows}
        ordered_rows   = [slug_to_row[slug] for slug in ordered_slugs if slug in slug_to_row]

        if len(ordered_rows) == 1:
            shade, product, brand, category = ordered_rows[0]
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
        else:
            prompt_steps = []
            for shade, product, brand, category in ordered_rows:
                prompt_steps.append({
                    "category_slug": category.slug,
                    "product_data": {
                        "brand_name": brand.name,
                        "shade_name": shade.name,
                    },
                })
            prompt = build_combined_prompt(
                steps              = prompt_steps,
                detected_skin_tone = req.detected_skin_tone,
            )

    # Create job
    primary_shade = ordered_rows[0][0]
    job = GenerationJob(
        user_id     = current_user.id,
        session_id  = session_id,
        chain_order = 0,
        shade_id    = primary_shade.id,
        upload_path = req.upload_path,
        input_path  = req.upload_path,
        prompt_used = prompt,
        zone        = zone_value,
        status      = "pending",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    for shade, product, brand, category in ordered_rows:
        db.add(GenerationJobItem(
            job_id     = job.id,
            product_id = product.id,
            shade_id   = shade.id,
        ))
    await db.commit()

    return {
        "job_id":         job.id,
        "status":         "pending",
        "session_id":     session_id,
        "message":        "Job queued. Poll GET /jobs/{job_id} for result.",
        "zone":           zone_value,
        "shades_applied": [
            {
                "zone":     CATEGORY_ZONE.get(cat.slug, "unknown"),
                "category": cat.slug,
                "shade":    shade.name,
                "product":  product.name,
                "brand":    brand.name,
            }
            for shade, product, brand, cat in ordered_rows
        ],
    }


# ── JOBS ──────────────────────────────────────────────────────────

@app.get("/jobs/{job_id}")
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GenerationJob).where(GenerationJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")
    result_url = None
    if job.status == "completed" and job.result_path:
        result_url = f"{BASE_URL}/results/{Path(job.result_path).name}"
    return {
        "job_id":          job.id,
        "status":          job.status,
        "result_url":      result_url,
        "generation_time": job.generation_time,
        "error":           job.error_message if job.status == "failed" else None,
        "session_id":      job.session_id,
        "chain_order":     job.chain_order,
        "completed_at":    job.completed_at,
    }


# ── CANCEL JOB ────────────────────────────────────────────────────

@app.delete("/jobs/{job_id}")
async def cancel_job(
    job_id:       str,
    current_user: User         = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    result = await db.execute(select(GenerationJob).where(GenerationJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")
    if job.user_id != current_user.id:
        raise HTTPException(403, "Not your job")
    if job.status in ("completed", "failed", "cancelled"):
        return {"job_id": job_id, "status": job.status, "message": "Already finished"}
    job.status = "cancelled"
    await db.commit()
    cancelled_jobs.add(job_id)
    return {"job_id": job_id, "status": "cancelled"}


# ── HISTORY ───────────────────────────────────────────────────────

@app.get("/history")
async def get_history(
    current_user: User         = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
    limit:        int          = 10,
    skip:         int          = 0,
    offset:       int          = 0,   # legacy alias
):
    effective_skip = skip or offset
    result = await db.execute(
        select(GenerationJob)
        .where(
            GenerationJob.user_id == current_user.id,
            GenerationJob.status  == "completed",
        )
        .options(
            selectinload(GenerationJob.items).selectinload(GenerationJobItem.product).selectinload(Product.brand),
            selectinload(GenerationJob.items).selectinload(GenerationJobItem.shade),
        )
        .order_by(GenerationJob.created_at.desc())
        .limit(min(limit, 50))
        .offset(effective_skip)
    )
    jobs = result.scalars().all()

    history = []
    for job in jobs:
        result_url         = f"{BASE_URL}/results/{Path(job.result_path).name}" if job.result_path else None
        upload_url         = f"{BASE_URL}/uploads/{Path(job.upload_path).name}" if job.upload_path else None
        upload_path_exists = job.upload_path and Path(job.upload_path).exists()

        history.append({
            "id":            job.id,
            "createdAt":     job.created_at.isoformat() if job.created_at else None,
            "zone":          job.zone or "",
            "resultImage":   result_url,
            "originalImage": upload_url,
            "uploadPath":    job.upload_path if upload_path_exists else None,
            "cart": [
                {"productId": item.product_id, "shadeId": item.shade_id}
                for item in job.items
            ],
            "cartMeta": [
                {
                    "productId":  item.product_id,
                    "shadeName":  item.shade.name,
                    "shadeHex":   item.shade.hex_color or "#000000",
                    "brandName":  item.product.brand.name if item.product.brand else "",
                    "categoryId": item.product.category_id,
                }
                for item in job.items
            ],
        })

    return history


# ── SHARE ─────────────────────────────────────────────────────────

FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')

@app.post('/jobs/{job_id}/share')
async def create_share_link(
    job_id:       str,
    current_user: User         = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    result = await db.execute(select(GenerationJob).where(GenerationJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, 'Job not found')
    if job.user_id != current_user.id:
        raise HTTPException(403, 'Not your job')
    if job.status != 'completed' or not job.result_path:
        raise HTTPException(400, 'Job not completed yet')

    # Re-use existing token or generate new one
    if not job.share_token:
        job.share_token = secrets.token_urlsafe(32)
    job.is_shared = True
    await db.commit()
    await db.refresh(job)

    return {
        'share_url':   f'{FRONTEND_URL}/look/{job.share_token}',
        'share_token': job.share_token,
    }


@app.delete('/jobs/{job_id}/share')
async def revoke_share_link(
    job_id:       str,
    current_user: User         = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    result = await db.execute(select(GenerationJob).where(GenerationJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, 'Job not found')
    if job.user_id != current_user.id:
        raise HTTPException(403, 'Not your job')
    job.is_shared = False
    await db.commit()
    return {'message': 'Share link revoked'}


@app.get('/share/{share_token}')
async def get_shared_look(
    share_token: str,
    db:          AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GenerationJob)
        .where(
            GenerationJob.share_token == share_token,
            GenerationJob.is_shared   == True,
            GenerationJob.status      == 'completed',
        )
        .options(
            selectinload(GenerationJob.items).selectinload(GenerationJobItem.product).selectinload(Product.brand),
            selectinload(GenerationJob.items).selectinload(GenerationJobItem.shade),
            selectinload(GenerationJob.items).selectinload(GenerationJobItem.product).selectinload(Product.category),
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, 'Look not found or no longer shared')

    return {
        'share_token': share_token,
        'zone':        job.zone,
        'created_at':  job.created_at.isoformat() if job.created_at else None,
        'image_url': f'{BASE_URL}/share/{share_token}/image',
        'shades': [
            {
                'productId':  item.product_id,
                'productName': item.product.name if item.product else '',
                'brandName':  item.product.brand.name if item.product and item.product.brand else '',
                'shadeName':  item.shade.name if item.shade else '',
                'shadeHex':   item.shade.hex_color or '#000000' if item.shade else '#000000',
                'categoryId': item.product.category_id if item.product else '',
                'categoryName': item.product.category.name if item.product and item.product.category else '',
            }
            for item in job.items
        ],
    }


@app.get('/share/{share_token}/image')
async def get_shared_image(
    share_token: str,
    db:          AsyncSession = Depends(get_db),
):
    """Proxy the result image — only serves if is_shared=True."""
    from fastapi.responses import FileResponse
    result = await db.execute(
        select(GenerationJob)
        .where(
            GenerationJob.share_token == share_token,
            GenerationJob.is_shared   == True,
            GenerationJob.status      == 'completed',
        )
    )
    job = result.scalar_one_or_none()
    if not job or not job.result_path:
        raise HTTPException(404, 'Image not found or no longer shared')

    path = Path(job.result_path)
    if not path.exists():
        raise HTTPException(404, 'Image file not found')

    return FileResponse(
        path,
        media_type='image/png',
        headers={
            'Cache-Control': 'public, max-age=3600',
            'Content-Disposition': 'inline',
        }
    )

class SkinAnalyzeRequest(BaseModel):
    upload_path: str


@app.post("/analyze-skin")
async def analyze_skin(
    req:          SkinAnalyzeRequest,
    current_user: User         = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    """
    Analyze skin tone and color season from an already-uploaded photo.
    Costs 1 credit. Deducts after successful analysis.

    Returns:
      skin_tone:           fair | light | medium | tan | deep
      undertone:           warm | cool | neutral
      hex:                 "#C4956A"
      season:              Spring | Summer | Autumn | Winter
      season_description:  str
      recommended_colors:  [{ name, hex, category, why }, ...]  (6 items)
    """
    # Check credits before doing any work
    has_credits = await check_has_credits(current_user.id, db)
    if not has_credits:
        raise HTTPException(402, "No credits available. Please top up to continue.")

    if not Path(req.upload_path).exists():
        raise HTTPException(422, "Upload file not found. Please upload your photo first.")

    try:
        result = await analyze_skin_tone(req.upload_path)
    except FileNotFoundError:
        raise HTTPException(422, "Upload file not found.")
    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {str(e)}")

    # Deduct 1 credit only after successful analysis
    await deduct_credit(current_user.id, db)

    return result