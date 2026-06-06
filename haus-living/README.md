# @haus_living1 — Furniture Mockup Images

Instagram furniture account mockup image generation.

## Files

- `generate_mockups.py` — Main script to generate all 6 mockup images
- `mockups/` — Output directory for generated images

## Generated Images (6 total)

| # | Filename | Description |
|---|----------|-------------|
| 1 | `sofa-living-room.png` | L-shape sofa, warm living room, dark charcoal wall |
| 2 | `dining-set-warm.png` | 6-seater dining set, warm wood, pendant lighting |
| 3 | `bedroom-cozy.png` | Low-profile bed, walnut, white linen, throw blanket |
| 4 | `tv-unit-floating.png` | Floating TV unit, oak, LED strip lighting |
| 5 | `desk-wfh-setup.png` | WFH desk 120cm, laptop + monitor, task lamp |
| 6 | `reading-nook.png` | Accent armchair, floor lamp, hygge vibe |

All images: **4:5 portrait** aspect ratio, **Instagram feed** optimized.

## How to Generate

```bash
cd ~/.hermes/haus-living
python3 generate_mockups.py
```

Requires one of these API keys in `~/.hermes/.env`:
- `FAL_KEY` (preferred — FLUX/dev, best quality/cost)
- `OPENAI_API_KEY` (gpt-image-1 or dall-e-3)
- `XAI_API_KEY` (grok-2-image)

## Style Notes

All prompts follow the @haus_living1 brand aesthetic:
- Modern minimalist furniture
- Warm wood tones (oak, walnut)
- Dark charcoal backgrounds
- Warm ambient lighting
- Green plant accents
- Catalog/magazine quality photography
