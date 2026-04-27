from __future__ import annotations

import argparse
import hashlib
import html
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - optional runtime feature
    Image = None
    ImageDraw = None
    ImageFont = None


PALETTE = [
    "#006D77",
    "#E29578",
    "#2A9D8F",
    "#E9C46A",
    "#264653",
    "#D62828",
    "#457B9D",
    "#6A994E",
    "#BC6C25",
    "#7B2CBF",
]


@dataclass(frozen=True)
class ViewTransform:
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    width: int
    height: int
    padding: int
    scale: float
    offset_x: float
    offset_y: float

    def point(self, point: dict[str, Any]) -> tuple[float, float]:
        x = self.padding + (float(point["x"]) - self.min_x) * self.scale + self.offset_x
        y = self.padding + (self.max_y - float(point["y"])) * self.scale + self.offset_y
        return x, y


def render_svg(analysis: dict[str, Any], width: int = 1400, height: int = 1000) -> str:
    transform = _build_transform(analysis, width=width, height=height)
    geometry_markup = "\n".join(_render_geometry(item, transform) for item in analysis.get("geometries", []))
    block_markup = "\n".join(_render_block(item, transform) for item in analysis.get("blocks", []))
    link_markup = "\n".join(_render_link(item, analysis, transform) for item in analysis.get("links", []))
    text_markup = "\n".join(_render_text(item, transform) for item in analysis.get("texts", []))
    legend_markup = _render_legend(analysis)
    title = html.escape(Path(analysis.get("source_file", "CAD analysis")).name)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{title}">
  <title>{title}</title>
  <rect width="100%" height="100%" fill="#fbfaf7"/>
  <g id="links" opacity="0.35">
{link_markup}
  </g>
  <g id="geometries" fill="none" stroke-linecap="round" stroke-linejoin="round">
{geometry_markup}
  </g>
  <g id="blocks">
{block_markup}
  </g>
  <g id="labels" font-family="Avenir Next, Apple SD Gothic Neo, Malgun Gothic, sans-serif" fill="#1f2933">
{text_markup}
  </g>
  <g id="legend" font-family="Avenir Next, Apple SD Gothic Neo, Malgun Gothic, sans-serif">
{legend_markup}
  </g>
</svg>
"""


def render_html(analysis: dict[str, Any], svg: str) -> str:
    source = html.escape(Path(analysis.get("source_file", "CAD analysis")).name)
    counts = analysis.get("entity_counts", {})
    count_text = ", ".join(f"{html.escape(str(key))}: {value}" for key, value in counts.items())
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{source}</title>
  <style>
    body {{
      margin: 0;
      background: #f3f0e8;
      color: #1f2933;
      font-family: Avenir Next, Apple SD Gothic Neo, Malgun Gothic, sans-serif;
    }}
    header {{
      padding: 18px 24px;
      border-bottom: 1px solid #d7d0c2;
      background: #fffaf0;
    }}
    h1 {{
      margin: 0 0 6px;
      font-size: 18px;
      font-weight: 700;
      letter-spacing: 0;
    }}
    p {{
      margin: 0;
      font-size: 13px;
      color: #52616b;
    }}
    main {{
      overflow: auto;
      padding: 18px;
    }}
    svg {{
      display: block;
      max-width: none;
      border: 1px solid #d7d0c2;
      background: #fbfaf7;
    }}
  </style>
</head>
<body>
  <header>
    <h1>{source}</h1>
    <p>{html.escape(count_text)}</p>
  </header>
  <main>
{svg}
  </main>
</body>
</html>
"""


def write_visualization(
    analysis_path: str | Path,
    svg_out: str | Path | None = None,
    html_out: str | Path | None = None,
    png_out: str | Path | None = None,
    width: int = 1400,
    height: int = 1000,
    clip_percentile: float = 0.0,
) -> tuple[Path | None, Path | None]:
    analysis_file = Path(analysis_path)
    analysis = json.loads(analysis_file.read_text(encoding="utf-8"))
    svg = render_svg(analysis, width=width, height=height)
    written_svg = _write_optional(svg_out, svg)
    written_html = _write_optional(html_out, render_html(analysis, svg))
    if png_out:
        render_png(analysis, png_out, width=width, height=height, clip_percentile=clip_percentile)
    return written_svg, written_html


def render_png(
    analysis: dict[str, Any],
    output: str | Path,
    width: int = 2400,
    height: int = 1800,
    clip_percentile: float = 0.0,
    draw_texts: bool = True,
    draw_blocks: bool = True,
    max_labels: int = 12000,
) -> Path:
    if Image is None or ImageDraw is None:
        raise RuntimeError("Pillow is required for PNG rendering. Install with: pip install pillow")
    transform = _build_transform(analysis, width=width, height=height, bounds=_analysis_bounds(analysis, clip_percentile))
    image = Image.new("RGB", (width, height), "#fbfaf7")
    draw = ImageDraw.Draw(image, "RGBA")

    for geometry in analysis.get("geometries", []):
        bounds = geometry.get("bounds")
        if not bounds or not _bounds_intersects(bounds, transform):
            continue
        points = geometry.get("points") or []
        if len(points) < 2:
            continue
        pixel_points = [transform.point(point) for point in points]
        if geometry.get("metadata", {}).get("closed") and pixel_points:
            pixel_points.append(pixel_points[0])
        color = _hex_to_rgba(_layer_color(geometry.get("layer", "0")), 185)
        width_px = 2 if geometry.get("kind") in {"POLYLINE", "LWPOLYLINE", "LINE"} else 1
        draw.line(pixel_points, fill=color, width=width_px, joint="curve")

    if draw_blocks:
        for block in analysis.get("blocks", []):
            point = block.get("insert")
            if not point or not _point_inside(point, transform):
                continue
            x, y = transform.point(point)
            color = _hex_to_rgba(_layer_color(block.get("layer", "0")), 210)
            draw.rectangle((x - 3, y - 3, x + 3, y + 3), fill=color)

    if draw_texts:
        font = _default_font(14)
        for text in analysis.get("texts", [])[:max_labels]:
            label = str(text.get("text", "")).strip()
            point = text.get("insert")
            if not label or not point or not _point_inside(point, transform):
                continue
            x, y = transform.point(point)
            display = label[:24]
            draw.text((x + 5, y - 12), display, fill=(31, 41, 51, 220), font=font)

    _draw_png_legend(draw, analysis, width)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Render annotation-aware CAD JSON as SVG/HTML.")
    parser.add_argument("analysis_json", type=Path)
    parser.add_argument("--svg-out", type=Path)
    parser.add_argument("--html-out", type=Path)
    parser.add_argument("--png-out", type=Path)
    parser.add_argument("--width", type=int, default=1400)
    parser.add_argument("--height", type=int, default=1000)
    parser.add_argument("--clip-percentile", type=float, default=0.0)
    parser.add_argument("--no-text", action="store_true")
    parser.add_argument("--no-blocks", action="store_true")
    parser.add_argument("--max-labels", type=int, default=12000)
    args = parser.parse_args()

    if not args.svg_out and not args.html_out and not args.png_out:
        args.svg_out = args.analysis_json.with_suffix(".svg")
    write_visualization(
        args.analysis_json,
        args.svg_out,
        args.html_out,
        None,
        width=args.width,
        height=args.height,
        clip_percentile=args.clip_percentile,
    )
    if args.png_out:
        analysis = json.loads(args.analysis_json.read_text(encoding="utf-8"))
        render_png(
            analysis,
            args.png_out,
            width=args.width,
            height=args.height,
            clip_percentile=args.clip_percentile,
            draw_texts=not args.no_text,
            draw_blocks=not args.no_blocks,
            max_labels=args.max_labels,
        )
    return 0


def _write_optional(path: str | Path | None, content: str) -> Path | None:
    if path is None:
        return None
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    return output


def _build_transform(
    analysis: dict[str, Any],
    width: int,
    height: int,
    padding: int = 40,
    bounds: tuple[float, float, float, float] | None = None,
) -> ViewTransform:
    bounds = bounds or _analysis_bounds(analysis)
    min_x, min_y, max_x, max_y = bounds
    drawing_width = max(max_x - min_x, 1.0)
    drawing_height = max(max_y - min_y, 1.0)
    available_width = max(width - padding * 2, 1)
    available_height = max(height - padding * 2, 1)
    scale = min(available_width / drawing_width, available_height / drawing_height)
    offset_x = (available_width - drawing_width * scale) / 2
    offset_y = (available_height - drawing_height * scale) / 2
    return ViewTransform(min_x, min_y, max_x, max_y, width, height, padding, scale, offset_x, offset_y)


def _analysis_bounds(analysis: dict[str, Any], clip_percentile: float = 0.0) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    for geometry in analysis.get("geometries", []):
        bounds = geometry.get("bounds")
        if not bounds:
            continue
        xs.extend([float(bounds["min_x"]), float(bounds["max_x"])])
        ys.extend([float(bounds["min_y"]), float(bounds["max_y"])])
    for collection in ("texts", "blocks"):
        for item in analysis.get(collection, []):
            point = item.get("insert")
            if point:
                xs.append(float(point["x"]))
                ys.append(float(point["y"]))
    if not xs or not ys:
        return 0.0, 0.0, 1.0, 1.0
    if clip_percentile > 0:
        xs.sort()
        ys.sort()
        lower = min(max(clip_percentile, 0.0), 0.49)
        upper = 1.0 - lower
        return _quantile(xs, lower), _quantile(ys, lower), _quantile(xs, upper), _quantile(ys, upper)
    return min(xs), min(ys), max(xs), max(ys)


def _quantile(values: list[float], fraction: float) -> float:
    index = int((len(values) - 1) * fraction)
    return values[index]


def _bounds_intersects(bounds: dict[str, Any], transform: ViewTransform) -> bool:
    return not (
        float(bounds["max_x"]) < transform.min_x
        or float(bounds["min_x"]) > transform.max_x
        or float(bounds["max_y"]) < transform.min_y
        or float(bounds["min_y"]) > transform.max_y
    )


def _point_inside(point: dict[str, Any], transform: ViewTransform) -> bool:
    return transform.min_x <= float(point["x"]) <= transform.max_x and transform.min_y <= float(point["y"]) <= transform.max_y


def _render_geometry(geometry: dict[str, Any], transform: ViewTransform) -> str:
    points = geometry.get("points") or []
    if len(points) < 2:
        return ""
    color = _layer_color(geometry.get("layer", "0"))
    width = 1.2 if geometry.get("kind") in {"POLYLINE", "LWPOLYLINE", "LINE"} else 0.9
    encoded_points = " ".join(_svg_point(transform.point(point)) for point in points)
    if geometry.get("metadata", {}).get("closed") and points:
        encoded_points = f"{encoded_points} {_svg_point(transform.point(points[0]))}"
    layer = html.escape(str(geometry.get("layer", "0")))
    kind = html.escape(str(geometry.get("kind", "")))
    return f'    <polyline points="{encoded_points}" stroke="{color}" stroke-width="{width}" data-layer="{layer}" data-kind="{kind}"/>'


def _render_block(block: dict[str, Any], transform: ViewTransform) -> str:
    x, y = transform.point(block["insert"])
    color = _layer_color(block.get("layer", "0"))
    name = html.escape(str(block.get("name", "")))
    layer = html.escape(str(block.get("layer", "0")))
    return (
        f'    <g data-layer="{layer}" data-block="{name}">'
        f'<rect x="{x - 3:.2f}" y="{y - 3:.2f}" width="6" height="6" fill="{color}" opacity="0.82"/>'
        f'<title>{name}</title></g>'
    )


def _render_text(text: dict[str, Any], transform: ViewTransform) -> str:
    label = str(text.get("text", "")).strip()
    if not label:
        return ""
    x, y = transform.point(text["insert"])
    safe_label = html.escape(label)
    layer = html.escape(str(text.get("layer", "0")))
    font_size = max(8, min(14, float(text.get("height") or 10) * transform.scale * 0.8))
    return (
        f'    <text x="{x + 4:.2f}" y="{y - 4:.2f}" font-size="{font_size:.2f}" '
        f'data-layer="{layer}" paint-order="stroke" stroke="#fbfaf7" stroke-width="2" fill="#1f2933">{safe_label}</text>'
    )


def _render_link(link: dict[str, Any], analysis: dict[str, Any], transform: ViewTransform) -> str:
    text = _find_by_id(analysis.get("texts", []), link.get("text_id"))
    if not text:
        return ""
    target = _find_by_id(analysis.get("geometries", []), link.get("target_id"))
    target_point = _target_point(target)
    if target_point is None:
        block = _find_by_id(analysis.get("blocks", []), link.get("target_id"))
        target_point = block.get("insert") if block else None
    if target_point is None:
        return ""
    x1, y1 = transform.point(text["insert"])
    x2, y2 = transform.point(target_point)
    return f'    <line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="#5f6c72" stroke-width="0.7" stroke-dasharray="4 4"/>'


def _target_point(geometry: dict[str, Any] | None) -> dict[str, float] | None:
    if not geometry:
        return None
    bounds = geometry.get("bounds")
    if not bounds:
        return None
    return {
        "x": (float(bounds["min_x"]) + float(bounds["max_x"])) / 2,
        "y": (float(bounds["min_y"]) + float(bounds["max_y"])) / 2,
        "z": 0.0,
    }


def _render_legend(analysis: dict[str, Any], max_layers: int = 8) -> str:
    layers = analysis.get("layers", [])[:max_layers]
    lines = [
        '    <rect x="18" y="18" width="230" height="{}" fill="#fffaf0" stroke="#d7d0c2"/>'.format(
            34 + len(layers) * 20
        ),
        '    <text x="30" y="40" font-size="13" font-weight="700" fill="#1f2933">Top layers</text>',
    ]
    for index, layer in enumerate(layers):
        y = 62 + index * 20
        name = str(layer.get("name", "0"))
        label = html.escape(f"{name} ({layer.get('entity_count', 0)})")
        lines.append(f'    <rect x="30" y="{y - 10}" width="10" height="10" fill="{_layer_color(name)}"/>')
        lines.append(f'    <text x="48" y="{y}" font-size="11" fill="#52616b">{label}</text>')
    return "\n".join(lines)


def _find_by_id(items: list[dict[str, Any]], item_id: Any) -> dict[str, Any] | None:
    return next((item for item in items if item.get("id") == item_id), None)


def _svg_point(point: tuple[float, float]) -> str:
    return f"{point[0]:.2f},{point[1]:.2f}"


def _layer_color(layer: str) -> str:
    digest = hashlib.sha1(str(layer).encode("utf-8")).digest()
    return PALETTE[digest[0] % len(PALETTE)]


def _hex_to_rgba(color: str, alpha: int) -> tuple[int, int, int, int]:
    color = color.lstrip("#")
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16), alpha


def _default_font(size: int):
    if ImageFont is None:
        return None
    for path in (
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "C:/Windows/Fonts/malgun.ttf",
    ):
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _draw_png_legend(draw, analysis: dict[str, Any], width: int) -> None:
    font = _default_font(16)
    rows = analysis.get("layers", [])[:10]
    box_width = 350
    box_height = 42 + len(rows) * 24
    x0 = width - box_width - 24
    y0 = 24
    draw.rectangle((x0, y0, x0 + box_width, y0 + box_height), fill=(255, 250, 240, 232), outline=(215, 208, 194, 255))
    draw.text((x0 + 16, y0 + 14), "Top layers", fill=(31, 41, 51, 255), font=font)
    small = _default_font(13)
    for index, layer in enumerate(rows):
        y = y0 + 42 + index * 24
        name = str(layer.get("name", "0"))
        draw.rectangle((x0 + 16, y, x0 + 28, y + 12), fill=_hex_to_rgba(_layer_color(name), 255))
        draw.text((x0 + 38, y - 2), f"{name} ({layer.get('entity_count', 0)})", fill=(82, 97, 107, 255), font=small)


if __name__ == "__main__":
    raise SystemExit(main())
