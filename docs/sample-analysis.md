# Sample CAD Analysis

## Files Stored In Project

- `data/raw/(B010)수치지도_367020122_2022_00000170761195.dxf`
- `data/raw/보고서 계획평면도 (펌프장추가)-재원협의.dwg`

## DXF Result

The DXF sample is an AutoCAD R11/R12 drawing (`AC1009`). Its filename and content indicate an NGII-style numeric map rather than a normal design drawing.

Observed modelspace content:

- `POLYLINE`: 493
- `INSERT`: 159
- `TEXT`: 29
- Layers: 47
- Text records: 29
- Block references: 159
- Geometry records: 493
- Label-to-target link candidates: 87

Top layers by entity count:

- `D0015112`: 71 geometries
- `B0014116`: 67 geometries
- `D0015212`: 49 block references
- `F0017114`: 40 geometries
- `C0285311`: 29 block references
- `B0014111`: 28 geometries
- `C0536117`: 27 geometries
- `E0022112`: 26 geometries
- `C0076116`: 25 geometries
- `B0024126`: 23 geometries

Example labels extracted from `TEXT` entities:

- `동명스틸`
- `(주)동면스틸`
- `케이원산업가스`
- `TK스틸`
- `계동`
- `도  기  동`

## Initial Interpretation

This is a map-like CAD file. The useful interpretation task is not only vector extraction; it is layer, block, and label interpretation.

The current parser can already answer:

- Which CAD entity types are present?
- Which layers dominate the file?
- What text labels are present and where are they?
- Which block symbols exist and where are they inserted?
- Which nearby geometry or block each text label may describe?

The next useful layer is a feature-code dictionary for layer names such as `H0049140`, `H0049210`, `F0017114`, and `D0015112`.

## DWG Status

The DWG sample is AutoCAD 2000 (`AC1015`). It has now been converted with ODA File Converter and normalized through the same DXF parser.

Generated files:

- `data/intermediate/pump_plan.dxf`
- `data/processed/pump_plan_conversion_manifest.json`
- `data/processed/pump_plan_analysis.json`
- `data/processed/pump_plan_preview.svg`
- `data/processed/pump_plan_preview.html`

Conversion validation:

- DXF version: `AC1032`
- Layers: 244
- `LINE`: 90,843
- `TEXT`: 57,563
- `INSERT`: 55,984
- `LWPOLYLINE`: 16,327
- `POLYLINE`: 12,405
- Basic geometry count: 121,770

Parser output:

- Text records: 79,163, including extracted block attributes
- Block records: 55,984
- Geometry records: 121,770
- Link records: 0 for the first full-file run, because exhaustive label-to-geometry matching at this scale should be scoped by layer/region before running

Initial interpretation: this is a very large plan/map CAD file with dense labels and many block inserts. It is now ready for layer-focused analysis, label filtering, and scoped visualization.
