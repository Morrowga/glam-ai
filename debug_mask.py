"""
Debug script — generates and saves the mask as a visible overlay
so you can see exactly where the mask lands on the face.

Run: python debug_mask.py <image_path> <category_slug>
Example: python debug_mask.py uploads/abc.jpg lipstick
"""
import sys, cv2
import numpy as np
from PIL import Image
from pathlib import Path
sys.path.append(".")

from engine.masking import generate_mask, RESULTS_DIR

def debug_mask(image_path: str, category_slug: str):
    # Generate the mask
    mask_path = generate_mask(image_path, category_slug, "debug")
    if not mask_path:
        print("❌ No face detected or no mask for this category")
        return

    # Load original resized to 1024x1024
    original = Image.open(image_path).convert("RGBA").resize((1024, 1024), Image.LANCZOS)

    # Load mask
    mask = Image.open(mask_path).convert("RGBA")
    mask_alpha = mask.split()[3]                     # alpha channel
    paste_alpha = mask_alpha.point(lambda p: 255-p)  # invert → edit zone = white

    # Create red overlay to show edit zone
    overlay = Image.new("RGBA", (1024, 1024), (255, 0, 0, 120))

    # Paste red overlay onto original using edit zone mask
    debug_img = original.copy()
    debug_img.paste(overlay, mask=paste_alpha)

    # Save debug image
    out_path = RESULTS_DIR / f"debug_{category_slug}_overlay.png"
    debug_img.convert("RGB").save(str(out_path))
    print(f"✅ Debug overlay saved: {out_path}")
    print(f"   Red zone = where AI edits will be applied")

    # Also save the raw mask as grayscale for inspection
    raw_path = RESULTS_DIR / f"debug_{category_slug}_mask_raw.png"
    paste_alpha.save(str(raw_path))
    print(f"✅ Raw mask saved: {raw_path}")
    print(f"   White = edit zone, Black = preserved")

    # Cleanup
    Path(mask_path).unlink(missing_ok=True)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python debug_mask.py <image_path> <category_slug>")
        print("Categories: lipstick, eyeshadow, blush, foundation, etc.")
        sys.exit(1)
    debug_mask(sys.argv[1], sys.argv[2])