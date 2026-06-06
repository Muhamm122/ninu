#!/usr/bin/env python3
"""
Haus Living — Watermark Generator v2
Generates SVG + PNG watermarks from logo, with dark/light variants.
Usage:
  python3 generate_watermarks_v2.py              # Generate all
  python3 generate_watermarks_v2.py --variant light  # Light only
  python3 generate_watermarks_v2.py --variant dark   # Dark only
"""

import os
import sys
import subprocess
from pathlib import Path

LOGO_DIR = Path.home() / ".hermes/haus-living/logo"
OUTPUT_DIR = LOGO_DIR / "watermarks-v2"
INKSCAPE = "/usr/bin/inkscape"

# Brand colors
DARK_BG = "#1A1A1C"
LIGHT_BG = "#FAF7F2"
HONEY = "#D4A574"
HONEY_DARK = "#C4735B"
TERRACOTTA = "#C4735B"

SIZES = {
    "lg": 1080,
    "md": 720,
    "sm": 400,
    "thumb": 200,
}

OPACITY = {
    "corner": 0.15,
    "bar": 0.40,
    "badge": 0.70,
    "center": 0.12,
    "stripe": 0.07,
}

VARIANTS = ["dark", "light"]


def check_inkscape():
    if not os.path.exists(INKSCAPE):
        print("⚠️  Inkscape not found, trying convert/ImageMagick fallback...")
        for cmd in ["convert", "magick"]:
            r = subprocess.run(f"which {cmd}", shell=True, capture_output=True)
            if r.returncode == 0:
                return cmd
        print("❌ No SVG-to-PNG converter found. Install inkscape:")
        print("   sudo apt install inkscape")
        return None
    return "inkscape"


def get_logo_svg(variant="dark"):
    """Generate pure logo SVG (no bg) for watermark use."""
    if variant == "light":
        hl_color = "none"
        hl_stroke = TERRACOTTA
        text_color = DARK_BG
        living_color = DARK_BG
        divider_color = TERRACOTTA
    else:
        hl_color = "none"
        hl_stroke = HONEY
        text_color = HONEY
        living_color = HONEY
        divider_color = HONEY

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 200" width="600" height="200">
  <!-- H -->'
  <text x="60" y="130" text-anchor="middle" font-family="Georgia, serif" font-size="140" font-weight="bold" fill="{hl_color}" stroke="{hl_stroke}" stroke-width="3" letter-spacing="-5">H</text>
  <!-- L -->
  <text x="170" y="130" text-anchor="middle" font-family="Georgia, serif" font-size="140" font-weight="bold" fill="{hl_color}" stroke="{hl_stroke}" stroke-width="3" letter-spacing="-5">L</text>
  <!-- Divider -->
  <line x1="210" y1="100" x2="260" y2="100" stroke="{divider_color}" stroke-width="1.5" opacity="0.6"/>
  <text x="280" y="115" font-family="Georgia, serif" font-size="32" letter-spacing="8" fill="{text_color}" font-weight="600">HAUS</text>
  <line x1="430" y1="100" x2="450" y2="100" stroke="{divider_color}" stroke-width="1.5" opacity="0.6"/>
  <text x="470" y="115" font-family="Georgia, serif" font-size="20" letter-spacing="10" fill="{living_color}" opacity="0.7">LIVING</text>
</svg>'''


def generate_horizontal_watermark(variant, size_name, output_dir):
    """Horizontal bar watermark (top or bottom of image)."""
    w = SIZES[size_name]
    op = OPACITY["bar"]
    logo_svg = get_logo_svg(variant)

    bg_rect = ""
    variant_label = "dark" if variant == "dark" else "light"

    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {w//6}" width="{w}" height="{w//6}">
  {logo_svg.replace('viewBox="0 0 600 200"', f'viewBox="0 0 600 200" width="{w}" height="{w//6}" preserveAspectRatio="xMidYMid meet"').replace('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 200" width="600" height="200">', '')}
</svg>'''

    # Simplified — just save the logo at correct size
    svg_path = output_dir / f"wm-bar-{variant_label}-{size_name}.svg"
    # We'll create a bar by scaling the logo
    bar_h = max(w // 6, 80)
    bar_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {bar_h}" width="{w}" height="{bar_h}" opacity="{op}">
  <g transform="translate({w//2 - 300}, {bar_h//2 - 100})">
    {get_inner_logo_svg(variant)}
  </g>
</svg>'''

    svg_path.write_text(bar_svg)

    # Generate stamp variation (small centered logo)
    stamp_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {bar_h} {bar_h}" width="{bar_h}" height="{bar_h}" opacity="{op}">
  <g transform="translate({bar_h//2 - 300}, {bar_h//2 - 100})">
    {get_inner_logo_svg(variant)}
  </g>
</svg>'''

    stamp_path = output_dir / f"wm-stamp-{variant_label}-{size_name}.svg"
    stamp_path.write_text(stamp_svg)

    return svg_path, stamp_path


def get_inner_logo_svg(variant="dark"):
    """Inner logo SVG without outer svg tag."""
    if variant == "light":
        hl_stroke = TERRACOTTA
        text_color = DARK_BG
    else:
        hl_stroke = HONEY
        text_color = HONEY

    return f'''<text x="60" y="130" text-anchor="middle" font-family="Georgia, serif" font-size="140" font-weight="bold" fill="none" stroke="{hl_stroke}" stroke-width="3" letter-spacing="-5">H</text>
    <text x="170" y="130" text-anchor="middle" font-family="Georgia, serif" font-size="140" font-weight="bold" fill="none" stroke="{hl_stroke}" stroke-width="3" letter-spacing="-5">L</text>
    <line x1="210" y1="100" x2="260" y2="100" stroke="{HONEY}" stroke-width="1.5" opacity="0.6"/>
    <text x="280" y="115" font-family="Georgia, serif" font-size="32" letter-spacing="8" fill="{text_color}" font-weight="600">HAUS</text>
    <line x1="430" y1="100" x2="450" y2="100" stroke="{HONEY}" stroke-width="1.5" opacity="0.6"/>
    <text x="470" y="115" font-family="Georgia, serif" font-size="20" letter-spacing="10" opacity="0.7">LIVING</text>'''


def generate_corner_watermark(variant, size_name, output_dir, corner="bottom-right"):
    """Corner watermark — small logo in corner."""
    w = SIZES[size_name]
    op = OPACITY["corner"]
    logo_w = w // 3
    logo_h = logo_w // 3

    if "right" in corner:
        x = w - logo_w - 20
    else:
        x = 20

    if "bottom" in corner:
        y = w - logo_h - 20
    else:
        y = 20

    inner = get_inner_logo_svg(variant)
    variant_label = "dark" if variant == "dark" else "light"
    suffix = corner.replace("-", "")

    svg_path = output_dir / f"wm-{suffix}-{variant_label}-{size_name}.svg"
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {logo_w} {logo_h}" width="{logo_w}" height="{logo_h}" opacity="{op}">
  <g transform="translate(0, 0)">
    {inner}
  </g>
</svg>'''
    svg_path.write_text(svg_content)
    return svg_path


def generate_stripe_watermark(variant, size_name, output_dir):
    """Diagonal stripe watermark — anti-theft."""
    w = SIZES[size_name]
    op = OPACITY["stripe"]
    inner = get_inner_logo_svg(variant)
    variant_label = "dark" if variant == "dark" else "light"

    svg_path = output_dir / f"wm-stripe-{variant_label}-{size_name}.svg"
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {int(w*1.4)} {int(w*1.4)}" width="{int(w*1.4)}" height="{int(w*1.4)}" opacity="{op}">
  <g transform="rotate(-30, {w//2}, {w//2}) translate({w//4}, {w//4})">
    {inner}
  </g>
</svg>'''
    svg_path.write_text(svg_content)
    return svg_path


def generate_center_watermark(variant, size_name, output_dir):
    """Center watermark — large, faint."""
    w = SIZES[size_name]
    op = OPACITY["center"]
    inner = get_inner_logo_svg(variant)
    variant_label = "dark" if variant == "dark" else "light"

    svg_path = output_dir / f"wm-center-{variant_label}-{size_name}.svg"
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {w}" width="{w}" height="{w}" opacity="{op}">
  <g transform="translate({w//2 - 300}, {w//2 - 100})">
    {inner}
  </g>
</svg>'''
    svg_path.write_text(svg_content)
    return svg_path


def generate_badge_watermark(variant, size_name, output_dir):
    """Badge watermark — framed logo, for reels/thumbnails."""
    w = SIZES[size_name]
    op = OPACITY["badge"]
    inner = get_inner_logo_svg(variant)
    variant_label = "dark" if variant == "dark" else "light"

    pad = 15
    badge_w = 320 + pad * 2
    badge_h = 120 + pad * 2

    svg_path = output_dir / f"wm-badge-{variant_label}-{size_name}.svg"
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {badge_w} {badge_h}" width="{badge_w}" height="{badge_h}" opacity="{op}">
  <rect x="0" y="0" width="{badge_w}" height="{badge_h}" rx="8" fill="none" stroke="{HONEY if variant == 'dark' else TERRACOTTA}" stroke-width="1" opacity="0.5"/>
  <g transform="translate({pad + 50}, {pad + 30}) scale(0.5)">
    {inner}
  </g>
</svg>'''
    svg_path.write_text(svg_content)
    return svg_path


def render_svg_to_png(svg_path, png_path, converter, size=None):
    """Render SVG to PNG using available converter."""
    if converter == "inkscape":
        cmd = f'{INKSCAPE} --export-filename="{png_path}" --export-width={size or SIZES.get("lg", 1080)} "{svg_path}" 2>/dev/null'
    elif converter == "convert":
        cmd = f'convert -background none -density 300 -resize {size or 1080}x "{svg_path}" "{png_path}" 2>/dev/null'
    elif converter == "magick":
        cmd = f'magick -background none -density 300 -resize {size or 1080}x "{svg_path}" "{png_path}" 2>/dev/null'
    else:
        return False

    r = subprocess.run(cmd, shell=True, capture_output=True, timeout=30)
    return r.returncode == 0


def render_cairo(svg_path, png_path, size):
    """Fallback: render SVG to PNG using CairoSVG."""
    try:
        import cairosvg
        cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), output_width=size, output_height=size)
        return True
    except ImportError:
        return False


def main():
    variant_filter = None
    if "--variant" in sys.argv:
        idx = sys.argv.index("--variant")
        if idx + 1 < len(sys.argv):
            variant_filter = sys.argv[idx + 1]

    variants = [variant_filter] if variant_filter else VARIANTS

    output_dir = OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check converter
    converter = check_inkscape()
    if not converter:
        print("❌ Cannot generate PNGs without inkscape or ImageMagick.")
        print("   SVG files will still be generated.")
        converter = None
    else:
        print(f"  Using converter: {converter}")

    total = 0
    for variant in variants:
        print(f"\n{'='*50}")
        print(f"  Variant: {variant.upper()}")
        print(f"{'='*50}")

        for size_name in SIZES:
            size_val = SIZES[size_name]

            # Generate SVGs
            files = []
            files.append(generate_corner_watermark(variant, size_name, output_dir))
            files.append(generate_center_watermark(variant, size_name, output_dir))
            files.append(generate_badge_watermark(variant, size_name, output_dir))
            files.append(generate_stripe_watermark(variant, size_name, output_dir))
            bar, stamp = generate_horizontal_watermark(variant, size_name, output_dir)
            files.extend([bar, stamp])

            # Render to PNGs
            if converter:
                for svg_path in files:
                    png_path = svg_path.with_suffix('.png')
                    if render_svg_to_png(svg_path, png_path, converter, size_val):
                        total += 1
                    elif render_cairo(svg_path, png_path, size_val):
                        total += 1
                    else:
                        print(f"  ⚠️  Failed to render: {svg_path.name}")

            total += len(files)

    print(f"\n{'='*50}")
    print(f"  ✅ Generated {total} files")
    print(f"  📁 Output: {output_dir}")
    print(f"{'='*50}")
    print(f"\nUsage with watermark.py:")
    print(f"  python3 ~/.hermes/haus-living/w watermark.py batch ~/photos/ --type watermark-v2")


if __name__ == "__main__":
    main()
