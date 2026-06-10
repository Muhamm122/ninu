# Watermark System v2 — Reference

## Files

| File | Purpose |
|------|---------|
| `watermark.py` | Main watermark apply tool (PIL-based, 3 types × 2 variants) |
| `generate_watermarks_v2.py` | SVG/PNG watermark generator (CairoSVG-based) |

## Watermark Types × Variants

| Type | Style | Opacity | Dark Variant | Light Variant |
|------|-------|---------|--------------|---------------|
| `catalog` | Corner stamp (bottom-right) | 15% | Honey on dark | Terracotta on cream |
| `content` | Bottom bar | 40% | Honey bar | Terracotta bar |
| `reel` | Top-left badge | 70% | Honey badge | Terracotta badge |

## Brand Colors

```
DARK_BG    = #1A1A1C
LIGHT_BG   = #FAF7F2
HONEY      = #D4A574
TERRACOTTA = #C4735B
```

## IG Photo Specs

| Type | Ratio | Resolution |
|------|-------|------------|
| Feed | 4:5 | 1080×1350px |
| Carousel | 4:5 | 1080×1350px |
| Reel | 9:16 | 1080×1920px |
| Story | 9:16 | 1080×1920px |
| Product | 1:1 | 1080×1080px |

## SVG Renderer

CairoSVG works without Inkscape: `pip install cairosvg`

## Usage

```bash
# Single photo
python3 ~/.hermes/haus-living/watermark.py foto.jpg --type content --variant light

# Batch
python3 ~/.hermes/haus-living/watermark.py batch ~/foto/ --type catalog --variant dark
```