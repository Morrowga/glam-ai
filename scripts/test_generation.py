"""
Test a single generation end to end.
Usage: python scripts/test_generation.py
"""
import asyncio, sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.prompt_engine import build_prompt
from engine.generator import generate_with_image_edit
from rich.console import Console
import uuid

console = Console()

async def test():
    # ── Test prompt engine ───────────────────────────────────────
    console.print("\n[bold cyan]Testing Prompt Engine[/]")

    test_cases = [
        ("lipstick",    {"brand_name":"MAC","product_name":"Ruby Woo","shade_name":"Ruby Woo","hex_color":"#9B1B30","finish_type":"matte","coverage":"full"}),
        ("eyeshadow",   {"brand_name":"Urban Decay","product_name":"Naked Palette","shade_name":"Smog","hex_color":"#706050","finish_type":"shimmer","coverage":"medium"}),
        ("foundation",  {"brand_name":"Fenty Beauty","product_name":"Pro Filt'r","shade_name":"220N","hex_color":"#D4A882","finish_type":"matte","coverage":"full"}),
        ("blush",       {"brand_name":"NARS","product_name":"Orgasm Blush","shade_name":"Orgasm","hex_color":"#E89080","finish_type":"shimmer","coverage":"medium"}),
        ("mascara",     {"brand_name":"Maybelline","product_name":"Sky High","shade_name":"Blackest Black","hex_color":"#050505","finish_type":"matte","coverage":"full"}),
    ]

    for category, data in test_cases:
        prompt = build_prompt(category, data)
        console.print(f"\n[yellow]{category.upper()} — {data['brand_name']} {data['shade_name']}[/]")
        console.print(f"[dim]{prompt[:120]}...[/]")

    # ── Test actual generation ───────────────────────────────────
    console.print("\n[bold cyan]Testing Generation[/]")

    user_photo = input("\nEnter path to your bare face test photo: ").strip()

    if not os.path.exists(user_photo):
        console.print("[red]Photo not found. Skipping generation test.[/]")
        return

    console.print("\n[yellow]Building prompt for MAC Ruby Woo...[/]")
    prompt = build_prompt("lipstick", {
        "brand_name":   "MAC Cosmetics",
        "product_name": "Ruby Woo Lipstick",
        "shade_name":   "Ruby Woo",
        "hex_color":    "#9B1B30",
        "finish_type":  "matte",
        "coverage":     "full",
        "prompt_supplement": "Iconic blue-red. Perfectly defined lip edges."
    })

    console.print(f"[green]Prompt built ({len(prompt)} chars)[/]")
    console.print("\n[yellow]Sending to OpenAI...[/]")

    result = await generate_with_image_edit(
        user_photo_path=user_photo,
        prompt=prompt,
        job_id=str(uuid.uuid4())[:8]
    )

    console.print(f"\n[bold green]✅ Generation complete![/]")
    console.print(f"Result saved to: [cyan]{result['result_path']}[/]")
    console.print(f"Time taken: [yellow]{result['generation_time']}s[/]")

if __name__ == "__main__":
    asyncio.run(test())