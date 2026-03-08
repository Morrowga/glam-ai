"""
GlamAI — Face Validator
Location: engine/face_validator.py

Uses MediaPipe (local, free, ~0.1 sec) for face validation.
No API calls. No cost. Instant.

Checks:
  - Face detected
  - Forward facing
  - Face size ok (not too far)
  - Eyes open
  - Mouth neutral
  - Not blurry
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

def _is_blurry(image: np.ndarray, threshold: float = 80.0) -> bool:
    gray      = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F).var()
    return laplacian < threshold


# ── Main validator ────────────────────────────────────────────────

async def validate_photo(image_path: str) -> dict:
    """
    Validate a user photo using MediaPipe face mesh.
    Fast, free, runs locally — no API calls.

    Returns:
        {
            "pass": bool,
            "reject_reason": str or None,
            "details": { all individual checks }
        }
    """

    if not _mp_available:
        return {
            "pass":          True,
            "reject_reason": None,
            "details":       {}
        }

    path = Path(image_path)
    if not path.exists():
        return {
            "pass":          False,
            "reject_reason": "Photo file not found.",
            "details":       {}
        }

    # Load image
    image = cv2.imread(str(path))
    if image is None:
        return {
            "pass":          False,
            "reject_reason": "Could not read photo. Please try a different image.",
            "details":       {}
        }

    # ── Blur check ────────────────────────────────────────────────
    not_blurry = not _is_blurry(image)

    # ── MediaPipe face mesh ───────────────────────────────────────
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    with _mp_face_mesh.FaceMesh(
        static_image_mode        = True,
        max_num_faces            = 1,
        refine_landmarks         = True,
        min_detection_confidence = 0.5,
    ) as face_mesh:

        results = face_mesh.process(rgb)

        # ── No face detected ──────────────────────────────────────
        if not results.multi_face_landmarks:
            return {
                "pass":          False,
                "reject_reason": "No face detected. Please take a clear photo facing the camera.",
                "details": {
                    "face_detected":  False,
                    "forward_facing": False,
                    "face_size_ok":   False,
                    "eyes_open":      False,
                    "mouth_neutral":  False,
                    "not_blurry":     not_blurry,
                }
            }

        landmarks = results.multi_face_landmarks[0].landmark

        # ── Face size ─────────────────────────────────────────────
        xs        = [lm.x for lm in landmarks]
        ys        = [lm.y for lm in landmarks]
        face_w    = max(xs) - min(xs)
        face_h    = max(ys) - min(ys)
        face_area = face_w * face_h
        face_size_ok = face_area >= 0.08

        # ── Forward facing ────────────────────────────────────────
        nose       = landmarks[1]
        left_ear   = landmarks[234]
        right_ear  = landmarks[454]
        left_dist  = abs(nose.x - left_ear.x)
        right_dist = abs(nose.x - right_ear.x)
        if left_dist + right_dist > 0:
            symmetry       = min(left_dist, right_dist) / max(left_dist, right_dist)
            forward_facing = symmetry >= 0.45
        else:
            forward_facing = False

        # ── Eyes open ─────────────────────────────────────────────
        left_eye_top     = landmarks[159]
        left_eye_bottom  = landmarks[145]
        right_eye_top    = landmarks[386]
        right_eye_bottom = landmarks[374]
        left_eye_open    = abs(left_eye_top.y  - left_eye_bottom.y) > 0.01
        right_eye_open   = abs(right_eye_top.y - right_eye_bottom.y) > 0.01
        eyes_open        = left_eye_open and right_eye_open

        # ── Mouth neutral ─────────────────────────────────────────
        mouth_top    = landmarks[13]
        mouth_bottom = landmarks[14]
        mouth_left   = landmarks[61]
        mouth_right  = landmarks[291]
        mouth_height = abs(mouth_top.y - mouth_bottom.y)
        mouth_width  = abs(mouth_left.x - mouth_right.x)
        mouth_ratio  = mouth_height / mouth_width if mouth_width > 0 else 0
        mouth_neutral = mouth_ratio < 0.25

        # ── Build details ─────────────────────────────────────────
        details = {
            "face_detected":  True,
            "forward_facing": forward_facing,
            "face_size_ok":   face_size_ok,
            "eyes_open":      eyes_open,
            "mouth_neutral":  mouth_neutral,
            "not_blurry":     not_blurry,
        }

        # Return first failure with human friendly reason
        if not not_blurry:
            return {"pass": False, "reject_reason": "Photo is too blurry. Please take a sharper photo.", "details": details}

        if not face_size_ok:
            return {"pass": False, "reject_reason": "Your face is too far from the camera. Please move closer.", "details": details}

        if not forward_facing:
            return {"pass": False, "reject_reason": "Please face the camera directly. Avoid tilting your head.", "details": details}

        if not eyes_open:
            return {"pass": False, "reject_reason": "Please keep both eyes open for the photo.", "details": details}

        if not mouth_neutral:
            return {"pass": False, "reject_reason": "Please keep your mouth closed or slightly open for the photo.", "details": details}

        return {
            "pass":          True,
            "reject_reason": None,
            "details":       details,
        }