# Logo Generation — SVG-First Approach

## Technique

Generate brand logos as **SVG files** (text-based, zero dependencies) using programmatic SVG with brand colors and typography, then convert to PNG via `rsvg-convert`.

### Why SVG-first
- No GPU required (unlike AI image gen)
- No API key required
- Deterministic output — same SVG = same PNG every time
- Editable in any text editor for quick tweaks
- Scales to any resolution without quality loss
- Can be embedded directly in HTML landing pages

### Prerequisites
```bash
# SVG → PNG conversion
sudo apt install librsvg2-bin
# Python SVG → PNG (alternative, for server-side rendering)
pip install cairosvg
# Image processing (for watermark tool)
pip install Pillow
```

### Conversion
```bash
# High-res for IG (1080×1080)
rsvg-convert -w 1080 -h 1080 logo.svg > logo.png

# Thumbnail for previews (320×320)
rsvg-convert -w 320 -h 320 logo.svg > logo-thumb.png
```

## Design System for Dark Modern Brands

| Element | Value | Rationale |
|---------|-------|-----------|
| Background | `#1A1A1C` → `#2C2C2C` linear gradient | Dark charcoal, matches furniture aesthetic |
| Primary accent | `#D4A574` (honey/oak) | Warm wood tone, premium feel |
| Secondary accent | `#C4735B` (terra) | Terracotta, earthy warmth |
| Typography | Georgia / Playfair Display (serif) | Classic furniture/interior branding |
| Monogram font | Bold serif, 2-3x main text | Strong visual anchor |
| Layout | Centered, vertical stack | Works in 1:1 (IG) and adapt to rectangular |

## Logo Variations to Generate

Always provide **3-5 variations** — let user choose:

1. **Icon + Text** — Brand icon (house, sofa, etc.) above stacked text. Most versatile.
2. **Monogram** — Large outline initials (e.g., "HL") with smaller brand name. Premium, works as avatar.
3. **Wordmark** — Pure text, bold primary word + italic/lighter secondary. Cleanest, most scalable.
4. **Geometric** — Abstract geometric letterform (e.g., H made of lines + roof accent). Modern, architectural.
5. **Niche-specific icon** — Furniture: sofa outline. Fashion: hanger. Food: fork+knife.

## File Structure

```
~/.hermes/[brand]/
├── logo/
│   ├── logo-v1-[name].svg    ← Source SVG (editable)
│   ├── logo-v1-[name].png    ← 1080×1080 PNG (IG/crop)
│   ├── logo-v1-[name]-thumb.png  ← 320×320 thumbnail
│   ├── ... (more variations)
│   └── watermark-demo/       ← Sample watermarked images
└── watermark.py              ← Watermark application tool
```

## Session Example (Haus Living, 2026-06-05)

Brand: Haus Living (@haus_living1), dark modern furniture.

Generated 5 variations:
- V1: House icon + HAUS / LIVING stacked text
- V2: HL monogram (outline) + HAUS / LIVING
- V3: Sofa line-drawing icon + brand text
- V4: Pure wordmark — bold "HAUS" + italic "Living"
- V5: Geometric H + roof accent

User selected V4 (wordmark) for profile pic — "clean, luxurious, readable at small scale."

Watermark tool created with 3 types:
- `catalog` — corner stamp at 15% opacity (doesn't obscure product)
- `content` — bottom bar at 65% opacity (clear brand credit)
- `reel` — top-left badge at 70% opacity (visible but compact)
