#!/usr/bin/env python3
"""
Furniture Mockup Generator — @haus_living1
Uses Hermes image_gen tool via CLI
"""
import subprocess
import json
import os
from pathlib import Path

OUTPUT_DIR = Path.home() / ".hermes/haus-living/mockups"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PROMPTS = [
    ("sofa-living-room", "Modern minimalist L-shape sofa in warm-toned living room, dark charcoal wall, natural oak coffee table, warm ambient floor lamp, green monstera plant, cozy linen throw pillows, area rug, photorealistic interior photography, warm color grading, 4:5 portrait"),
    ("dining-set-warm", "Modern minimalist dining table 6-seater with upholstered chairs, solid walnut wood, dark concrete floor, warm pendant lights, elegant table setting with candles, photorealistic furniture catalog, warm ambient lighting"),
    ("bedroom-cozy", "Modern minimalist bedroom, low-profile walnut bed frame, white linen bedding with knit throw blanket, floating bedside shelf with warm lamp and books, dark navy feature wall, potted plant, cozy atmosphere, interior photography"),
    ("tv-unit-floating", "Modern floating TV unit on dark charcoal wall, natural oak wood, hidden cables, warm LED strip underneath, minimalist styling with ceramic vase, clean interior design, warm ambient glow"),
    ("desk-wfh-setup", "Modern WFH desk setup, natural solid wood desk, clean cables, laptop on stand, small succulent plant, warm brass task lamp, dark wall, productivity aesthetic, warm lighting"),
    ("reading-nook", "Cozy reading nook with terracotta armchair, arc floor lamp, round side table with coffee mug and book, wall bookshelf, trailing plant, warm golden lighting, dark wall, hygge lifestyle"),
]

def main():
    print("🎨 FURNITURE MOCKUP GENERATOR — @haus_living1")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Images: {len(PROMPTS)}")
    print()
    
    # Write prompts as a reference file
    for name, prompt in PROMPTS:
        print(f"  📝 {name}: {prompt[:60]}...")
    
    print()
    print("Run each prompt via: hermes tools call image_gen --prompt '...'")
    print("Or use the prompts directly in chat with 'generate image of ...'")
    print()
    
    # Save prompts for manual use
    prompts_file = OUTPUT_DIR / "prompts.json"
    with open(prompts_file, "w") as f:
        json.dump([{"name": n, "prompt": p} for n, p in PROMPTS], f, indent=2)
    print(f"Prompts saved: {prompts_file}")

if __name__ == "__main__":
    main()
