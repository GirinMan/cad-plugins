# CAD Parser Research Notes

## Recommendation

Use `ezdxf` as the primary Python parser for DXF and treat DWG as a conversion boundary.
The project pipeline should preserve the source file and make DXF the canonical processing format:

```text
raw DWG/DXF -> canonical DXF -> annotation-aware JSON -> agent analysis
```

For this project, the most useful intermediate shape is annotation-aware JSON:

- `layers`: per-layer entity counts and type mix
- `texts`: `TEXT`, `MTEXT`, and block `ATTRIB` content with coordinates
- `blocks`: `INSERT` references with block names and attributes
- `geometries`: linework and simple shapes with bounds
- `links`: nearest text-to-geometry or text-to-block candidates

## Library Options

`ezdxf` is the best default for the Python analysis layer. It reads and writes DXF, exposes text content, handles `MTEXT`, and can use ODA File Converter for DWG if the converter is installed.

ODA File Converter is the practical DWG bridge for Windows and macOS when direct DWG support is needed. In `ezdxf`, the `odafc` add-on can load a DWG by converting it to a temporary DXF first. For this project, ODA is the stability-first converter.

LibreDWG is a useful open-source alternative for command-line DWG conversion. Its tools can output DXF, JSON, minimal JSON, and GeoJSON. The tradeoff is packaging and conversion fidelity, so it should be treated as the open-source fallback and validated per file.

GDAL/OGR has a DXF driver and is useful when the goal is GIS export. Its own documentation notes that DXF is treated as a single `entities` layer and has no georeferencing information by default, which makes it less ideal as the first layer for label interpretation.

Commercial libraries such as Aspose.CAD can read DWG/DXF and export to other formats, but they are heavier and more conversion-oriented. They are worth considering only if offline DWG rendering/conversion becomes a hard requirement.

## Cross-Platform Conversion Contract

The Python pipeline exposes conversion through `python -m cad_parser.convert`.
It is designed to work the same way on macOS and Windows:

- `--converter oda`: use ODA File Converter
- `--converter libredwg`: use LibreDWG `dwgread`
- `--converter auto`: try ODA first, then LibreDWG
- `--oda-path`: explicit path to ODA executable
- `--dwgread-path`: explicit path to LibreDWG `dwgread`
- `CAD_PARSER_ODA_PATH`: environment variable alternative for ODA
- `CAD_PARSER_DWGREAD_PATH`: environment variable alternative for LibreDWG

This keeps the project code Python-only while allowing each workstation to provide its own native converter binary.

## Current Sample Files

- `data/raw/(B010)수치지도_367020122_2022_00000170761195.dxf`
- `data/raw/보고서 계획평면도 (펌프장추가)-재원협의.dwg`

The DXF sample is AutoCAD R11/R12 (`AC1009`) and can be read directly by `ezdxf`.
The DWG sample is AutoCAD 2000 and needs ODA File Converter or LibreDWG before it can enter the same parser path.
