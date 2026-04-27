# CAD Plugins

## Quickstart

- Codex: "https://github.com/girinman/cad-plugins repo를 clone하고 AGENTS.md의 지시사항대로 설치를 진행하세요"
- Claude: "https://github.com/girinman/cad-plugins repo를 clone하고 AGENTS.md의 지시사항대로 설치를 진행하세요"

```bash
git clone https://github.com/girinman/cad-plugins.git
cd cad-plugins
python3 --version  # must be Python 3.10+
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
```

If macOS `python3` is the system Python 3.9, use a newer interpreter such as `python3.13 -m venv .venv`.

Windows PowerShell:

```powershell
git clone https://github.com/girinman/cad-plugins.git
cd cad-plugins
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -r requirements.txt
```

Any Python 3.10+ interpreter is fine on Windows; `py -3.11` is just a concrete example.

## What This Repo Is

This repo is a draft export package for CAD-oriented agent skills. It combines:

- `skills/cad-convert`: normalize DWG/DXF into canonical DXF.
- `skills/cad-quicklook`: produce a short, non-CAD-specialist summary.
- `skills/cad-render`: generate readable PNG/SVG/HTML views.
- `skills/cad-inspect`: answer focused questions about layers, labels, blocks, and coordinates.
- `cad_parser/`: Python utilities used by the skills for conversion, parsing, and rendering.

The workflow is intentionally not “turn CAD into one image.” CAD files can contain geometry, labels, blocks, attributes, and layer semantics. The useful reading mode depends on the question:

- Fast orientation: quicklook summary plus one clipped preview.
- Visual check: render linework, blocks, labels, or layer-specific views.
- Agent analysis: parse into annotation-aware JSON.
- Focused inspection: search labels, layers, block names, and coordinate regions.

## Install As Skills

Codex local skill install:

```bash
mkdir -p ~/.codex/skills
cp -R skills/cad-* ~/.codex/skills/
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.codex\skills"
Copy-Item -Recurse -Force .\skills\cad-* "$env:USERPROFILE\.codex\skills\"
```

Claude-compatible local skill copy:

```bash
mkdir -p ~/.claude/skills
cp -R skills/cad-* ~/.claude/skills/
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\skills"
Copy-Item -Recurse -Force .\skills\cad-* "$env:USERPROFILE\.claude\skills\"
```

The plugin manifest lives at `.codex-plugin/plugin.json` and points to `./skills/`.

## CAD Converter Dependencies

DXF files can be parsed directly with Python. DWG conversion needs a local converter.

Recommended DWG converter:

- ODA File Converter for macOS and Windows. This is the practical default for stable DWG to DXF conversion.
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

Persist the Windows variable for future terminals:

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

## Skill Execution Results

### B010 수치지도 DXF

This sample behaved like a map-style DXF: layer-centered geometry with meaningful labels. A quicklook/render pass produced a readable clipped preview suitable for orientation before deeper label inspection.

![B010 수치지도 preview](assets/examples/b010_preview.png)

### Pump Station Plan DWG

This DWG was normalized to DXF first, then rendered as CAD-derived previews. The useful view was not a single full screenshot: clipped linework and block-aware previews made the dense plan easier to inspect.

![Pump station plan preview](assets/examples/pump_plan_preview.png)

Block-aware preview:

![Pump station plan block preview](assets/examples/pump_plan_preview_with_blocks.png)

## Recommended Agent Workflow

1. Start with `cad-convert` for every DWG/DXF input so downstream steps use canonical DXF.
2. Use `cad-quicklook` when the user asks “what is this file?” or needs a short summary.
3. Use `cad-render` when the user needs to see the drawing, but pick a purpose-specific view.
4. Use `cad-inspect` only after the target is specific: keyword, layer, block, coordinate area, or facility label.

## What Not To Commit

Do not commit customer CAD originals, huge normalized JSON reports, or generated intermediate DXF files by default. Put reusable public examples under `assets/examples/` after confirming they are safe to share.
