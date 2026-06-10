#!/usr/bin/env python3
"""
Brand Watermark Tool — Instagram Brand Management Skill

Adds watermark to product photos for IG content and catalog.
Uses Pillow only — no GPU, no API key required.

Usage:
  python3 watermark.py <input_image> [--type catalog|content|reel] [--output output.png]
  python3 watermark.py batch <input_folder> [--type catalog|content|reel] [--output output_folder/]

Customize BRAND, COLOR_HONEY, COLOR_DARK below for your brand.
"""

import os
import sys
import argparse
from PIL import Image, ImageDraw, ImageFont

# ===== BRAND CONFIG — edit these for your brand =====
BRAND_SHORT = "HL"          # Monogram initials
BRAND_NAME = "HAUS LIVING"  # Full brand name (first word = primary, rest = secondary)
BRAND_WORD1 = "HAUS"        # Primary word
BRAND_WORD2 = "LIVING"      # Secondary word
COLOR_HONEY = (212, 165, 116)  # #D4A574 — honey/oak accent
COLOR_DARK = (26, 26, 26)      # #1A1A1A — dark background
# ====================================================

def get_font(size, bold=False):
    """Try to load a serif font, fallback to default."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            return ImageFont.truetype(fp, size)
    return ImageFont.load_default()

def watermark_catalog(img):
    """Subtle corner stamp — bottom-right, very low opacity (15%)."""
    w, h = img.size
    overlay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    base_size = min(w, h)

    font_main = get_font(int(base_size * 0.035), bold=True)
    font_sub = get_font(int(base_size * 0.02))
    font_hl = get_font(int(base_size * 0.065), bold=True)

    hl_bbox = draw.textbbox((0, 0), BRAND_SHORT, font=font_hl)
    hl_w, hl_h = hl_bbox[2] - hl_bbox[0], hl_bbox[3] - hl_bbox[1]
    haus_bbox = draw.textbbox((0, 0), BRAND_WORD1, font=font_main)
    haus_w, haus_h = haus_bbox[2] - haus_bbox[0], haus_bbox[3] - haus_bbox[1]
    liv_bbox = draw.textbbox((0, 0), BRAND_WORD2, font=font_sub)
    liv_w, liv_h = liv_bbox[2] - liv_bbox[0], liv_bbox[3] - liv_bbox[1]

    total_w = hl_w + 20 + max(haus_w, liv_w)
    total_h = max(hl_h, haus_h + liv_h + 5)
    pad = int(base_size * 0.04)
    x_start = w - total_w - pad
    y_start = h - total_h - pad
    opacity_main = int(255 * 0.15)
    opacity_sub = int(255 * 0.10)

    draw.text((x_start, y_start), BRAND_SHORT, fill=(*COLOR_HONEY, opacity_main), font=font_hl)
    x_right = x_start + hl_w + 20
    draw.text((x_right, y_start), BRAND_WORD1, fill=(*COLOR_HONEY, opacity_main), font=font_main)
    draw.text((x_right, y_start + haus_h + 5), BRAND_WORD2, fill=(*COLOR_HONEY, opacity_sub), font=font_sub)
    div_x = x_start + hl_w + 10
    draw.line([(div_x, y_start + 5), (div_x, y_start + total_h - 5)], fill=(*COLOR_HONEY, int(255 * 0.08)), width=1)

    result = img.convert('RGBA')
    result = Image.alpha_composite(result, overlay)
    return result.convert('RGB')

def watermark_content(img):
    """Full-width bottom bar — medium opacity (40-65%)."""
    w, h = img.size
    overlay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    base_size = min(w, h)
    font_brand = get_font(int(base_size * 0.04), bold=True)
    font_sub = get_font(int(base_size * 0.018))

    bar_h = int(base_size * 0.09)
    bar_y = h - bar_h
    draw.rectangle([(0, bar_y), (w, h)], fill=(*COLOR_DARK, int(255 * 0.65)))
    draw.line([(0, bar_y), (w, bar_y)], fill=(*COLOR_HONEY, int(255 * 0.3)), width=1)

    pad = int(base_size * 0.025)
    hl_size = int(base_size * 0.055)
    font_hl = get_font(hl_size, bold=True)
    draw.text((pad, bar_y + (bar_h - hl_size) // 2), BRAND_SHORT, fill=(*COLOR_HONEY, int(255 * 0.8)), font=font_hl)
    haus_bbox = draw.textbbox((0, 0), BRAND_NAME, font=font_brand)
    haus_h = haus_bbox[3] - haus_bbox[1]
    x_text = pad + hl_size + pad
    draw.text((x_text, bar_y + (bar_h - haus_h - font_sub.size - 2) // 2), BRAND_NAME, fill=(*COLOR_HONEY, int(255 * 0.7)), font=font_brand)

    result = img.convert('RGBA')
    result = Image.alpha_composite(result, overlay)
    return result.convert('RGB')

def watermark_reel(img):
    """Top-left badge — for Reels and Stories."""
    w, h = img.size
    overlay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    base_size = min(w, h)

    badge_w = int(base_size * 0.22)
    badge_h = int(base_size * 0.065)
    pad = int(base_size * 0.025)
    corner_r = int(base_size * 0.012)

    draw.rounded_rectangle([(pad, pad), (pad + badge_w, pad + badge_h)], radius=corner_r, fill=(*COLOR_DARK, int(255 * 0.7)))
    draw.rounded_rectangle([(pad, pad), (pad + badge_w, pad + badge_h)], radius=corner_r, outline=(*COLOR_HONEY, int(255 * 0.3)), width=1)

    font_hl = get_font(int(base_size * 0.035), bold=True)
    hl_x = pad + int(badge_h * 0.25)
    draw.text((hl_x, pad + int(badge_h * 0.15)), BRAND_SHORT, fill=(*COLOR_HONEY, int(255 * 0.9)), font=font_hl)
    font_h = get_font(int(base_size * 0.016), bold=True)
    font_l = get_font(int(base_size * 0.01))
    text_x = hl_x + int(base_size * 0.04)
    draw.text((text_x, pad + int(badge_h * 0.12)), BRAND_WORD1, fill=(*COLOR_HONEY, int(255 * 0.8)), font=font_h)
    draw.text((text_x, pad + int(badge_h * 0.52)), BRAND_WORD2, fill=(*COLOR_HONEY, int(255 * 0.55)), font=font_l)

    result = img.convert('RGBA')
    result = Image.alpha_composite(result, overlay)
    return result.convert('RGB')

def process_image(input_path, wm_type, output_path=None):
    img = Image.open(input_path)
    funcs = {'catalog': watermark_catalog, 'content': watermark_content, 'reel': watermark_reel}
    if wm_type not in funcs:
        print(f"Unknown type: {wm_type}"); return
    result = funcs[wm_type](img)
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}-wm-{wm_type}{ext}"
    result.save(output_path, quality=95)
    print(f"✅ {os.path.basename(input_path)} → {os.path.basename(output_path)}")

def batch_process(input_folder, wm_type, output_folder=None):
    if output_folder is None:
        output_folder = os.path.join(input_folder, f"watermarked-{wm_type}")
    os.makedirs(output_folder, exist_ok=True)
    exts = ('.jpg', '.jpeg', '.png', '.webp')
    files = [f for f in os.listdir(input_folder) if f.lower().endswith(exts)]
    if not files:
        print(f"No images found in {input_folder}"); return
    print(f"Processing {len(files)} images with '{wm_type}' watermark...")
    for f in files:
        process_image(os.path.join(input_folder, f), wm_type, os.path.join(output_folder, f))
    print(f"\n✅ Done! {len(files)} images → {output_folder}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Brand Watermark Tool')
    parser.add_argument('input', help='Input image path or folder')
    parser.add_argument('--type', '-t', default='catalog', choices=['catalog', 'content', 'reel'])
    parser.add_argument('--output', '-o', help='Output path/folder')
    parser.add_argument('--batch', '-b', action='store_true', help='Batch process folder')
    args = parser.parse_args()
    if args.batch:
        batch_process(args.input, args.type, args.output)
    else:
        process_image(args.input, args.type, args.output)
