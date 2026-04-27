---
name: cad-convert
description: Convert CAD inputs to a canonical DXF working format. Use when the user provides DWG/DXF files and asks to process, analyze, preview, normalize, batch convert, or make Windows/macOS-compatible CAD workflows. This skill focuses only on preserving originals, converting DWG to DXF, validating the DXF, and recording conversion manifests before any deeper CAD analysis.
---

# CAD Convert

## Purpose

Use DXF as the canonical processing format. Keep the original DWG/DXF unchanged, create or reuse a DXF in an intermediate folder, validate that DXF, and write a manifest that downstream quicklook/inspect/render workflows can trust.

## Workflow

1. Preserve the source file. Do not edit or overwrite the uploaded CAD file.
2. Detect extension and version when possible.
3. If input is already `.dxf`, validate it and either reuse it or copy it to the canonical output path if the user asked for one.
4. If input is `.dwg`, convert to `.dxf`.
5. Prefer converters in this order:
   1. Project-local converter, if the repo already has one such as `python -m cad_parser.convert`
   2. ODA File Converter for operational stability
   3. LibreDWG `dwgread` for open-source-only fallback
6. Validate the resulting DXF with `ezdxf` when available.
7. Write a manifest with source path, DXF path, converter, success/failure, file size, DXF version, layer count, text count, block count, and geometry count.
8. Stop at DXF unification unless the user also asks for quicklook, rendering, or semantic inspection.

## Commands

If a project-local converter exists, prefer it:

```bash
python -m cad_parser.convert --check
python -m cad_parser.convert input.dwg --out data/intermediate/input.dxf --manifest data/processed/conversion_manifest.json
```

If no project converter exists, use the bundled script:

```bash
python skills/cad-convert/scripts/cad_to_dxf.py --check
python skills/cad-convert/scripts/cad_to_dxf.py input.dwg --out data/intermediate/input.dxf --manifest data/processed/conversion_manifest.json
```

For Windows, use the same Python script and pass ODA explicitly when it is not on `PATH`:

```powershell
python .\skills\cad-convert\scripts\cad_to_dxf.py input.dwg `
  --converter oda `
  --oda-path "C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe" `
  --out data\intermediate\input.dxf `
  --manifest data\processed\conversion_manifest.json
```

Environment variables are also supported:

- `CAD_PARSER_ODA_PATH`
- `CAD_PARSER_DWGREAD_PATH`

## Output Contract

Use this folder convention unless the repo already has another established layout:

- Originals: `data/raw/`
- Canonical DXF: `data/intermediate/`
- Manifest: `data/processed/conversion_manifest.json`

Return a concise summary:

- Which files were converted or reused
- Which converter was used
- Whether validation passed
- Where the canonical DXF and manifest are
- Any failed files and exact errors

## Notes

ODA File Converter is usually the best operational default for DWG conversion, even though it is not a FOSS dependency. LibreDWG is the open-source fallback and must be validated per file. For macOS Unicode filenames, the bundled script copies DWG files to an ASCII temporary name before invoking ODA to avoid filename filter misses.
