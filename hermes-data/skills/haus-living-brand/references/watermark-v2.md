# Watermark v2 — Dark & Light Variants

## System
- Script: `~/.hermes/haus-living/watermark.py`
- Generator: `~/.hermes/haus-living/generate_watermarks_v2.py`
- Samples: `~/.hermes/haus-living/logo/watermark-samples/`

## 3 Types × 2 Variants

| Type | Style | Opacity | Best For |
|------|-------|---------|----------|
| `catalog` | Corner stamp (bottom-right) | 15% | Product catalog |
| `content` | Bottom bar | 40% | IG feed posts |
| `reel` | Top-left badge | 70% | Reels & Stories |

| Variant | Primary | Background | For |
|---------|---------|------------|-----|
| `dark` | `#D4A574` Honey | `#1A1A1A` Dark | Bright photos |
| `light` | `#C4735B` Terracotta | `#FAF7F2` Cream | Dark photos |

## Usage
```bash
# Single photo
python3 ~/.hermes/haus-living/watermark.py foto.jpg --type content --variant light

# Batch folder
python3 ~/.hermes/haus-living/watermark.py batch ~/foto-produk/ --type catalog --variant dark
```

## Demo Output
Available at: `http://18.143.107.30/demo/wm-samples/`
