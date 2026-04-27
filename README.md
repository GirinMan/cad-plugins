<p align="center">
  <img src="assets/cad-plugins-cover.png" alt="CAD Plugins cover image" width="100%">
</p>

<h1 align="center">CAD Plugins</h1>

<p align="center">
  <strong>Agent-ready CAD skills and Python utilities for DWG/DXF conversion, quick summaries, focused inspection, and readable previews.</strong>
</p>

<p align="center">
  <a href="https://github.com/GirinMan/cad-plugins/blob/main/LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-00A6A6?style=for-the-badge"></a>
  <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-2E7DDB?style=for-the-badge&logo=python&logoColor=white">
  <img alt="CAD formats" src="https://img.shields.io/badge/CAD-DWG%20%2F%20DXF-FFB000?style=for-the-badge">
  <img alt="Codex skills" src="https://img.shields.io/badge/Codex-Skills-111827?style=for-the-badge">
  <img alt="Claude compatible" src="https://img.shields.io/badge/Claude-Compatible-5A45FF?style=for-the-badge">
</p>

<p align="center">
  <a href="README.ko.md">한국어</a> |
  <strong>English</strong>
</p>

<p align="center">
  <a href="#quickstart">Quickstart</a> |
  <a href="#skills">Skills</a> |
  <a href="#common-commands">Commands</a> |
  <a href="#examples">Examples</a> |
  <a href="#recommended-agent-workflow">Workflow</a>
</p>

---

## Why This Exists

CAD files are rarely just pictures. A single drawing can contain nested blocks, layers, dimensions, labels, attributes, construction geometry, and huge coordinate spaces. `CAD Plugins` gives agents a practical CAD workflow:

- Preserve original DWG/DXF inputs.
- Normalize DWG to canonical DXF when needed.
- Parse CAD structure into annotation-aware JSON.
- Render purpose-specific previews instead of one overloaded screenshot.
- Inspect by layer, block, text, entity type, keyword, or coordinate region.

## Skills

| Area | Path | Purpose |
| --- | --- | --- |
| Conversion | `skills/cad-convert` | Normalize DWG/DXF inputs into canonical DXF and validate results. |
| Quicklook | `skills/cad-quicklook` | Produce concise first-pass summaries for non-CAD specialists. |
| Rendering | `skills/cad-render` | Generate readable PNG/SVG/HTML previews from CAD analysis JSON. |
| Inspection | `skills/cad-inspect` | Extract focused answers about layers, labels, blocks, entities, and regions. |
| Python utilities | `cad_parser/` | Shared conversion, parsing, modeling, and visualization code used by the skills. |

## Quickstart

```bash
git clone https://github.com/GirinMan/cad-plugins.git
cd cad-plugins

python3 --version  # must be Python 3.10+
python3 -m venv .venv
source .venv/bin/activate

python -m pip install -U pip
python -m pip install -r requirements.txt
python -m unittest discover -v
```

If macOS `python3` points to Python 3.9, use a newer interpreter such as `python3.13 -m venv .venv`.

Windows PowerShell:

```powershell
git clone https://github.com/GirinMan/cad-plugins.git
cd cad-plugins

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install -U pip
python -m pip install -r requirements.txt
python -m unittest discover -v
```

Any Python 3.10+ interpreter is fine on Windows; `py -3.11` is just a concrete example.

## Install As Skills

Codex local skill install:

```bash
mkdir -p ~/.codex/skills
cp -R skills/cad-* ~/.codex/skills/
```

Claude-compatible local skill copy:

```bash
mkdir -p ~/.claude/skills
cp -R skills/cad-* ~/.claude/skills/
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.codex\skills"
Copy-Item -Recurse -Force .\skills\cad-* "$env:USERPROFILE\.codex\skills\"

New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\skills"
Copy-Item -Recurse -Force .\skills\cad-* "$env:USERPROFILE\.claude\skills\"
```

The plugin manifest lives at `.codex-plugin/plugin.json` and points to `./skills/`.

## CAD Converter Dependencies

DXF files can be parsed directly with Python. DWG conversion needs a local converter.

Recommended DWG converter:

- [ODA File Converter](https://www.opendesign.com/guestfiles/oda_file_converter) for macOS and Windows.
- LibreDWG `dwgread` as an open-source fallback when available, with per-file validation.

macOS ODA path example:

```bash
export CAD_PARSER_ODA_PATH="/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter"
python -m cad_parser.convert --check
```

Windows ODA path example:

```powershell
$env:CAD_PARSER_ODA_PATH = "C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe"
python -m cad_parser.convert --check
```

If you need the Windows installer itself, use the ODA File Converter MSI and install it first:

<https://www.opendesign.com/guestfiles/get?filename=ODAFileConverter_QT6_vc16_amd64dll_27.1.msi>
Persist it for future Windows shells if desired:

```powershell
[Environment]::SetEnvironmentVariable(
  "CAD_PARSER_ODA_PATH",
  "C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe",
  "User"
)
```

## Common Commands

Check converter availability:

```bash
python -m cad_parser.convert --check
```

Convert one DWG to canonical DXF:

```bash
python -m cad_parser.convert input.dwg \
  --out data/intermediate/input.dxf \
  --manifest data/processed/input_conversion_manifest.json
```

Analyze DXF or DWG into JSON and PNG:

```bash
python -m cad_parser.cli input.dxf \
  --out data/processed/input_analysis.json \
  --png-out data/processed/input_preview.png \
  --png-width 2400 \
  --png-height 1800 \
  --png-clip-percentile 0.01
```

Render again from an existing JSON analysis:

```bash
python -m cad_parser.visualize data/processed/input_analysis.json \
  --png-out data/processed/input_linework.png \
  --width 2400 \
  --height 1800 \
  --clip-percentile 0.01
```

## Examples

### B010 수치지도 DXF

This sample behaves like a map-style DXF: layer-centered geometry with meaningful labels. A quicklook/render pass produces a readable clipped preview suitable for orientation before deeper label inspection.

![B010 수치지도 preview](assets/examples/b010_preview.png)

### Pump Station Plan DWG

This DWG is normalized to DXF first, then rendered as CAD-derived previews. The useful view is not a single full screenshot: clipped linework and block-aware previews make the dense plan easier to inspect.

![Pump station plan preview](assets/examples/pump_plan_preview.png)

Block-aware preview:

![Pump station plan block preview](assets/examples/pump_plan_preview_with_blocks.png)

## Recommended Agent Workflow

1. Start with `cad-convert` for every DWG/DXF input so downstream steps use canonical DXF.
2. Use `cad-quicklook` when the user asks "what is this file?" or needs a short summary.
3. Use `cad-render` when the user needs to see the drawing, but pick a purpose-specific view.
4. Use `cad-inspect` only after the target is specific: keyword, layer, block, coordinate area, or facility label.

## What Not To Commit

Do not commit customer CAD originals, huge normalized JSON reports, or generated intermediate DXF files by default. Put reusable public examples under `assets/examples/` after confirming they are safe to share.

## Verification

Before publishing changes, run:

```bash
python -m json.tool .codex-plugin/plugin.json >/dev/null
python -m unittest discover -v
python ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/cad-convert
python ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/cad-quicklook
python ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/cad-render
python ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/cad-inspect
```
