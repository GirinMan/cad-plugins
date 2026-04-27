# CAD Conversion Policy

Use this policy when converting CAD files for agent analysis.

- Preserve the original file as the source of record.
- Use DXF as the canonical internal format.
- Prefer ODA File Converter for operational DWG conversion.
- Use LibreDWG `dwgread` only when an open-source-only path is required or ODA is unavailable.
- Validate every output DXF with `ezdxf` when available.
- For large drawings, conversion is not the same as rendering; downstream quicklook/render workflows should decide which views to create.
- On Windows, prefer setting `CAD_PARSER_ODA_PATH` once rather than passing `--oda-path` repeatedly.
- On macOS with decomposed Korean filenames, convert through an ASCII temporary DWG name to avoid ODA filename filter misses.
