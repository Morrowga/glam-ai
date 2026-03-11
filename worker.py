# worker.py
import asyncio
from sqlalchemy import select
from sqlalchemy.sql import func
from datetime import datetime
from db.models import AsyncSessionLocal, GenerationJob, Shade, Product, Brand, Category, ReferenceImage
from engine.generator import generate_with_image_edit
from engine.prompt_engine import build_prompt
from engine.credits import deduct_credit

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
                    print(f"⚙️  Processing job {job.id}")
                    job.status = "processing"
                    await db.commit()

                    try:
                        # Load shade + product + brand + category
                        row = await db.execute(
                            select(Shade, Product, Brand, Category)
                            .join(Product,  Shade.product_id   == Product.id)
                            .join(Brand,    Product.brand_id   == Brand.id)
                            .join(Category, Product.category_id == Category.id)
                            .where(Shade.id == job.shade_id)
                        )
                        row = row.first()
                        if not row:
                            raise Exception(f"Shade not found for job {job.id}")

                        shade, product, brand, category = row

                        # Load reference images
                        refs = await db.execute(
                            select(ReferenceImage)
                            .where(
                                ReferenceImage.shade_id == shade.id,
                                ReferenceImage.source == "swatch"
                            )
                            .limit(1)
                        )
                        reference_paths = [r.image_path for r in refs.scalars().all()]

                        # Call Gemini
                        result = await generate_with_image_edit(
                            user_photo_path = job.input_path,
                            prompt          = job.prompt_used,
                            job_id          = job.id,
                            category_slug   = category.slug,
                            reference_paths = reference_paths,
                        )

                        job.result_path     = result["result_path"]
                        job.status          = "complete"
                        job.generation_time = result["generation_time"]
                        job.completed_at    = datetime.utcnow()
                        if job.user_id:
                            await deduct_credit(job.user_id, db)
                        print(f"✅ Job {job.id} complete")

                    except Exception as e:
                        job.status        = "failed"
                        job.error_message = str(e)
                        print(f"❌ Job {job.id} failed: {e}")

                    await db.commit()

        except Exception as e:
            print(f"⚠️  Worker loop error: {e}")

        await asyncio.sleep(3)

if __name__ == "__main__":
    asyncio.run(process_jobs())