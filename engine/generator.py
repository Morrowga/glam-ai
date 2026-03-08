"""
GlamAI Generator v17 — Gemini 3.1 Flash Image Preview
======================================================
- Primary: gemini-3.1-flash-image-preview
- Retry twice on failure (2s delay between)
- Email admin on full failure
- Return clean user-facing error
- RGBA → RGB fix for swatch images
"""

import os, time, asyncio
from io import BytesIO
from pathlib import Path
from PIL import Image
from dotenv import load_dotenv
from google import genai
from google.genai import types
import smtplib
from email.mime.text import MIMEText

load_dotenv()

_gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

GEMINI_MODEL = "gemini-3.1-flash-image-preview"
RESULTS_DIR  = Path(os.getenv("RESULTS_DIR", "./results"))
PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", os.getcwd()))
RESULTS_DIR.mkdir(exist_ok=True)

# ── Email config (.env) ───────────────────────────────────────────
# ADMIN_EMAIL=admin@yourdomain.com
# SMTP_HOST=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USER=your@gmail.com
# SMTP_PASS=your_app_password


# ── Image helpers ─────────────────────────────────────────────────

def _to_rgb(path: str) -> Image.Image:
    img = Image.open(path)
    if img.mode == "RGBA":
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        return background
    return img.convert("RGB")


def _image_part(path: str) -> types.Part:
    img = _to_rgb(path)
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
        else:
            print(f"[WARN] Reference image not found, skipping: {full}")
    return resolved


# ── Admin email notification ──────────────────────────────────────

def _notify_admin(error: str, prompt: str):
    try:
        admin_email = os.getenv("ADMIN_EMAIL")
        smtp_host   = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port   = int(os.getenv("SMTP_PORT", 587))
        smtp_user   = os.getenv("SMTP_USER")
        smtp_pass   = os.getenv("SMTP_PASS")

        if not all([admin_email, smtp_user, smtp_pass]):
            print("[WARN] Email config missing — skipping admin notification")
            return

        msg = MIMEText(
            f"GlamAI Generation Failed\n\n"
            f"Model: {GEMINI_MODEL}\n"
            f"Error: {error}\n"
            f"Prompt: {prompt}\n"
            f"Time: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}"
        )
        msg["Subject"] = "🚨 GlamAI — Generation Service Down"
        msg["From"]    = smtp_user
        msg["To"]      = admin_email

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, admin_email, msg.as_string())

        print(f"[INFO] Admin notified at {admin_email}")

    except Exception as e:
        print(f"[WARN] Failed to send admin email: {e}")


# ── Gemini call ───────────────────────────────────────────────────

async def _call_gemini(image_path: str, prompt: str, refs: list[str]) -> bytes:
    contents = [_image_part(image_path)]
    if refs:
        for ref in refs[:3]:
            contents.append(_image_part(ref))
        prompt = prompt + " Use the reference image(s) only to match the exact color and finish."
    contents.append(prompt)

    response = _gemini_client.models.generate_content(
        model    = GEMINI_MODEL,
        contents = contents,
        config   = types.GenerateContentConfig(
            response_modalities = ["IMAGE"],
            temperature         = 0.0,
        ),
    )

    if not response.candidates:
        raise RuntimeError(f"Gemini blocked. Feedback: {response.prompt_feedback}")

    candidate = response.candidates[0]
    if candidate.content is None or candidate.content.parts is None:
        raise RuntimeError(f"Gemini returned no content. Finish reason: {candidate.finish_reason}")

    for part in candidate.content.parts:
        if part.inline_data and part.inline_data.mime_type.startswith("image/"):
            return part.inline_data.data

    raise RuntimeError(f"Gemini returned no image. Finish reason: {candidate.finish_reason}")


# ── Main call with retry ──────────────────────────────────────────

async def _call(image_path: str, prompt: str, reference_paths: list[str] = None) -> tuple[bytes, int, str]:
    refs      = _resolve_refs(reference_paths)
    attempts  = 2
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            print(f"[INFO] Gemini attempt {attempt}/{attempts}")
            img_bytes = await _call_gemini(image_path, prompt, refs)
            print(f"[INFO] Gemini succeeded on attempt {attempt}")
            return img_bytes, len(refs), GEMINI_MODEL

        except Exception as e:
            last_error = e
            print(f"[WARN] Attempt {attempt} failed: {e}")
            if attempt < attempts:
                print(f"[INFO] Retrying in 2s...")
                await asyncio.sleep(2)

    # ── All attempts failed — notify admin ────────────────────────
    print(f"[ERROR] All {attempts} attempts failed. Notifying admin...")
    _notify_admin(error=str(last_error), prompt=prompt)

    raise RuntimeError("service_unavailable")


# ── Public functions ──────────────────────────────────────────────

async def generate_with_image_edit(
    user_photo_path: str,
    prompt: str,
    job_id: str,
    category_slug: str = None,
    reference_paths: list[str] = None,
) -> dict:
    print(f"[DEBUG] prompt: {prompt}")
    print(f"[DEBUG] reference_paths: {reference_paths}")
    print(f"[DEBUG] upload_path exists: {Path(user_photo_path).exists()}")

    start                            = time.time()
    img_bytes, refs_used, model_used = await _call(user_photo_path, prompt, reference_paths)
    result_path                      = RESULTS_DIR / f"{job_id}.png"
    _save_result(img_bytes, result_path)

    return {
        "result_path":     str(result_path),
        "generation_time": round(time.time() - start, 2),
        "references_used": refs_used,
        "model_used":      model_used,
    }


async def generate_combo(
    user_photo_path: str,
    steps: list[dict],
    job_id: str,
) -> dict:
    start                            = time.time()
    prompt                           = steps[0].get("combined_prompt") or steps[0]["prompt"]
    refs                             = steps[0].get("reference_paths", [])
    img_bytes, refs_used, model_used = await _call(user_photo_path, prompt, refs)
    result_path                      = RESULTS_DIR / f"{job_id}.png"
    _save_result(img_bytes, result_path)

    return {
        "result_path":     str(result_path),
        "generation_time": round(time.time() - start, 2),
        "references_used": refs_used,
        "model_used":      model_used,
        "calls_made":      1,
    }