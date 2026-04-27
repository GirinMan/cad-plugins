---
name: cad-render
description: Render CAD data into readable visual previews. Use when the user asks to make, remake, fix, or compare CAD images/previews from DXF or normalized CAD JSON, including PNG/SVG/HTML output, clipped views, text-free linework views, block-only views, label views, layer-specific views, or Windows/macOS-compatible CAD rendering workflows.
---

# CAD Render

## Purpose

Render CAD as purpose-specific views, not as one overloaded screenshot. Use this after `$cad-convert` has produced a canonical DXF and after a parser/quicklook step has produced normalized JSON when possible.

## Workflow

1. Preserve source CAD and existing normalized JSON.
2. Prefer a project-local renderer if present, such as `python -m cad_parser.visualize`.
3. If no project renderer exists, use `scripts/render_cad_json.py` on normalized CAD JSON.
4. Choose the view based on the user's goal:
   - `full`: diagnostic extent view; useful for outliers but often unreadable
   - `clipped`: remove coordinate outliers for a readable overview
   - `linework`: hide labels and blocks; best default for dense CAD
   - `blocks`: show symbols/blocks without text
   - `labels`: show text labels when label count is manageable
   - `layer`: render only a selected layer or layer substring
5. Open or inspect the generated image before claiming it is useful.
6. If the image is blank or tiny, check coordinate outliers and regenerate with clipping.
7. If the image is black or cluttered, turn off text and/or blocks.

## Commands

Project-local renderer example:

```bash
python -m cad_parser.visualize data/processed/example_analysis.json \
  --png-out data/processed/example_linework.png \
  --width 2400 \
  --height 1800 \
  --clip-percentile 0.01 \
  --no-text \
  --no-blocks
```

Bundled fallback renderer:

```bash
python skills/cad-render/scripts/render_cad_json.py data/processed/example_analysis.json \
  --out data/processed/example_linework.png \
  --view linework \
  --clip-percentile 0.01
```

Layer-focused fallback:

```bash
python skills/cad-render/scripts/render_cad_json.py data/processed/example_analysis.json \
  --out data/processed/layer_map_house.png \
  --view layer \
  --layer MAP-HOUSE \
  --clip-percentile 0.01
```

## Defaults

- Use PNG for large files; huge SVG/HTML can be slow or unreadable.
- Use `linework` plus `clip-percentile 0.01` as the default for dense DWG conversions.
- Use `full` only to diagnose why a drawing appears blank.
- Use labels only for label-focused tasks or small drawings.
- Generate multiple small purposeful views rather than one visually overloaded image.

## Output Contract

Report:

- image path
- view type
- clipping used
- whether text and blocks were included
- what you saw when opening/checking the image
- recommended next render if the current one is still cluttered
