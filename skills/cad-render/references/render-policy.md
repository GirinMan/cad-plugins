# CAD Render Policy

CAD rendering is a question-driven view, not a single canonical image.

Recommended view order for unknown large CAD files:

1. `full`: find outliers and diagnose empty-looking images
2. `linework` with clipping: readable geometry overview
3. `blocks`: inspect symbol density
4. `labels`: inspect annotation density
5. `layer`: inspect a specific layer or layer family

Common fixes:

- Blank or tiny drawing: use clipped bounds.
- Text becomes black mass: hide text or limit labels.
- Blocks cover geometry: hide blocks or make block-only view.
- Browser struggles with SVG/HTML: render PNG.
- Important layer hidden in clutter: render a layer-filtered view.
