---
name: cad-inspect
description: Inspect specific CAD content after conversion/quicklook. Use when the user asks about a particular CAD layer, label, keyword, block, symbol, coordinate area, facility name, road/pipe/elevation text, or wants focused extraction from normalized DWG/DXF data instead of a broad preview.
---

# CAD Inspect

## Purpose

Answer targeted questions about CAD content. Use this after `$cad-convert` or `$cad-quicklook` has produced a canonical DXF or normalized JSON.

## Workflow

1. Locate the normalized analysis JSON for the CAD file. If none exists, run quicklook or the project parser first.
2. Narrow the target:
   - layer name or prefix
   - text keyword or regex
   - block name
   - coordinate bounding box
   - entity type
3. Extract only the relevant slice.
4. Render a focused preview only for the selected slice or region when useful.
5. Explain findings in plain language: what was found, where it appears, and what confidence/limits apply.

## Avoid

- Do not brute-force all text-to-geometry links for huge files.
- Do not send the entire JSON to an agent when a filtered slice answers the question.
- Do not assume layer codes mean something without local/project dictionaries or repeated evidence.

## Helper Script

Use `scripts/inspect_json.py` for quick layer/text/block searches in normalized JSON:

```bash
python skills/cad-inspect/scripts/inspect_json.py data/processed/example_analysis.json --text pump
python skills/cad-inspect/scripts/inspect_json.py data/processed/example_analysis.json --layer MAP-HOUSE
python skills/cad-inspect/scripts/inspect_json.py data/processed/example_analysis.json --blocks
```

## Output Shape

Return:

- matched count
- top matching layers or block names
- sample records with text, layer, type, and coordinates
- whether a focused render is needed next
