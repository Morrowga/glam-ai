"""
GlamAI Generator v9 — images.edit with multiple images
=======================================================
gpt-image-1 images.edit supports up to 16 images in an array.
Pass [face_photo, ref1, ref2, ...] — no Responses API needed.
"""

import os, time, base64
from io import BytesIO
from pathlib import Path
from PIL import Image
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

client      = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
RESULTS_DIR = Path(os.getenv("RESULTS_DIR", "./results"))
RESULTS_DIR.mkdir(exist_ok=True)


async def generate_with_image_edit(
    user_photo_path: str,
    prompt: str,
    job_id: str,
    category_slug: str = None,
    reference_paths: list[str] = None,
) -> dict:
    start = time.time()

    refs = [r for r in (reference_paths or []) if os.path.exists(r)]

    if refs:
        # Multiple images: face photo first, then references
        images = []
        for path in [user_photo_path] + refs[:3]:
            images.append(open(path, "rb"))

        ref_instruction = (
            f"The last {len(refs)} image(s) are reference swatches showing the exact "
            f"color, finish, and intensity of the makeup product. "
            f"Match them precisely when applying to the first image (the face photo). "
        )
        full_prompt = ref_instruction + prompt

        try:
            response = await client.images.edit(
                model  = "gpt-image-1",
                image  = images,
                prompt = full_prompt,
                n      = 1,
                size   = "1024x1024",
            )
        finally:
            for f in images:
                f.close()
    else:
        # No references — single image
        with open(user_photo_path, "rb") as f:
            response = await client.images.edit(
                model  = "gpt-image-1",
                image  = f,
                prompt = prompt,
                n      = 1,
                size   = "1024x1024",
            )

    img_bytes   = base64.b64decode(response.data[0].b64_json)
    result_path = RESULTS_DIR / f"{job_id}.png"
    Image.open(BytesIO(img_bytes)).save(str(result_path), format="PNG")

    return {
        "result_path":     str(result_path),
        "generation_time": round(time.time() - start, 2),
        "cached":          False,
        "mask_used":       False,
        "references_used": len(refs),
    }