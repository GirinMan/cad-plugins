# CAD Quicklook Preview Policy

- Use `full_extent` only to diagnose bounds and outliers.
- Use `clipped_linework` as the default preview for dense DWG/DXF files.
- Use labels only when text count is modest or the task is label-focused.
- Use blocks only when symbols are the subject or block count is modest.
- For very large files, prefer PNG over huge inline SVG/HTML.
- Always tell the user which preview is reliable and which previews are diagnostic only.
