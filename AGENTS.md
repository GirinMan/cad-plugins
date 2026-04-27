# CAD Plugins Agent Instructions

This repository packages CAD-oriented skills and Python utilities for Codex-style agents. Treat DXF as the canonical working format: preserve original CAD files, convert DWG to DXF when needed, then parse/render/inspect from DXF or normalized JSON.

## Skill Order

Use the smallest skill that answers the user:

- `cad-convert`: DWG/DXF normalization and conversion manifests.
- `cad-quicklook`: concise first-pass file identity and summary.
- `cad-render`: readable purpose-specific previews.
- `cad-inspect`: focused extraction by layer, text, block, entity type, or coordinate region.

Avoid deep parsing when a quicklook answers the question. Avoid rendering one giant image when a clipped linework, block-only, label-only, or layer view is more useful.

## macOS Install

```bash
git clone https://github.com/girinman/cad-plugins.git
cd cad-plugins
python3 --version  # must be Python 3.10+
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
mkdir -p ~/.codex/skills
cp -R skills/cad-* ~/.codex/skills/
```

If macOS `python3` points to Python 3.9, use a newer interpreter such as `python3.13 -m venv .venv`.

Install ODA File Converter for DWG support, then set the path if it is not discoverable:

```bash
export CAD_PARSER_ODA_PATH="/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter"
python -m cad_parser.convert --check
```

Optional open-source fallback:

```bash
brew install libredwg
python -m cad_parser.convert --check
```

## Windows Install

Run in PowerShell from the cloned repo:

```powershell
git clone https://github.com/girinman/cad-plugins.git
cd cad-plugins
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -r requirements.txt
New-Item -ItemType Directory -Force "$env:USERPROFILE\.codex\skills"
Copy-Item -Recurse -Force .\skills\cad-* "$env:USERPROFILE\.codex\skills\"
```

Use any installed Python 3.10+ interpreter; `py -3.11` is a concrete Windows example.

Install ODA File Converter for DWG support, then configure the executable path:

```powershell
$env:CAD_PARSER_ODA_PATH = "C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe"
python -m cad_parser.convert --check
```

Persist it for future shells if desired:

```powershell
[Environment]::SetEnvironmentVariable(
  "CAD_PARSER_ODA_PATH",
  "C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe",
  "User"
)
```

LibreDWG may also be used as a fallback if `dwgread` is installed and visible on `PATH`, or if `CAD_PARSER_DWGREAD_PATH` is set.

## Operating Rules

- Never modify or overwrite original DWG/DXF inputs.
- Store raw/private CAD inputs under `data/raw/`; this path is gitignored.
- Store converted DXF under `data/intermediate/`; this path is gitignored.
- Store bulky generated JSON/HTML/SVG/PNG under `data/processed/`; this path is gitignored.
- Curated public screenshots belong under `assets/examples/`.
- Validate converted DXF with `ezdxf` before claiming conversion success.
- If rendering looks blank, regenerate with clipping before concluding the CAD is empty.
- If rendering is cluttered, make separate linework/block/label/layer views.

## Verification

Before reporting completion, run the relevant checks:

```bash
python -m json.tool .codex-plugin/plugin.json >/dev/null
python -m unittest discover -v
python ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/cad-convert
python ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/cad-quicklook
python ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/cad-render
python ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/cad-inspect
```

On a machine without Codex's local `skill-creator`, skip only the skill validation commands and still validate JSON plus Python tests.
