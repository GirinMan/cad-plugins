# CAD Plugins Instructions For Claude

Use this repository as a CAD workflow kit for Claude/Claude Code. The core idea is simple: convert every CAD input to DXF first, then choose the lightest reading mode that answers the user's question.

## macOS Setup

```bash
git clone https://github.com/girinman/cad-plugins.git
cd cad-plugins
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
mkdir -p ~/.claude/skills
cp -R skills/cad-* ~/.claude/skills/
```

For DWG conversion, install ODA File Converter and configure it when needed:

```bash
export CAD_PARSER_ODA_PATH="/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter"
python -m cad_parser.convert --check
```

Optional LibreDWG fallback:

```bash
brew install libredwg
python -m cad_parser.convert --check
```

## Windows Setup

Run in PowerShell:

```powershell
git clone https://github.com/girinman/cad-plugins.git
cd cad-plugins
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -r requirements.txt
New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\skills"
Copy-Item -Recurse -Force .\skills\cad-* "$env:USERPROFILE\.claude\skills\"
```

For DWG conversion:

```powershell
$env:CAD_PARSER_ODA_PATH = "C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe"
python -m cad_parser.convert --check
```

Persist the setting:

```powershell
[Environment]::SetEnvironmentVariable(
  "CAD_PARSER_ODA_PATH",
  "C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe",
  "User"
)
```

If LibreDWG is installed instead, make `dwgread` available on `PATH` or set `CAD_PARSER_DWGREAD_PATH`.

## Skill Selection

Use these repo skills as workflow prompts:

- `cad-convert` for DWG to DXF normalization and conversion validation.
- `cad-quicklook` for short, human-friendly file summaries.
- `cad-render` for PNG/SVG/HTML previews, especially clipped linework previews.
- `cad-inspect` for targeted label/layer/block/coordinate questions.

Prefer quicklook before deep inspection unless the user already named a specific target. Prefer deterministic parser/render output over image-generation models for CAD truth. Image generation models may help explain a report visually, but they should not invent geometry, labels, or coordinates.

## Commands

```bash
python -m cad_parser.convert --check
python -m cad_parser.convert input.dwg --out data/intermediate/input.dxf
python -m cad_parser.cli input.dxf --out data/processed/input_analysis.json --png-out data/processed/input_preview.png --png-clip-percentile 0.01
python -m cad_parser.visualize data/processed/input_analysis.json --png-out data/processed/input_linework.png --clip-percentile 0.01
```

## Data Safety

Do not commit private DWG/DXF inputs, large intermediate DXF files, or bulky generated analysis JSON. Keep shareable screenshots under `assets/examples/` only after confirming they are safe for publication.
