#!/usr/bin/env python3
"""
Generate Haus Living watermark logos — transparent PNG overlays.
Output: multiple sizes for different use cases (IG profile, product photo, reel, catalog).
"""
from PIL import Image, ImageDraw, ImageFont
import os

OUTPUT_DIR = os.path.expanduser("~/.hermes/haus-living/logo/watermarks")
os.makedirs(OUTPUT_DIR, exist_ok=True)

COLOR_HONEY = (212, 165, 116, 255)  # #D4A574

def get_font(size, bold=False):
    paths = []
    if bold:
        paths.append("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf")
        paths.append("/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf")
    else:
        paths.append("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf")
        paths.append("/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf")
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def create_corner_watermark(size=1080, opacity=0.20):
    """Bottom-right corner — for product catalog photos."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    s = size
    # Scale
    font_hl = get_font(int(s * 0.055), bold=True)
    font_brand = get_font(int(s * 0.028), bold=True)  
    font_sub = get_font(int(s * 0.016))
    
    pad = int(s * 0.035)
    
    # Calculate text widths
    hl_bbox = draw.textbbox((0,0), "HL", font=font_hl)
    hl_w = hl_bbox[2] - hl_bbox[0]
    hl_h = hl_bbox[3] - hl_bbox[1]
    
    brand_bbox = draw.textbbox((0,0), "HAUS LIVING", font=font_brand)
    brand_w = brand_bbox[2] - brand_bbox[0]
    brand_h = brand_bbox[3] - brand_bbox[1]
    
    tag_bbox = draw.textbbox((0,0), "handcrafted furniture", font=font_sub)
    tag_w = tag_bbox[2] - tag_bbox[0]
    tag_h = tag_bbox[3] - tag_bbox[1]
    
    total_w = max(hl_w + 15 + brand_w, hl_w + 15 + tag_w)
    total_h = hl_h + tag_h + 8
    
    # Position: bottom-right
    x0 = size - total_w - pad
    y0 = size - total_h - pad
    
    a_main = int(255 * opacity)
    a_sub = int(255 * (opacity * 0.6))
    
    # HL monogram
    draw.text((x0, y0), "HL", fill=(*COLOR_HONEY[:3], a_main), font=font_hl)
    
    # Vertical divider
    div_x = x0 + hl_w + 7
    draw.line([(div_x, y0 + 3), (div_x, y0 + total_h - 3)], 
              fill=(*COLOR_HONEY[:3], int(a_main * 0.5)), width=1)
    
    # HAUS LIVING
    text_x = x0 + hl_w + 15
    draw.text((text_x, y0), "HAUS LIVING", fill=(*COLOR_HONEY[:3], a_main), font=font_brand)
    
    # Tagline
    draw.text((text_x, y0 + brand_h + 4), "handcrafted furniture", 
              fill=(*COLOR_HONEY[:3], a_sub), font=font_sub)
    
    return img

def create_bar_watermark(size=1080, opacity=0.85):
    """Bottom bar — for IG feed posts."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    s = size
    bar_h = int(s * 0.085)
    bar_y = size - bar_h
    
    # Gradient-like dark bar
    for i in range(bar_h):
        row_y = bar_y + i
        # Fade from transparent to semi-opaque
        progress = i / bar_h
        alpha = int(255 * opacity * (0.3 + 0.7 * progress))
        draw.line([(0, row_y), (size, row_y)], fill=(26, 26, 26, alpha))
    
    # Top accent line
    draw.line([(0, bar_y), (size, bar_y)], fill=(*COLOR_HONEY[:3], int(255 * 0.35)), width=2)
    
    # Content inside bar
    pad_inner = int(s * 0.03)
    font_hl = get_font(int(s * 0.05), bold=True)
    font_brand = get_font(int(s * 0.025), bold=True)
    font_tag = get_font(int(s * 0.014))
    
    # HL on left
    draw.text((pad_inner, bar_y + (bar_h - int(s*0.05)) // 2), "HL",
              fill=(*COLOR_HONEY[:3], int(255 * 0.9)), font=font_hl)
    
    # Brand name next to HL
    x_text = pad_inner + int(s * 0.065)
    draw.text((x_text, bar_y + bar_h // 2 - int(s * 0.02)), "HAUS LIVING",
              fill=(*COLOR_HONEY[:3], int(255 * 0.8)), font=font_brand)
    
    # Small tag right side
    tag_text = "@haus_living1"
    tag_bbox = draw.textbbox((0,0), tag_text, font=font_tag)
    tag_w = tag_bbox[2] - tag_bbox[0]
    draw.text((size - tag_w - pad_inner, bar_y + bar_h // 2 - int(s * 0.008)), 
              tag_text, fill=(*COLOR_HONEY[:3], int(255 * 0.45)), font=font_tag)
    
    return img

def create_badge_watermark(size=1080, opacity=0.85):
    """Top-left badge — for Reels & Stories."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    s = size
    badge_w = int(s * 0.215)
    badge_h = int(s * 0.065)
    pad = int(s * 0.025)
    radius = int(s * 0.012)
    
    # Badge background
    draw.rounded_rectangle(
        [(pad, pad), (pad + badge_w, pad + badge_h)],
        radius=radius, fill=(15, 15, 15, int(255 * 0.75))
    )
    # Badge border
    draw.rounded_rectangle(
        [(pad, pad), (pad + badge_w, pad + badge_h)],
        radius=radius, outline=(*COLOR_HONEY[:3], int(255 * 0.3)), width=1
    )
    
    # HL
    font_hl = get_font(int(s * 0.032), bold=True)
    hl_x = pad + int(badge_h * 0.22)
    draw.text((hl_x, pad + int(badge_h * 0.12)), "HL",
              fill=(*COLOR_HONEY[:3], int(255 * 0.9)), font=font_hl)
    
    # HAUS / LIVING
    font_h = get_font(int(s * 0.015), bold=True)
    font_l = get_font(int(s * 0.009))
    text_x = hl_x + int(s * 0.038)
    draw.text((text_x, pad + int(badge_h * 0.08)), "HAUS",
              fill=(*COLOR_HONEY[:3], int(255 * 0.8)), font=font_h)
    draw.text((text_x, pad + int(badge_h * 0.5)), "LIVING",
              fill=(*COLOR_HONEY[:3], int(255 * 0.55)), font=font_l)
    
    # Decorative dot
    dot_x = pad + badge_w - int(badge_h * 0.3)
    dot_y = pad + badge_h // 2
    dot_r = int(s * 0.003)
    draw.ellipse([(dot_x - dot_r, dot_y - dot_r), (dot_x + dot_r, dot_y + dot_r)],
                 fill=(*COLOR_HONEY[:3], int(255 * 0.4)))
    
    return img

def create_center_watermark(size=1080, opacity=0.12):
    """Centered large text — very subtle, for full-photo protection."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    s = size
    
    # Large HAUS
    font_main = get_font(int(s * 0.14), bold=True)
    main_bbox = draw.textbbox((0,0), "HAUS", font=font_main)
    main_w = main_bbox[2] - main_bbox[0]
    main_h = main_bbox[3] - main_bbox[1]
    
    a = int(255 * opacity)
    
    x = (size - main_w) // 2
    y = size // 2 - int(s * 0.06)
    draw.text((x, y), "HAUS", fill=(*COLOR_HONEY[:3], a), font=font_main)
    
    # LIVING below
    font_sub = get_font(int(s * 0.06), bold=True)
    sub_bbox = draw.textbbox((0,0), "LIVING", font=font_sub)
    sub_w = sub_bbox[2] - sub_bbox[0]
    x_sub = (size - sub_w) // 2
    draw.text((x_sub, y + main_h + int(s * 0.01)), "LIVING",
              fill=(*COLOR_HONEY[:3], int(a * 0.7)), font=font_sub)
    
    # Decorative line between
    line_w = int(s * 0.15)
    line_x = (size - line_w) // 2
    line_y = y + main_h + int(s * 0.005)
    draw.line([(line_x, line_y), (line_x + line_w, line_y)],
              fill=(*COLOR_HONEY[:3], int(a * 0.5)), width=1)
    
    return img

def create_stripe_watermark(size=1080, opacity=0.06):
    """Diagonal repeating text stripe — maximum copy protection."""
    img = Image.new('RGBA', (size * 2, size * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    font = get_font(int(size * 0.025))
    text = "HAUS LIVING • "
    a = int(255 * opacity)
    
    # Draw repeating text in rows
    y_step = int(size * 0.06)
    x_step = int(size * 0.035)
    
    for row in range(0, size * 2, y_step):
        offset = (x_step * 8) if (row // y_step) % 2 else 0
        x = -offset
        while x < size * 2:
            draw.text((x, row), text, fill=(*COLOR_HONEY[:3], a), font=font)
            x += int(size * 0.25)
    
    # Rotate 30 degrees and crop
    rotated = img.rotate(-30, resample=Image.BICUBIC, expand=False)
    # Crop to original size
    crop_x = (rotated.width - size) // 2
    crop_y = (rotated.height - size) // 2
    cropped = rotated.crop((crop_x, crop_y, crop_x + size, crop_y + size))
    
    return cropped

# ============================================================
# GENERATE ALL WATERMARKS
# ============================================================

print("🏗️  Generating Haus Living Watermarks...\n")

watermarks = {
    "corner": (create_corner_watermark, {"opacity": 0.22}),
    "bar": (create_bar_watermark, {"opacity": 0.85}),
    "badge": (create_badge_watermark, {"opacity": 0.85}),
    "center": (create_center_watermark, {"opacity": 0.12}),
    "stripe": (create_stripe_watermark, {"opacity": 0.07}),
}

sizes = {
    "1080": 1080,  # IG post / Reel
    "720": 720,    # Story
    "400": 400,    # Thumbnail
}

for name, (func, kwargs) in watermarks.items():
    for size_name, size in sizes.items():
        wm = func(size=size, **kwargs)
        fname = f"wm-{name}-{size_name}.png"
        fpath = os.path.join(OUTPUT_DIR, fname)
        wm.save(fpath)
        kb = os.path.getsize(fpath) // 1024
        print(f"  ✅ {fname} ({kb}KB)")

print(f"\n📁 All watermarks saved to: {OUTPUT_DIR}")
