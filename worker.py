"""
worker.py
──────────
Background worker — polls for pending GenerationJob rows and runs Gemini.

Flow:
    1. POST /generate creates job with status="pending"
    2. Lifespan starts process_jobs() as asyncio task
    3. Worker sets status="processing" → calls Gemini → saves result
    4. Success → status="completed", deduct 1 credit from user
    5. Failure → status="failed", error_message set, credits NOT deducted
    6. Cancelled → status="cancelled", credits NOT deducted
"""

import asyncio
from datetime import datetime
from sqlalchemy import select
from db.models import AsyncSessionLocal, GenerationJob, Shade, Product, Brand, Category, ReferenceImage
from engine.generator import generate_with_image_edit
from engine.credits import deduct_credit
from shared_state import cancelled_jobs


async def process_jobs():
    print("🔄 Worker started — polling every 3 seconds...")
    while True:
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(GenerationJob)
                    .where(GenerationJob.status == "pending")
                    .order_by(GenerationJob.created_at)
                    .limit(1)
                )
                job = result.scalar_one_or_none()

                if job:
                    # ── Check 1: cancelled before we even start ────────────
                    if job.id in cancelled_jobs:
                        cancelled_jobs.discard(job.id)
                        job.status = "cancelled"
                        await db.commit()
                        print(f"🚫 Job {job.id} was cancelled before processing")
                        await asyncio.sleep(3)
                        continue

                    print(f"⚙️  Processing job {job.id}")
                    job.status = "processing"
                    await db.commit()

                    try:
                        # ── Load shade + product + brand + category ────────
                        row = await db.execute(
                            select(Shade, Product, Brand, Category)
                            .join(Product,  Shade.product_id    == Product.id)
                            .join(Brand,    Product.brand_id    == Brand.id)
                            .join(Category, Product.category_id == Category.id)
                            .where(Shade.id == job.shade_id)
                        )
                        row = row.first()
                        if not row:
                            raise Exception(f"Shade not found for job {job.id}")

                        shade, product, brand, category = row

                        # ── Load reference images (swatch only) ───────────
                        refs_result = await db.execute(
                            select(ReferenceImage)
                            .where(
                                ReferenceImage.shade_id == shade.id,
                                ReferenceImage.source   == "swatch",
                            )
                            .limit(1)
                        )
                        reference_paths = [r.image_path for r in refs_result.scalars().all()]

                        # ── Call Gemini ───────────────────────────────────
                        gen_result = await generate_with_image_edit(
                            user_photo_path = job.input_path,
                            prompt          = job.prompt_used,
                            job_id          = job.id,
                            category_slug   = category.slug,
                            reference_paths = reference_paths,
                        )

                        # ── Check 2: cancelled while Gemini was running ────
                        if job.id in cancelled_jobs:
                            cancelled_jobs.discard(job.id)
                            job.status = "cancelled"
                            await db.commit()
                            print(f"🚫 Job {job.id} was cancelled after Gemini returned — discarding result")
                            await asyncio.sleep(3)
                            continue

                        # ── Mark completed ────────────────────────────────
                        job.result_path     = gen_result["result_path"]
                        job.status          = "completed"
                        job.generation_time = gen_result["generation_time"]
                        job.completed_at    = datetime.utcnow()
                        await db.commit()

                        # ── Deduct credit ─────────────────────────────────
                        if job.user_id:
                            await deduct_credit(job.user_id, db)
                            print(f"💳 Credit deducted for user {job.user_id}")
                        else:
                            print(f"⚠️  Job {job.id} has no user_id — skipping credit deduction")

                        print(f"✅ Job {job.id} completed in {gen_result['generation_time']}s")

                    except Exception as e:
                        # Clean up cancellation set if error happened to a cancelled job
                        cancelled_jobs.discard(job.id)
                        job.status        = "failed"
                        job.error_message = str(e)
                        await db.commit()
                        print(f"❌ Job {job.id} failed: {e}")

        except Exception as e:
            print(f"⚠️  Worker loop error: {e}")

        await asyncio.sleep(3)