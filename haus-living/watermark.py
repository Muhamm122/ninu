#!/usr/bin/env python3
"""
Haus Living Watermark Tool v2
Adds watermark to product photos for IG content and catalog.
Supports dark/light variants, SVG-based watermarks via CairoSVG.

Usage:
  python3 watermark.py <input_image> [--type catalog|content|reel] [--variant dark|light] [--output output.png]
  python3 watermark.py batch <input_folder> [--type catalog|content|reel] [--variant dark|light] [--output output_folder/]

Types:
  catalog  — Bottom-right corner stamp, very subtle (opacity 15%)
  content  — Bottom-left horizontal bar, medium opacity (opacity 40%)
  reel     — Top-left badge overlay for stories/reels

Variants:
  dark     — Honey gold on dark (for light/bright photos)
  light    — Terracotta on light (for dark photos)
"""

import os
import sys
import argparse
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

BRAND = "HAUS LIVING"
COLOR_HONEY = (212, 165, 116)   # #D4A574
COLOR_DARK = (26, 26, 26)       # #1A1A1A
COLOR_TERRACOTTA = (196, 115, 91)  # #C4735B
COLOR_LIGHT_BG = (250, 247, 242)   # #FAF7F2

# Variant color maps
VARIANT_COLORS = {
    "dark": {
        "primary": COLOR_HONEY,
        "secondary": COLOR_HONEY,
        "bg": COLOR_DARK,
        "text": COLOR_HONEY,
    },
    "light": {
        "primary": COLOR_TERRACOTTA,
        "secondary": COLOR_TERRACOTTA,
        "bg": COLOR_LIGHT_BG,
        "text": COLOR_DARK,
    },
}

def get_font(size, bold=False):
    """Try to load a nice serif font, fallback to default."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            return ImageFont.truetype(fp, size)
    return ImageFont.load_default()

def watermark_catalog(img, variant="dark"):
    """Subtle corner stamp — bottom-right, very low opacity."""
    colors = VARIANT_COLORS.get(variant, VARIANT_COLORS["dark"])
    w, h = img.size
    overlay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    base_size = min(w, h)
    font_main = get_font(int(base_size * 0.035), bold=True)
    font_sub = get_font(int(base_size * 0.02))
    font_hl = get_font(int(base_size * 0.065), bold=True)

    hl_text = "HL"
    haus_text = "HAUS"
    liv_text = "LIVING"

    hl_bbox = draw.textbbox((0, 0), hl_text, font=font_hl)
    hl_w = hl_bbox[2] - hl_bbox[0]
    hl_h = hl_bbox[3] - hl_bbox[1]

    haus_bbox = draw.textbbox((0, 0), haus_text, font=font_main)
    haus_w = haus_bbox[2] - haus_bbox[0]
    haus_h = haus_bbox[3] - haus_bbox[1]

    liv_bbox = draw.textbbox((0, 0), liv_text, font=font_sub)
    liv_w = liv_bbox[2] - liv_bbox[0]
    liv_h = liv_bbox[3] - liv_bbox[1]

    total_w = hl_w + 20 + max(haus_w, liv_w)
    total_h = max(hl_h, haus_h + liv_h + 5)

    pad = int(base_size * 0.04)
    x_start = w - total_w - pad
    y_start = h - total_h - pad

    opacity_main = int(255 * 0.15)
    opacity_sub = int(255 * 0.10)
    primary = colors["primary"]

    draw.text((x_start, y_start), hl_text, fill=(*primary, opacity_main), font=font_hl)

    x_right = x_start + hl_w + 20
    draw.text((x_right, y_start), haus_text, fill=(*primary, opacity_main), font=font_main)
    draw.text((x_right, y_start + haus_h + 5), liv_text, fill=(*primary, opacity_sub), font=font_sub)

    div_x = x_start + hl_w + 10
    draw.line([(div_x, y_start + 5), (div_x, y_start + total_h - 5)],
              fill=(*primary, int(255 * 0.08)), width=1)

    result = img.convert('RGBA')
    result = Image.alpha_composite(result, overlay)
    return result.convert('RGB')

def watermark_content(img, variant="dark"):
    """Medium bar — bottom-left, good visibility for IG posts."""
    colors = VARIANT_COLORS.get(variant, VARIANT_COLORS["dark"])
    primary = colors["primary"]
    bg = colors["bg"]
    w, h = img.size
    overlay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    base_size = min(w, h)
    font_brand = get_font(int(base_size * 0.04), bold=True)
    font_sub = get_font(int(base_size * 0.018))

    bar_h = int(base_size * 0.09)
    bar_y = h - bar_h

    # Semi-transparent bar
    draw.rectangle([(0, bar_y), (w, h)], fill=(*bg, int(255 * 0.65)))

    # Top edge accent line
    draw.line([(0, bar_y), (w, bar_y)], fill=(*primary, int(255 * 0.3)), width=1)

    # HL monogram
    pad = int(base_size * 0.025)
    hl_size = int(base_size * 0.055)
    font_hl = get_font(hl_size, bold=True)
    draw.text((pad, bar_y + (bar_h - hl_size) // 2), "HL",
              fill=(*primary, int(255 * 0.8)), font=font_hl)

    # Brand text
    haus_bbox = draw.textbbox((0, 0), "HAUS", font=font_brand)
    haus_h = haus_bbox[3] - haus_bbox[1]
    x_text = pad + hl_size + pad

    draw.text((x_text, bar_y + (bar_h - haus_h - font_sub.size - 2) // 2),
              "HAUS LIVING", fill=(*primary, int(255 * 0.7)), font=font_brand)

    # Small house icon
    house_x = x_text + 10
    house_y = bar_y + bar_h - font_sub.size - pad
    draw.text((house_x, house_y), "🏠", fill=(*primary, int(255 * 0.4)), font=font_sub)

    result = img.convert('RGBA')
    result = Image.alpha_composite(result, overlay)
    return result.convert('RGB')

def watermark_reel(img, variant="dark"):
    """Top-left badge — for Reels and Stories."""
    colors = VARIANT_COLORS.get(variant, VARIANT_COLORS["dark"])
    primary = colors["primary"]
    bg = colors["bg"]
    text = colors["text"]
    w, h = img.size
    overlay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    base_size = min(w, h)

    badge_w = int(base_size * 0.22)
    badge_h = int(base_size * 0.065)
    pad = int(base_size * 0.025)
    corner_r = int(base_size * 0.012)

    draw.rounded_rectangle(
        [(pad, pad), (pad + badge_w, pad + badge_h)],
        radius=corner_r,
        fill=(*bg, int(255 * 0.7))
    )
    draw.rounded_rectangle(
        [(pad, pad), (pad + badge_w, pad + badge_h)],
        radius=corner_r,
        outline=(*primary, int(255 * 0.3)),
        width=1
    )

    font_hl = get_font(int(base_size * 0.035), bold=True)
    hl_x = pad + int(badge_h * 0.25)
    draw.text((hl_x, pad + int(badge_h * 0.15)), "HL",
              fill=(*text, int(255 * 0.9)), font=font_hl)

    font_h = get_font(int(base_size * 0.016), bold=True)
    font_l = get_font(int(base_size * 0.01))
    text_x = hl_x + int(base_size * 0.04)
    draw.text((text_x, pad + int(badge_h * 0.12)), "HAUS",
              fill=(*text, int(255 * 0.8)), font=font_h)
    draw.text((text_x, pad + int(badge_h * 0.52)), "LIVING",
              fill=(*text, int(255 * 0.55)), font=font_l)

    result = img.convert('RGBA')
    result = Image.alpha_composite(result, overlay)
    return result.convert('RGB')

def process_image(input_path, wm_type, output_path=None, variant="dark"):
    """Process a single image with watermark."""
    img = Image.open(input_path)

    if wm_type == 'catalog':
        result = watermark_catalog(img, variant=variant)
    elif wm_type == 'content':
        result = watermark_content(img, variant=variant)
    elif wm_type == 'reel':
        result = watermark_reel(img, variant=variant)
    else:
        print(f"Unknown type: {wm_type}")
        return

    if output_path is None:
        base, ext = os.path.splitext(input_path)
        vtag = f"-{variant}" if variant != "dark" else ""
        output_path = f"{base}-wm-{wm_type}{vtag}{ext}"

    result.save(output_path, quality=95)
    print(f"✅ {os.path.basename(input_path)} → {os.path.basename(output_path)}")
    return output_path

def batch_process(input_folder, wm_type, output_folder=None, variant="dark"):
    """Process all images in a folder."""
    if output_folder is None:
        vtag = f"-{variant}" if variant != "dark" else ""
        output_folder = os.path.join(input_folder, f"watermarked-{wm_type}{vtag}")
    os.makedirs(output_folder, exist_ok=True)

    extensions = ('.jpg', '.jpeg', '.png', '.webp')
    files = [f for f in os.listdir(input_folder) if f.lower().endswith(extensions)]

    if not files:
        print(f"No images found in {input_folder}")
        return

    print(f"Processing {len(files)} images with '{wm_type}' watermark (variant: {variant})...")
    for f in files:
        input_path = os.path.join(input_folder, f)
        output_path = os.path.join(output_folder, f)
        process_image(input_path, wm_type, output_path, variant=variant)

    print(f"\n✅ Done! {len(files)} images → {output_folder}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Haus Living Watermark Tool v2')
    parser.add_argument('input', help='Input image path or "batch <folder>"')
    parser.add_argument('--type', '-t', default='catalog', choices=['catalog', 'content', 'reel'],
                       help='Watermark type (default: catalog)')
    parser.add_argument('--variant', '-V', default='dark', choices=['dark', 'light'],
                       help='Color variant: dark=honey on dark, light=terracotta on light (default: dark)')
    parser.add_argument('--output', '-o', help='Output path/folder')
    parser.add_argument('--batch', '-b', action='store_true', help='Batch process folder')

    args = parser.parse_args()

    if args.batch:
        batch_process(args.input, args.type, args.output, variant=args.variant)
    else:
        process_image(args.input, args.type, args.output, variant=args.variant)
