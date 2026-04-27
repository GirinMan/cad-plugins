from __future__ import annotations

from collections import Counter, defaultdict
from math import cos, radians, sin
from pathlib import Path

import ezdxf
from ezdxf import recover
from ezdxf.addons import odafc
from ezdxf.lldxf.const import DXFStructureError, DXFVersionError

from cad_parser.models import (
    AttributeRecord,
    BlockRecord,
    Bounds,
    CadAnalysis,
    GeometryRecord,
    LayerSummary,
    LinkRecord,
    Point,
    TextRecord,
)

TEXT_TYPES = {"TEXT", "MTEXT", "ATTRIB", "ATTDEF"}
GEOMETRY_TYPES = {
    "LINE",
    "LWPOLYLINE",
    "POLYLINE",
    "CIRCLE",
    "ARC",
    "POINT",
    "HATCH",
    "DIMENSION",
    "SPLINE",
    "ELLIPSE",
}


class UnsupportedCadFormatError(RuntimeError):
    """Raised when the local machine cannot read a CAD input format yet."""


def analyze_cad_file(path: str | Path, max_links_per_text: int = 3) -> CadAnalysis:
    source = Path(path)
    doc, notes = _load_document(source)
    msp = doc.modelspace()

    entity_counts: Counter[str] = Counter()
    layer_summaries: dict[str, LayerSummary] = defaultdict(lambda: LayerSummary(name=""))
    texts: list[TextRecord] = []
    blocks: list[BlockRecord] = []
    geometries: list[GeometryRecord] = []

    for entity in msp:
        kind = entity.dxftype()
        layer = _layer(entity)
        entity_counts[kind] += 1
        summary = layer_summaries[layer]
        summary.name = layer
        summary.entity_count += 1
        summary.type_counts[kind] = summary.type_counts.get(kind, 0) + 1

        if kind in {"TEXT", "MTEXT"}:
            texts.append(_text_record(entity, f"text:{len(texts) + 1}"))
            summary.text_count += 1
        elif kind == "INSERT":
            block = _block_record(entity, f"block:{len(blocks) + 1}")
            blocks.append(block)
            summary.block_count += 1
            for attrib in getattr(entity, "attribs", []):
                texts.append(_text_record(attrib, f"text:{len(texts) + 1}", block_id=block.id))
                summary.text_count += 1
        elif kind in {"ATTRIB", "ATTDEF"}:
            texts.append(_text_record(entity, f"text:{len(texts) + 1}"))
            summary.text_count += 1
        elif kind in GEOMETRY_TYPES:
            geometries.append(_geometry_record(entity, f"geometry:{len(geometries) + 1}"))
            summary.geometry_count += 1

    links = link_texts(texts, geometries, blocks, max_links_per_text=max_links_per_text)
    return CadAnalysis(
        source_file=str(source),
        format=source.suffix.lower().lstrip("."),
        dxf_version=getattr(doc, "dxfversion", None),
        entity_counts=dict(entity_counts.most_common()),
        layers=sorted(layer_summaries.values(), key=lambda layer: layer.entity_count, reverse=True),
        texts=texts,
        blocks=blocks,
        geometries=geometries,
        links=links,
        notes=notes,
    )


def link_texts(
    texts: list[TextRecord],
    geometries: list[GeometryRecord],
    blocks: list[BlockRecord],
    max_links_per_text: int = 3,
) -> list[LinkRecord]:
    if max_links_per_text <= 0:
        return []
    links: list[LinkRecord] = []
    for text in texts:
        candidates: list[LinkRecord] = []
        for geometry in geometries:
            if geometry.bounds is None:
                continue
            distance = geometry.bounds.distance_to(text.insert)
            candidates.append(_link_candidate(text, geometry.id, "geometry", geometry.layer, distance))
        for block in blocks:
            if block.id == text.block_id:
                continue
            distance = _point_distance(text.insert, block.insert)
            candidates.append(_link_candidate(text, block.id, "block", block.layer, distance))
        candidates.sort(key=lambda item: (item.score, item.distance, item.target_id))
        links.extend(candidates[:max_links_per_text])
    return links


def _load_document(path: Path):
    suffix = path.suffix.lower()
    if suffix == ".dxf":
        try:
            return ezdxf.readfile(path), []
        except (DXFStructureError, DXFVersionError):
            doc, auditor = recover.readfile(path)
            notes = [f"Recovered DXF with {len(auditor.errors)} auditor errors."]
            return doc, notes
    if suffix == ".dwg":
        if not odafc.is_installed():
            raise UnsupportedCadFormatError(
                "DWG parsing needs ODA File Converter on PATH or configured in ezdxf. "
                "Convert this DWG to DXF first, then run the analyzer again."
            )
        return odafc.readfile(path), ["Loaded DWG through ODA File Converter."]
    raise UnsupportedCadFormatError(f"Unsupported CAD extension: {suffix}")


def _text_record(entity, record_id: str, block_id: str | None = None) -> TextRecord:
    text = entity.plain_text() if hasattr(entity, "plain_text") else getattr(entity.dxf, "text", "")
    return TextRecord(
        id=record_id,
        kind=entity.dxftype(),
        text=text.strip(),
        layer=_layer(entity),
        insert=_point(getattr(entity.dxf, "insert", getattr(entity.dxf, "align_point", (0, 0, 0)))),
        rotation=_float_attr(entity, "rotation"),
        height=_float_attr(entity, "height"),
        width=_float_attr(entity, "width"),
        handle=getattr(entity.dxf, "handle", None),
        block_id=block_id,
        tag=getattr(entity.dxf, "tag", None),
    )


def _block_record(entity, record_id: str) -> BlockRecord:
    attributes = [
        AttributeRecord(
            tag=getattr(attrib.dxf, "tag", ""),
            text=getattr(attrib.dxf, "text", "").strip(),
            insert=_point(getattr(attrib.dxf, "insert", (0, 0, 0))),
            layer=_layer(attrib),
        )
        for attrib in getattr(entity, "attribs", [])
    ]
    return BlockRecord(
        id=record_id,
        name=getattr(entity.dxf, "name", ""),
        layer=_layer(entity),
        insert=_point(getattr(entity.dxf, "insert", (0, 0, 0))),
        rotation=_float_attr(entity, "rotation"),
        xscale=_float_attr(entity, "xscale"),
        yscale=_float_attr(entity, "yscale"),
        handle=getattr(entity.dxf, "handle", None),
        attributes=attributes,
    )


def _geometry_record(entity, record_id: str) -> GeometryRecord:
    kind = entity.dxftype()
    points = _geometry_points(entity)
    bounds = Bounds.from_points(points)
    metadata = _geometry_metadata(entity)
    return GeometryRecord(
        id=record_id,
        kind=kind,
        layer=_layer(entity),
        bounds=bounds,
        handle=getattr(entity.dxf, "handle", None),
        points=points,
        metadata=metadata,
    )


def _geometry_points(entity) -> list[Point]:
    kind = entity.dxftype()
    if kind == "LINE":
        return [_point(entity.dxf.start), _point(entity.dxf.end)]
    if kind == "LWPOLYLINE":
        return [Point(float(x), float(y), 0.0) for x, y in entity.get_points("xy")]
    if kind == "POLYLINE":
        return [_point(vertex.dxf.location) for vertex in entity.vertices]
    if kind == "POINT":
        return [_point(entity.dxf.location)]
    if kind == "CIRCLE":
        center = _point(entity.dxf.center)
        radius = float(entity.dxf.radius)
        return [
            Point(center.x - radius, center.y),
            Point(center.x + radius, center.y),
            Point(center.x, center.y - radius),
            Point(center.x, center.y + radius),
        ]
    if kind == "ARC":
        return _arc_points(entity)
    return []


def _arc_points(entity) -> list[Point]:
    center = _point(entity.dxf.center)
    radius = float(entity.dxf.radius)
    start = float(entity.dxf.start_angle)
    end = float(entity.dxf.end_angle)
    if end < start:
        end += 360.0
    angles = [start, end]
    angles.extend(angle for angle in (0, 90, 180, 270, 360) if start <= angle <= end)
    points = []
    for angle in angles:
        rad = radians(angle)
        points.append(Point(center.x + radius * cos(rad), center.y + radius * sin(rad), center.z))
    return points


def _geometry_metadata(entity) -> dict[str, float | str | bool]:
    kind = entity.dxftype()
    if kind in {"CIRCLE", "ARC"}:
        metadata: dict[str, float | str | bool] = {"radius": float(entity.dxf.radius)}
        if kind == "ARC":
            metadata["start_angle"] = float(entity.dxf.start_angle)
            metadata["end_angle"] = float(entity.dxf.end_angle)
        return metadata
    if kind in {"LWPOLYLINE", "POLYLINE"}:
        return {"closed": bool(getattr(entity, "is_closed", False))}
    return {}


def _link_candidate(text: TextRecord, target_id: str, target_kind: str, target_layer: str, distance: float) -> LinkRecord:
    same_layer = text.layer == target_layer
    score = distance * (0.75 if same_layer else 1.0)
    return LinkRecord(
        text_id=text.id,
        target_id=target_id,
        target_kind=target_kind,
        distance=round(distance, 6),
        same_layer=same_layer,
        score=round(score, 6),
    )


def _point(value) -> Point:
    if hasattr(value, "x"):
        return Point(float(value.x), float(value.y), float(getattr(value, "z", 0.0)))
    items = list(value)
    if len(items) == 2:
        items.append(0.0)
    return Point(float(items[0]), float(items[1]), float(items[2]))


def _point_distance(left: Point, right: Point) -> float:
    dx = left.x - right.x
    dy = left.y - right.y
    return (dx * dx + dy * dy) ** 0.5


def _layer(entity) -> str:
    return getattr(entity.dxf, "layer", "0") or "0"


def _float_attr(entity, name: str) -> float | None:
    value = getattr(entity.dxf, name, None)
    return None if value is None else float(value)
