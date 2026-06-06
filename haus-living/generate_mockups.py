#!/usr/bin/env python3
"""
Furniture Mockup Generator for @haus_living1
Uses Pollinations.ai (free, no API key) for image generation.
"""
import urllib.request
import json
import time
import os
from pathlib import Path

OUTPUT_DIR = Path.home() / ".hermes/haus-living/mockups"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PROMPTS = [
    {
        "name": "sofa-living-room",
        "prompt": "Modern minimalist L-shape sofa in a warm-toned living room interior, dark charcoal wall background, natural oak wood coffee table, soft warm ambient lighting from floor lamp, green monstera plant in corner, cozy linen throw pillows on sofa, rug on floor, photorealistic, 4:5 portrait, high-end furniture catalog quality, warm color grading, interior design photography"
    },
    {
        "name": "dining-set-warm",
        "prompt": "Modern minimalist dining set with rectangular 6-seater dining table and upholstered chairs, solid walnut wood tones, dark concrete tile floor, warm pendant lighting hanging above table, elegant table setting with white plates and candles, photorealistic, 4:5 portrait, furniture catalog quality, warm ambient lighting, interior design photography"
    },
    {
        "name": "bedroom-cozy",
        "prompt": "Modern minimalist bedroom interior with low-profile bed frame in natural walnut wood finish, white linen bedding with beige knit throw blanket, floating bedside shelf with small warm lamp and stacked books, warm ambient lighting, dark navy feature wall, potted plant, photorealistic, 4:5 portrait, aspirational home lifestyle, cozy atmosphere"
    },
    {
        "name": "tv-unit-floating",
        "prompt": "Modern floating TV media unit wall-mounted on dark charcoal painted wall, natural oak wood finish with grain texture, hidden cable management, subtle warm LED strip lighting underneath unit, minimalist styling with small ceramic vase and art books, photorealistic, 4:5 portrait, clean interior design style, warm ambient glow"
    },
    {
        "name": "desk-wfh-setup",
        "prompt": "Modern minimal work from home desk setup, natural solid wood desk 120cm width, clean cable management, laptop and external monitor on stand, small desk plant succulent, warm brass task lamp, dark wall background, wooden desk accessories, photorealistic, 4:5 portrait, productivity aesthetic, warm lighting"
    },
    {
        "name": "reading-nook",
        "prompt": "Cozy reading nook corner with modern accent armchair in warm terracotta fabric, tall arc floor lamp with warm light, small round side table with coffee mug and book, wall-mounted bookshelf with books, trailing green plant, warm golden lighting, dark corner wall ambiance, photorealistic, 4:5 portrait, hygge lifestyle, soft focus background"
    },
]

def generate_image(prompt: str, output_path: str, width: int = 768, height: int = 960) -> bool:
    """Generate image via Pollinations.ai (free, no API key)."""
    encoded_prompt = urllib.request.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true&seed={int(time.time())}"
    
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })
        resp = urllib.request.urlopen(req, timeout=120)
        data = resp.read()
        
        if len(data) > 10000:  # Valid image should be >10KB
            with open(output_path, "wb") as f:
                f.write(data)
            return True
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False

def main():
    print("╔══════════════════════════════════════════════════╗")
    print("║  🎨 FURNITURE MOCKUP GENERATOR — @haus_living1  ║")
    print("╚══════════════════════════════════════════════════╝")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Images: {len(PROMPTS)}")
    print()
    
    results = []
    for i, item in enumerate(PROMPTS, 1):
        name = item["name"]
        prompt = item["prompt"]
        output_path = OUTPUT_DIR / f"{name}.jpg"
        
        print(f"[{i}/{len(PROMPTS)}] Generating: {name}")
        print(f"  Prompt: {prompt[:80]}...")
        
        ok = generate_image(prompt, str(output_path))
        if ok:
            size = os.path.getsize(output_path)
            print(f"  ✅ Saved: {output_path.name} ({size//1024}KB)")
            results.append({"name": name, "path": str(output_path), "size": size, "status": "ok"})
        else:
            print(f"  ❌ Failed")
            results.append({"name": name, "path": str(output_path), "size": 0, "status": "failed"})
        
        # Rate limit
        if i < len(PROMPTS):
            print(f"  Waiting 5s...")
            time.sleep(5)
    
    print()
    print("══════════════════════════════════════════════════")
    ok_count = sum(1 for r in results if r["status"] == "ok")
    print(f"Results: {ok_count}/{len(results)} images generated")
    for r in results:
        icon = "✅" if r["status"] == "ok" else "❌"
        print(f"  {icon} {r['name']}")
    
    # Save manifest
    manifest_path = OUTPUT_DIR / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nManifest: {manifest_path}")

if __name__ == "__main__":
    main()
