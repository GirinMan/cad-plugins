#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:
    raise SystemExit("Pillow is required: pip install pillow") from exc

PALETTE = [
    "#006D77", "#E29578", "#2A9D8F", "#E9C46A", "#264653",
    "#D62828", "#457B9D", "#6A994E", "#BC6C25", "#7B2CBF",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Render normalized CAD JSON to PNG.")
    parser.add_argument("analysis_json", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--view", choices=["full", "clipped", "linework", "blocks", "labels", "layer"], default="linework")
    parser.add_argument("--layer")
    parser.add_argument("--width", type=int, default=2400)
    parser.add_argument("--height", type=int, default=1800)
    parser.add_argument("--clip-percentile", type=float, default=None)
    parser.add_argument("--max-labels", type=int, default=8000)
    args = parser.parse_args()

    data = json.loads(args.analysis_json.read_text(encoding="utf-8"))
    clip = args.clip_percentile
    if clip is None:
        clip = 0.0 if args.view == "full" else 0.01
    render_png(data, args.out, args.view, args.layer, args.width, args.height, clip, args.max_labels)
    print(f"out={args.out}")
    print(f"view={args.view}")
    print(f"clip_percentile={clip}")
    return 0


def render_png(data: dict[str, Any], out: Path, view: str, layer: str | None, width: int, height: int, clip: float, max_labels: int) -> None:
    bounds = analysis_bounds(data, clip, layer)
    transform = Transform(bounds, width, height, 40)
    image = Image.new("RGB", (width, height), "#fbfaf7")
    draw = ImageDraw.Draw(image, "RGBA")

    draw_geometries = view in {"full", "clipped", "linework", "blocks", "labels", "layer"}
    draw_blocks = view in {"blocks", "labels", "layer"}
    draw_texts = view in {"labels", "layer"}

    if draw_geometries:
        for geom in data.get("geometries", []):
            if not include_layer(geom, layer):
                continue
            b = geom.get("bounds")
            points = geom.get("points") or []
            if not b or len(points) < 2 or not intersects(b, transform):
                continue
            pixels = [transform.point(p) for p in points]
            if geom.get("metadata", {}).get("closed") and pixels:
                pixels.append(pixels[0])
            draw.line(pixels, fill=rgba(color_for(geom.get("layer", "0")), 190), width=2)

    if draw_blocks:
        for block in data.get("blocks", []):
            if not include_layer(block, layer):
                continue
            point = block.get("insert")
            if not point or not inside(point, transform):
                continue
            x, y = transform.point(point)
            draw.rectangle((x - 3, y - 3, x + 3, y + 3), fill=rgba(color_for(block.get("layer", "0")), 220))

    if draw_texts:
        font = default_font(14)
        count = 0
        for text in data.get("texts", []):
            if count >= max_labels or not include_layer(text, layer):
                continue
            label = str(text.get("text", "")).strip()
            point = text.get("insert")
            if not label or not point or not inside(point, transform):
                continue
            x, y = transform.point(point)
            draw.text((x + 5, y - 12), label[:24], fill=(31, 41, 51, 220), font=font)
            count += 1

    draw_legend(draw, data, width)
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out)


class Transform:
    def __init__(self, bounds: tuple[float, float, float, float], width: int, height: int, padding: int) -> None:
        self.min_x, self.min_y, self.max_x, self.max_y = bounds
        self.width = width
        self.height = height
        self.padding = padding
        drawing_width = max(self.max_x - self.min_x, 1.0)
        drawing_height = max(self.max_y - self.min_y, 1.0)
        available_width = max(width - padding * 2, 1)
        available_height = max(height - padding * 2, 1)
        self.scale = min(available_width / drawing_width, available_height / drawing_height)
        self.offset_x = (available_width - drawing_width * self.scale) / 2
        self.offset_y = (available_height - drawing_height * self.scale) / 2

    def point(self, point: dict[str, Any]) -> tuple[float, float]:
        x = self.padding + (float(point["x"]) - self.min_x) * self.scale + self.offset_x
        y = self.padding + (self.max_y - float(point["y"])) * self.scale + self.offset_y
        return x, y


def analysis_bounds(data: dict[str, Any], clip: float, layer: str | None) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    for geom in data.get("geometries", []):
        if not include_layer(geom, layer):
            continue
        b = geom.get("bounds")
        if b:
            xs.extend([float(b["min_x"]), float(b["max_x"])])
            ys.extend([float(b["min_y"]), float(b["max_y"])])
    for key in ("blocks", "texts"):
        for item in data.get(key, []):
            if not include_layer(item, layer):
                continue
            p = item.get("insert")
            if p:
                xs.append(float(p["x"]))
                ys.append(float(p["y"]))
    if not xs or not ys:
        return 0, 0, 1, 1
    if clip > 0:
        xs.sort(); ys.sort()
        lower = min(max(clip, 0), 0.49)
        upper = 1 - lower
        return quantile(xs, lower), quantile(ys, lower), quantile(xs, upper), quantile(ys, upper)
    return min(xs), min(ys), max(xs), max(ys)


def include_layer(item: dict[str, Any], layer: str | None) -> bool:
    if not layer:
        return True
    return layer.lower() in str(item.get("layer", "")).lower()


def quantile(values: list[float], fraction: float) -> float:
    return values[int((len(values) - 1) * fraction)]


def intersects(bounds: dict[str, Any], t: Transform) -> bool:
    return not (float(bounds["max_x"]) < t.min_x or float(bounds["min_x"]) > t.max_x or float(bounds["max_y"]) < t.min_y or float(bounds["min_y"]) > t.max_y)


def inside(point: dict[str, Any], t: Transform) -> bool:
    return t.min_x <= float(point["x"]) <= t.max_x and t.min_y <= float(point["y"]) <= t.max_y


def color_for(layer: str) -> str:
    digest = hashlib.sha1(str(layer).encode("utf-8")).digest()
    return PALETTE[digest[0] % len(PALETTE)]


def rgba(color: str, alpha: int) -> tuple[int, int, int, int]:
    c = color.lstrip("#")
    return int(c[:2], 16), int(c[2:4], 16), int(c[4:6], 16), alpha


def default_font(size: int):
    for path in ("/System/Library/Fonts/AppleSDGothicNeo.ttc", "C:/Windows/Fonts/malgun.ttf"):
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def draw_legend(draw: ImageDraw.ImageDraw, data: dict[str, Any], width: int) -> None:
    rows = data.get("layers", [])[:10]
    x0, y0 = width - 374, 24
    box_height = 42 + len(rows) * 24
    draw.rectangle((x0, y0, x0 + 350, y0 + box_height), fill=(255, 250, 240, 232), outline=(215, 208, 194, 255))
    font = default_font(13)
    draw.text((x0 + 16, y0 + 14), "Top layers", fill=(31, 41, 51, 255), font=font)
    for idx, row in enumerate(rows):
        y = y0 + 42 + idx * 24
        name = str(row.get("name", "0"))
        draw.rectangle((x0 + 16, y, x0 + 28, y + 12), fill=rgba(color_for(name), 255))
        draw.text((x0 + 38, y - 2), f"{name} ({row.get('entity_count', 0)})", fill=(82, 97, 107, 255), font=font)


if __name__ == "__main__":
    raise SystemExit(main())
