"""
GlamAI Generator v15 — Gemini 3.1 Flash Image Preview
======================================================
- Single call for everything, no chaining
- Ref images resolved from project root
"""

import os, time
from io import BytesIO
from pathlib import Path
from PIL import Image
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

_client      = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
GEMINI_MODEL = "gemini-3.1-flash-image-preview"
RESULTS_DIR  = Path(os.getenv("RESULTS_DIR", "./results"))
PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", os.getcwd()))
RESULTS_DIR.mkdir(exist_ok=True)


def _image_part(path: str) -> types.Part:
    img = Image.open(path).convert("RGB")
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg")


def _save_result(img_bytes: bytes, result_path: Path):
    Image.open(BytesIO(img_bytes)).convert("RGB").save(str(result_path), format="PNG")


def _resolve_refs(reference_paths: list[str]) -> list[str]:
    resolved = []
    for r in (reference_paths or []):
        full = PROJECT_ROOT / r
        if full.exists():
            resolved.append(str(full))
    return resolved


async def _call(image_path: str, prompt: str, reference_paths: list[str] = None) -> tuple[bytes, int]:
    refs = _resolve_refs(reference_paths)

    contents = [_image_part(image_path)]
    if refs:
        for ref in refs[:3]:
            contents.append(_image_part(ref))
        prompt = prompt + " Use the reference image(s) only to match the exact color and finish."
    contents.append(prompt)

    response = _client.models.generate_content(
        model    = GEMINI_MODEL,
        contents = contents,
        config   = types.GenerateContentConfig(
            response_modalities = ["IMAGE"],
            temperature         = 0.0,
        ),
    )

    if not response.candidates:
        raise RuntimeError(f"Gemini blocked the request. Feedback: {response.prompt_feedback}")

    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.mime_type.startswith("image/"):
            return part.inline_data.data, len(refs)

    raise RuntimeError(f"Gemini returned no image. Finish reason: {response.candidates[0].finish_reason}")


async def generate_with_image_edit(
    user_photo_path: str,
    prompt: str,
    job_id: str,
    category_slug: str = None,
    reference_paths: list[str] = None,
) -> dict:
    start               = time.time()
    img_bytes, refs_used = await _call(user_photo_path, prompt, reference_paths)
    result_path         = RESULTS_DIR / f"{job_id}.png"
    _save_result(img_bytes, result_path)

    return {
        "result_path":     str(result_path),
        "generation_time": round(time.time() - start, 2),
        "references_used": refs_used,
    }


async def generate_combo(
    user_photo_path: str,
    steps: list[dict],
    job_id: str,
) -> dict:
    start               = time.time()
    prompt              = steps[0].get("combined_prompt") or steps[0]["prompt"]
    refs                = steps[0].get("reference_paths", [])
    img_bytes, refs_used = await _call(user_photo_path, prompt, refs)
    result_path         = RESULTS_DIR / f"{job_id}.png"
    _save_result(img_bytes, result_path)

    return {
        "result_path":     str(result_path),
        "generation_time": round(time.time() - start, 2),
        "references_used": refs_used,
        "calls_made":      1,
    }