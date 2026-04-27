from __future__ import annotations

import argparse
import json
from pathlib import Path

from cad_parser.converters import CadConversionError, prepare_analysis_input
from cad_parser.models import to_jsonable
from cad_parser.parser import UnsupportedCadFormatError, analyze_cad_file
from cad_parser.visualize import render_html, render_png, render_svg


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze CAD files into annotation-aware JSON.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--converted-dir", type=Path, default=Path("data/intermediate"))
    parser.add_argument("--converter", choices=["auto", "oda", "libredwg"], default="auto")
    parser.add_argument("--dxf-version", default="R2018")
    parser.add_argument("--replace-converted", action="store_true")
    parser.add_argument("--oda-path", type=Path)
    parser.add_argument("--dwgread-path", type=Path)
    parser.add_argument("--max-links", type=int, default=3)
    parser.add_argument("--indent", type=int, default=2)
    parser.add_argument("--svg-out", type=Path)
    parser.add_argument("--html-out", type=Path)
    parser.add_argument("--png-out", type=Path)
    parser.add_argument("--png-width", type=int, default=2400)
    parser.add_argument("--png-height", type=int, default=1800)
    parser.add_argument("--png-clip-percentile", type=float, default=0.0)
    args = parser.parse_args()

    try:
        prepared = prepare_analysis_input(
            args.input,
            args.converted_dir,
            converter=args.converter,
            dxf_version=args.dxf_version,
            replace=args.replace_converted,
            oda_path=args.oda_path,
            dwgread_path=args.dwgread_path,
        )
        analysis = analyze_cad_file(prepared.dxf_file, max_links_per_text=args.max_links)
        analysis.notes = [*prepared.notes, *analysis.notes]
        if prepared.source_file != prepared.dxf_file:
            analysis.notes.append(f"Original source: {prepared.source_file}")
    except (CadConversionError, UnsupportedCadFormatError) as exc:
        parser.error(str(exc))

    payload = json.dumps(to_jsonable(analysis), ensure_ascii=False, indent=args.indent)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    if args.svg_out or args.html_out or args.png_out:
        analysis_payload = to_jsonable(analysis)
        svg = render_svg(analysis_payload)
        if args.svg_out:
            args.svg_out.parent.mkdir(parents=True, exist_ok=True)
            args.svg_out.write_text(svg, encoding="utf-8")
        if args.html_out:
            args.html_out.parent.mkdir(parents=True, exist_ok=True)
            args.html_out.write_text(render_html(analysis_payload, svg), encoding="utf-8")
        if args.png_out:
            render_png(
                analysis_payload,
                args.png_out,
                width=args.png_width,
                height=args.png_height,
                clip_percentile=args.png_clip_percentile,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
