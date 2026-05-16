"""
routers/look_prep.py
─────────────────────
Look Preparation feature — all endpoints.

Endpoints:
    POST   /look-prep/default-photo          → upload + validate default face photo
    GET    /look-prep/default-photo          → get current default photo
    GET    /look-prep/bag                    → list user's saved products
    POST   /look-prep/bag                    → validate + add a product to bag
    DELETE /look-prep/bag/{product_id}       → remove a product from bag
    POST   /look-prep/check-sufficiency      → Gemini checks bag vs occasion
    POST   /look-prep/generate               → Gemini selects products → queues job

Plan gate: Basic + Glam only (not free, not PAYG).
"""

import os
import shutil
import uuid
import json
import secrets
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    get_db, User, UserProfile, UserProduct,
    GenerationJob, GenerationJobItem, UserSubscription,
)
from engine.auth_deps import get_current_user
from engine.credits import check_has_credits
from engine.face_validator import validate_photo
from engine.look_prep_engine import (
    validate_product,
    check_sufficiency,
    select_products_for_occasion,
)

router = APIRouter()

UPLOAD_DIR = Path("./uploads")
BASE_URL   = os.getenv("BASE_URL", "http://localhost:8087")

OCCASIONS = [
    # Everyday
    "Natural / No Makeup", "Office / Work", "Casual Day Out", "School / College", "Gym / Workout", "Running Errands",
    # Date & Romance
    "First Date", "Romantic Dinner", "Anniversary", "Valentine's Day",
    # Night Out
    "Party", "Club / Nightclub", "Sexy Night Out", "Girls Night Out", "Rooftop Bar", "Cocktail Party",
    # Formal & Events
    "Wedding Guest", "Bride", "Gala / Black Tie", "Graduation", "Award Ceremony", "Job Interview", "Business Meeting",
    # Seasonal & Holiday
    "Christmas", "New Year's Eve", "Halloween", "Eid / Hari Raya", "Diwali", "Summer Beach", "Winter Glam",
    # Cultural & Bridal
    "Traditional / Cultural", "Bridesmaid", "Engagement Party",
    # Mood & Aesthetic
    "Soft Girl", "Glam / Bold", "Minimal / Clean", "Vintage / Retro", "Y2K", "Dark / Edgy", "Cottagecore",
]


# ── Plan gate helper ──────────────────────────────────────────────────────────

async def _require_look_prep_plan(user: User, db: AsyncSession) -> None:
    """Raises 403 if user is on free or PAYG plan."""
    result = await db.execute(
        select(UserSubscription).where(UserSubscription.user_id == user.id)
    )
    sub = result.scalar_one_or_none()
    if not sub or sub.plan_type not in ("basic", "glam"):
        raise HTTPException(
            status_code=403,
            detail="Look Preparation is available on Basic and Glam plans only.",
        )


# ── GET + POST /look-prep/default-photo ──────────────────────────────────────

@router.get("/default-photo")
async def get_default_photo(
    current_user: User         = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    """Returns the user's current default face photo URL, or null if not set."""
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile or not profile.default_photo_path:
        return {"default_photo_url": None, "has_photo": False}

    # Check file still exists
    if not Path(profile.default_photo_path).exists():
        return {"default_photo_url": None, "has_photo": False}

    return {
        "default_photo_url": profile.default_photo_url,
        "has_photo":         True,
    }


@router.post("/default-photo")
async def upload_default_photo(
    file:         UploadFile   = File(...),
    current_user: User         = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    """
    Upload and validate a default face photo for Look Preparation.
    Validates with face_validator (same as Try On).
    Saves path to UserProfile.
    """
    await _require_look_prep_plan(current_user, db)

    file_id   = str(uuid.uuid4())[:8]
    ext       = file.filename.split(".")[-1].lower()
    save_path = UPLOAD_DIR / f"profile_{file_id}.{ext}"

    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Validate face
    validation = await validate_photo(str(save_path.resolve()))
    if not validation["pass"]:
        save_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=422,
            detail={
                "message":    validation["reject_reason"],
                "validation": validation["details"],
            },
        )

    # Upsert UserProfile
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    photo_url = f"{BASE_URL}/uploads/{save_path.name}"

    if profile:
        # Delete old photo file if it exists
        if profile.default_photo_path:
            old = Path(profile.default_photo_path)
            if old.exists() and old != save_path:
                old.unlink(missing_ok=True)
        profile.default_photo_path = str(save_path.resolve())
        profile.default_photo_url  = photo_url
    else:
        profile = UserProfile(
            user_id            = current_user.id,
            default_photo_path = str(save_path.resolve()),
            default_photo_url  = photo_url,
        )
        db.add(profile)

    await db.commit()

    return {
        "message":           "Default photo saved.",
        "default_photo_url": photo_url,
        "skin_tone":         validation.get("skin_tone", "medium"),
    }


# ── GET /look-prep/bag ────────────────────────────────────────────────────────

@router.get("/bag")
async def get_bag(
    current_user: User         = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    """Returns all active products in the user's bag, grouped by zone."""
    await _require_look_prep_plan(current_user, db)

    result = await db.execute(
        select(UserProduct)
        .where(
            UserProduct.user_id   == current_user.id,
            UserProduct.is_active == True,
        )
        .order_by(UserProduct.created_at)
    )
    products = result.scalars().all()

    return {
        "products": [
            {
                "id":           p.id,
                "raw_input":    p.raw_input,
                "brand":        p.brand,
                "product_name": p.product_name,
                "shade":        p.shade,
                "zone":         p.zone,
                "hex_color":    p.hex_color,
                "created_at":   p.created_at,
            }
            for p in products
        ],
        "count": len(products),
    }


# ── POST /look-prep/bag ───────────────────────────────────────────────────────

class AddProductRequest(BaseModel):
    raw_input: str               # exactly what the user typed
    shade:     str | None = None  # optional — provided if user fills shade prompt
    zone:      str | None = None  # zone the user selected in the chat flow (lip/eye/cheek)


@router.post("/bag")
async def add_product(
    req:          AddProductRequest,
    current_user: User             = Depends(get_current_user),
    db:           AsyncSession     = Depends(get_db),
):
    """
    Validate and add a product to the user's bag.

    Flow:
    1. Gemini validates the product text
    2. If invalid → return error
    3. If valid but shade missing → return shade_required: true (frontend prompts shade)
    4. If shade provided in req.shade → use it
    5. Save to user_products

    Free plan: max 5 products. Basic+Glam: unlimited.
    """
    await _require_look_prep_plan(current_user, db)

    raw = req.raw_input.strip()
    if not raw:
        raise HTTPException(400, "Product text cannot be empty.")
    if len(raw) > 200:
        raise HTTPException(400, "Product text too long (max 200 characters).")

    # Check product count limit
    count_result = await db.execute(
        select(UserProduct).where(
            UserProduct.user_id   == current_user.id,
            UserProduct.is_active == True,
        )
    )
    existing = count_result.scalars().all()

    # Check subscription for limit
    sub_result = await db.execute(
        select(UserSubscription).where(UserSubscription.user_id == current_user.id)
    )
    sub = sub_result.scalar_one_or_none()
    is_subscriber = sub and sub.plan_type in ("basic", "glam")

    # Free users capped at 5 (shouldn't reach here due to plan gate, but safety check)
    if not is_subscriber and len(existing) >= 5:
        raise HTTPException(403, "Free plan allows up to 5 products. Upgrade to add more.")

    # Gemini validation
    validation = await validate_product(raw)

    if not validation["valid"]:
        raise HTTPException(
            status_code=422,
            detail={
                "message":  validation.get("reject_reason") or "This doesn't look like a real makeup product.",
                "valid":    False,
            },
        )

    # Zone mismatch check — Gemini's zone is the truth, not the user's selection
    gemini_zone = validation.get("zone")
    user_zone   = raw.split(" in ")[0].strip()  # not reliable — use req body zone if available

    # The raw_input contains the zone the user picked in the chat flow.
    # We pass it as part of the raw string e.g. "MAC Ruby Woo Lipstick in Ruby Woo"
    # But Gemini independently detected the real zone. If they don't match, reject.
    if gemini_zone and req.zone and gemini_zone != req.zone:
        raise HTTPException(
            status_code=422,
            detail={
                "message": f"This looks like a {gemini_zone} product, not a {req.zone} product. Please add it under the correct zone.",
                "valid":   False,
                "actual_zone": gemini_zone,
            },
        )

    # Use Gemini zone as source of truth
    final_zone = gemini_zone or req.zone

    if not final_zone:
        raise HTTPException(
            status_code=422,
            detail={"message": "Could not determine the product zone. Please try again.", "valid": False},
        )

    # Shade resolution: req.shade overrides Gemini extraction
    shade = req.shade or validation.get("shade")
    shade_missing = (not shade) and validation.get("shade_missing", False)

    # If shade still missing → ask frontend to prompt user
    if shade_missing:
        return {
            "shade_required": True,
            "message":        f"What shade is your {validation.get('product_name') or raw}?",
            "partial": {
                "brand":        validation.get("brand"),
                "product_name": validation.get("product_name"),
                "zone":         validation.get("zone"),
            },
        }

    # Duplicate check — same brand + product_name + shade for this user
    dup_result = await db.execute(
        select(UserProduct).where(
            UserProduct.user_id      == current_user.id,
            UserProduct.is_active    == True,
            UserProduct.brand        == validation.get("brand"),
            UserProduct.product_name == validation.get("product_name"),
            UserProduct.shade        == shade,
        )
    )
    if dup_result.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail={
                "message": f"{validation.get('brand')} {validation.get('product_name')} in {shade} is already in your bag.",
                "valid": True,
            },
        )

    # Save to DB
    product = UserProduct(
        user_id      = current_user.id,
        raw_input    = raw,
        brand        = validation.get("brand"),
        product_name = validation.get("product_name"),
        shade        = shade,
        zone         = final_zone,
        hex_color    = validation.get("hex_color"),
        is_active    = True,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    return {
        "shade_required": False,
        "message":        "Product added to your bag.",
        "product": {
            "id":           product.id,
            "raw_input":    product.raw_input,
            "brand":        product.brand,
            "product_name": product.product_name,
            "shade":        product.shade,
            "zone":         product.zone,
            "hex_color":    product.hex_color,
        },
    }


# ── DELETE /look-prep/bag/{product_id} ───────────────────────────────────────

@router.delete("/bag/{product_id}")
async def remove_product(
    product_id:   str,
    current_user: User         = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    """Soft-delete a product from the bag."""
    result = await db.execute(
        select(UserProduct).where(
            UserProduct.id      == product_id,
            UserProduct.user_id == current_user.id,
        )
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(404, "Product not found.")

    product.is_active = False
    await db.commit()

    return {"message": "Product removed from bag."}


# ── POST /look-prep/check-sufficiency ────────────────────────────────────────

class CheckSufficiencyRequest(BaseModel):
    occasion: str


@router.post("/check-sufficiency")
async def check_bag_sufficiency(
    req:          CheckSufficiencyRequest,
    current_user: User                    = Depends(get_current_user),
    db:           AsyncSession            = Depends(get_db),
):
    """
    Gemini checks whether the user's bag is sufficient for the given occasion.
    Returns per-zone scores + advice text.
    """
    await _require_look_prep_plan(current_user, db)

    if req.occasion not in OCCASIONS:
        raise HTTPException(400, f"Invalid occasion. Choose from: {', '.join(OCCASIONS)}")

    # Load bag
    result = await db.execute(
        select(UserProduct).where(
            UserProduct.user_id   == current_user.id,
            UserProduct.is_active == True,
        )
    )
    products = result.scalars().all()

    if not products:
        raise HTTPException(400, "Your bag is empty. Add some products first.")

    bag = [
        {
            "brand":        p.brand,
            "product_name": p.product_name,
            "shade":        p.shade,
            "zone":         p.zone,
            "hex_color":    p.hex_color,
        }
        for p in products
    ]

    result = await check_sufficiency(bag, req.occasion)

    return {
        "occasion": req.occasion,
        **result,
    }


# ── POST /look-prep/generate ──────────────────────────────────────────────────

class GenerateLookRequest(BaseModel):
    occasion:    str
    force:       bool = False   # True = user clicked "Generate Anyway"


@router.post("/generate")
async def generate_look(
    req:          GenerateLookRequest,
    current_user: User                = Depends(get_current_user),
    db:           AsyncSession        = Depends(get_db),
):
    """
    Generate a makeup look from the user's bag for the given occasion.

    Flow:
    1. Check credits
    2. Load default photo
    3. Load bag
    4. Gemini selects best products from bag for occasion
    5. Build prompt from selected products using prompt_engine logic
    6. Queue GenerationJob (reuses existing worker pipeline)
    7. Return job_id for polling
    """
    await _require_look_prep_plan(current_user, db)

    if req.occasion not in OCCASIONS:
        raise HTTPException(400, f"Invalid occasion. Choose from: {', '.join(OCCASIONS)}")

    # Check credits
    has_credits = await check_has_credits(current_user.id, db)
    if not has_credits:
        raise HTTPException(402, "No credits available. Please top up to continue.")

    # Load default photo
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()

    if not profile or not profile.default_photo_path:
        raise HTTPException(
            status_code=422,
            detail="No default photo set. Please upload your face photo first.",
        )
    if not Path(profile.default_photo_path).exists():
        raise HTTPException(
            status_code=422,
            detail="Default photo file not found. Please re-upload your face photo.",
        )

    # Load bag
    bag_result = await db.execute(
        select(UserProduct).where(
            UserProduct.user_id   == current_user.id,
            UserProduct.is_active == True,
        )
    )
    products = bag_result.scalars().all()

    if not products:
        raise HTTPException(400, "Your bag is empty. Add some products first.")

    bag = [
        {
            "brand":        p.brand,
            "product_name": p.product_name,
            "shade":        p.shade,
            "zone":         p.zone,
            "hex_color":    p.hex_color,
        }
        for p in products
    ]

    # Gemini selects best products
    selection = await select_products_for_occasion(bag, req.occasion)
    selected  = selection.get("selected", [])

    if not selected:
        raise HTTPException(500, "Could not select products for this occasion. Please try again.")

    # Build prompt from selected products
    # Map zone names to prompt_engine zone format
    ZONE_MAP = {"lip": "lips", "eye": "eyes", "cheek": "cheeks"}

    prompt_parts = []
    for item in selected:
        zone        = ZONE_MAP.get(item.get("zone", ""), "")
        brand       = item.get("brand", "")
        product     = item.get("product_name", "")
        shade       = item.get("shade", "")
        reason      = item.get("reason", "")
        prompt_parts.append(
            f"apply {brand} {product} in {shade} to her {zone}"
        )

    look_desc = selection.get("look_description", f"{req.occasion} look")

    prompt = (
        f"Create a {req.occasion} makeup look using only the following products. "
        f"Apply each product carefully and do not add anything not listed. "
        f"Look goal: {look_desc}\n\n"
        + "\n".join(f"- {p}" for p in prompt_parts)
        + "\n\nKeep her skin, facial features, hair, and background completely unchanged. "
        "The result should look like a real professionally applied makeup look."
    )

    # Queue job — reuses existing GenerationJob + worker pipeline
    # Use the first selected product's zone as the job zone
    first_zone = selected[0].get("zone", "multi") if selected else "multi"
    session_id = str(uuid.uuid4())

    # We need a shade_id for the job FK — use a placeholder approach:
    # Look Prep jobs don't map to DB shades, so we create the job with
    # shade_id = None is not allowed by FK. We'll use the first real shade
    # we can find, or add a sentinel. For now we skip shade_id by using
    # a special "look_prep" marker approach: reuse the job without shade_id
    # by making it nullable in models. Since GenerationJob.shade_id is
    # ForeignKey("shades.id") NOT NULL, we need to find a real shade or
    # make it nullable. The cleanest fix: add nullable=True to shade_id in
    # models.py for look prep support. See models_additions.py note below.
    #
    # For now we queue with shade_id pointing to a sentinel — the worker
    # already handles missing shade by reading prompt_used directly
    # (it only loads shade for reference images, which look prep doesn't need).

    # Find any valid shade_id as a placeholder (worker won't use it for prompt)
    from db.models import Shade
    any_shade = await db.execute(select(Shade).limit(1))
    placeholder_shade = any_shade.scalar_one_or_none()

    if not placeholder_shade:
        raise HTTPException(500, "No shades in database. Please run the seeder first.")

    job = GenerationJob(
        user_id     = current_user.id,
        session_id  = session_id,
        chain_order = 0,
        shade_id    = placeholder_shade.id,  # placeholder — prompt_used drives generation
        upload_path = profile.default_photo_path,
        input_path  = profile.default_photo_path,
        prompt_used = prompt,
        zone        = first_zone,
        status      = "pending",
    )
    job.look_meta = json.dumps({
        "occasion":         req.occasion,
        "look_description": look_desc,
        "products_used":    selected,
    })
    db.add(job)
    await db.commit()
    await db.refresh(job)

    return {
        "job_id":           job.id,
        "session_id":       session_id,
        "status":           "pending",
        "occasion":         req.occasion,
        "look_description": look_desc,
        "products_used":    selected,
        "message":          "Look generation queued. Poll GET /jobs/{job_id} for result.",
    }


# ── POST /look-prep/{job_id}/share ────────────────────────────────────────────

@router.post("/{job_id}/share")
async def create_look_prep_share(
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
    if job.status != "completed" or not job.result_path:
        raise HTTPException(400, "Job not completed yet")
    if not job.share_token:
        job.share_token = secrets.token_urlsafe(32)
    job.is_shared = True
    await db.commit()
    await db.refresh(job)
    return {
        "share_url":   f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/dashboard/look-prep/{job.share_token}",
        "share_token": job.share_token,
    }


# ── GET /look-prep/share/{share_token} ───────────────────────────────────────

@router.get("/share/{share_token}")
async def get_shared_look_prep(
    share_token: str,
    db:          AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GenerationJob).where(
            GenerationJob.share_token == share_token,
            GenerationJob.is_shared   == True,
            GenerationJob.status      == "completed",
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Look not found or no longer shared")

    BASE_URL = os.getenv("BASE_URL", "http://localhost:8087")
    result_url = f"{BASE_URL}/results/{Path(job.result_path).name}" if job.result_path else None

    look_meta = {}
    if job.look_meta:
        try:
            look_meta = json.loads(job.look_meta)
        except Exception:
            pass

    return {
        "share_token":      share_token,
        "result_url":       result_url,
        "occasion":         look_meta.get("occasion", ""),
        "look_description": look_meta.get("look_description", ""),
        "products_used":    look_meta.get("products_used", []),
        "created_at":       job.created_at.isoformat() if job.created_at else None,
    }