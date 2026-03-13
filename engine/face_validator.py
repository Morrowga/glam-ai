"""
GlamAI — Face Validator + Skin Tone Detector
Location: engine/face_validator.py

Uses MediaPipe (local, free, ~0.1 sec) for face validation.
Uses OpenCV skin sampling for skin tone detection.
No API calls. No cost. Instant.

Checks:
  - Face detected
  - Forward facing
  - Face size ok (not too far)
  - Eyes open
  - Not blurry (relaxed threshold for portrait/phone photos)

Skin tone categories:
  - fair    → very light skin, cool/neutral undertone
  - light   → light skin, warm or neutral undertone
  - medium  → medium/olive skin
  - tan     → tan/caramel skin
  - deep    → deep brown skin
  - rich    → very deep/dark skin

Notes:
  - Mouth check removed — smiling is fine
  - Blur threshold lowered to 30
  - Eye threshold lowered — downcast eyes still readable
  - Symmetry threshold lowered — slight head tilt is fine
"""

import cv2
import numpy as np
from pathlib import Path

try:
    import mediapipe as mp
    _mp_face_mesh = mp.solutions.face_mesh
    _mp_available = True
except ImportError:
    _mp_available = False


# ── Blur detection ────────────────────────────────────────────────

def _is_blurry(image: np.ndarray, threshold: float = 30.0) -> bool:
    gray      = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F).var()
    return laplacian < threshold


# ── Skin tone detection ───────────────────────────────────────────

def _detect_skin_tone(image: np.ndarray, landmarks: list, img_w: int, img_h: int) -> str:
    """
    Sample skin color from forehead and cheek regions using face landmarks.
    Returns one of: fair / light / medium / tan / deep / rich

    Sampling landmark indices:
      10  → forehead center
      151 → forehead slightly left
      9   → forehead slightly right
      205 → left cheek
      425 → right cheek
      50  → left jaw area
      280 → right jaw area
    """
    sample_indices = [10, 151, 9, 205, 425, 50, 280]

    pixels = []
    for idx in sample_indices:
        if idx >= len(landmarks):
            continue
        lm = landmarks[idx]
        px = int(lm.x * img_w)
        py = int(lm.y * img_h)

        x1 = max(0, px - 2)
        x2 = min(img_w, px + 3)
        y1 = max(0, py - 2)
        y2 = min(img_h, py + 3)

        patch = image[y1:y2, x1:x2]
        if patch.size == 0:
            continue

        patch_rgb  = cv2.cvtColor(patch, cv2.COLOR_BGR2RGB)
        mean_color = patch_rgb.mean(axis=(0, 1))
        pixels.append(mean_color)

    if not pixels:
        return "medium"

    avg = np.mean(pixels, axis=0)
    r, g, b = avg

    # Perceived luminance
    luminance = 0.299 * r + 0.587 * g + 0.114 * b

    if luminance >= 200:
        return "fair"
    elif luminance >= 170:
        return "light"
    elif luminance >= 140:
        return "medium"
    elif luminance >= 110:
        return "tan"
    elif luminance >= 75:
        return "deep"
    else:
        return "rich"


# ── Main validator ────────────────────────────────────────────────

async def validate_photo(image_path: str) -> dict:
    """
    Validate a user photo using MediaPipe face mesh.
    Also detects skin tone on successful validation.

    Returns:
        {
            "pass":          bool,
            "reject_reason": str or None,
            "skin_tone":     str,   <- fair/light/medium/tan/deep/rich
            "details":       dict
        }
    """
    if not _mp_available:
        return {
            "pass":          True,
            "reject_reason": None,
            "skin_tone":     "medium",
            "details":       {}
        }

    path = Path(image_path)
    if not path.exists():
        return {
            "pass":          False,
            "reject_reason": "Photo file not found.",
            "skin_tone":     "medium",
            "details":       {}
        }

    image = cv2.imread(str(path))
    if image is None:
        return {
            "pass":          False,
            "reject_reason": "Could not read photo. Please try a different image.",
            "skin_tone":     "medium",
            "details":       {}
        }

    img_h, img_w = image.shape[:2]
    not_blurry   = not _is_blurry(image)
    rgb          = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    with _mp_face_mesh.FaceMesh(
        static_image_mode        = True,
        max_num_faces            = 1,
        refine_landmarks         = True,
        min_detection_confidence = 0.5,
    ) as face_mesh:

        results = face_mesh.process(rgb)

        if not results.multi_face_landmarks:
            return {
                "pass":          False,
                "reject_reason": "No face detected. Please take a clear photo facing the camera.",
                "skin_tone":     "medium",
                "details": {
                    "face_detected":  False,
                    "forward_facing": False,
                    "face_size_ok":   False,
                    "eyes_open":      False,
                    "not_blurry":     not_blurry,
                }
            }

        landmarks = results.multi_face_landmarks[0].landmark

        # Face size
        xs           = [lm.x for lm in landmarks]
        ys           = [lm.y for lm in landmarks]
        face_area    = (max(xs) - min(xs)) * (max(ys) - min(ys))
        face_size_ok = face_area >= 0.05

        # Forward facing
        nose       = landmarks[1]
        left_ear   = landmarks[234]
        right_ear  = landmarks[454]
        left_dist  = abs(nose.x - left_ear.x)
        right_dist = abs(nose.x - right_ear.x)
        if left_dist + right_dist > 0:
            symmetry       = min(left_dist, right_dist) / max(left_dist, right_dist)
            forward_facing = symmetry >= 0.35
        else:
            forward_facing = False

        # Eyes open
        left_eye_open  = abs(landmarks[159].y - landmarks[145].y) > 0.007
        right_eye_open = abs(landmarks[386].y - landmarks[374].y) > 0.007
        eyes_open      = left_eye_open and right_eye_open

        details = {
            "face_detected":  True,
            "forward_facing": forward_facing,
            "face_size_ok":   face_size_ok,
            "eyes_open":      eyes_open,
            "not_blurry":     not_blurry,
        }

        if not not_blurry:
            return {"pass": False, "reject_reason": "Photo is too blurry. Please take a sharper photo in good lighting.", "skin_tone": "medium", "details": details}
        if not face_size_ok:
            return {"pass": False, "reject_reason": "Your face is too far from the camera. Please move a little closer.", "skin_tone": "medium", "details": details}
        if not forward_facing:
            return {"pass": False, "reject_reason": "Please face the camera more directly.", "skin_tone": "medium", "details": details}
        if not eyes_open:
            return {"pass": False, "reject_reason": "Please keep both eyes open for the photo.", "skin_tone": "medium", "details": details}

        # Detect skin tone only on valid photos
        skin_tone = _detect_skin_tone(image, landmarks, img_w, img_h)

        return {
            "pass":          True,
            "reject_reason": None,
            "skin_tone":     skin_tone,
            "details":       details,
        }