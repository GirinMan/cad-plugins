---
name: cad-quicklook
description: Quickly identify and summarize CAD files without deep analysis. Use when the user asks to open, preview, summarize, or understand what a DWG/DXF/CAD file is at a high level, especially when they are not a CAD specialist. Produces concise file identity, entity/layer/text/block counts, a small set of readable previews, and a 3-line interpretation.
---

# CAD Quicklook

## Purpose

Give a lightweight first answer before doing expensive CAD interpretation. Prefer enough evidence to orient the user: what the file is, what kinds of data dominate it, what preview is readable, and what a useful next question would be.

## Workflow

1. If the input is DWG, invoke `$cad-convert` first or use the project-local converter to create canonical DXF.
2. Parse/profile the DXF with the project-local parser if present.
3. If no project parser exists, use available CAD tools such as `ezdxf` to count entity types, layers, texts, blocks, and basic geometry.
4. Use `$cad-render` or a project-local renderer to render only a few previews:
   - `full_extent` for outlier detection
   - `clipped_linework` as the default readable view
   - `labels_or_blocks` only if the file is not too dense
5. Report a 3-line summary first.
6. Mention limitations and suggest `cad-inspect` only if the user asks to dig into specific labels, layers, regions, or objects.

## Defaults

- Keep quicklook under a minute for normal files.
- Avoid exhaustive text-to-geometry linking.
- Turn off labels for dense drawings unless the user asks for label review.
- If a full image looks blank, suspect coordinate outliers and make a clipped preview.
- If a drawing has tens of thousands of labels or blocks, say so plainly and keep the visual uncluttered.

## Helper Script

Use `scripts/quicklook_json.py` to summarize an existing normalized CAD JSON file:

```bash
python skills/cad-quicklook/scripts/quicklook_json.py data/processed/example_analysis.json
```

The script is intentionally small; it does not replace parsing or rendering. It turns an analysis JSON into a concise orientation summary.

## Output Shape

Return:

- `What it is`: probable drawing type and format/version
- `What is inside`: dominant entity/layer/text/block counts
- `Readable preview`: best image path and why that view was chosen
- `Next useful inspection`: one specific next step, not a menu of everything
