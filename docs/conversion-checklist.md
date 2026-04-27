# DWG Conversion Checklist

## Policy

Use ODA File Converter as the default operational converter and LibreDWG as the open-source fallback.

The pipeline keeps DWG as the source of record and DXF as the canonical processing format:

```text
raw DWG -> converted DXF -> validated DXF -> JSON/SVG/HTML
```

## Batch Command

macOS/Linux:

```bash
.venv/bin/python -m cad_parser.convert \
  --input-dir data/raw \
  --pattern "*.dwg" \
  --converted-dir data/intermediate \
  --manifest data/processed/conversion_manifest.json \
  --keep-going
```

Windows PowerShell:

```powershell
.venv\Scripts\python.exe -m cad_parser.convert `
  --input-dir data\raw `
  --pattern "*.dwg" `
  --converted-dir data\intermediate `
  --manifest data\processed\conversion_manifest.json `
  --keep-going
```

## Converter Paths

Prefer environment variables on shared machines:

- `CAD_PARSER_ODA_PATH`
- `CAD_PARSER_DWGREAD_PATH`

Or pass paths explicitly:

- `--oda-path`
- `--dwgread-path`

## Validation Gates

Each converted DXF should pass these checks before downstream analysis:

- File exists and is not empty
- `ezdxf` can open the file
- DXF version is detected
- Layer count is non-zero
- Geometry count is non-zero for map/plan drawings
- Text count is reviewed for label-heavy drawings
- `INSERT` count is reviewed for symbol-heavy drawings

## Failure Handling

Use `--keep-going` for batch conversion so one bad DWG does not block the whole folder.
The manifest records failed files with an `ok: false` entry and the converter error.
