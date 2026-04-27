from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any


@dataclass(frozen=True)
class Point:
    x: float
    y: float
    z: float = 0.0


@dataclass(frozen=True)
class Bounds:
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @classmethod
    def from_points(cls, points: list[Point]) -> "Bounds | None":
        if not points:
            return None
        xs = [point.x for point in points]
        ys = [point.y for point in points]
        return cls(min(xs), min(ys), max(xs), max(ys))

    @property
    def center(self) -> Point:
        return Point((self.min_x + self.max_x) / 2, (self.min_y + self.max_y) / 2)

    def distance_to(self, point: Point) -> float:
        dx = max(self.min_x - point.x, 0.0, point.x - self.max_x)
        dy = max(self.min_y - point.y, 0.0, point.y - self.max_y)
        return (dx * dx + dy * dy) ** 0.5


@dataclass
class TextRecord:
    id: str
    kind: str
    text: str
    layer: str
    insert: Point
    rotation: float | None = None
    height: float | None = None
    width: float | None = None
    handle: str | None = None
    block_id: str | None = None
    tag: str | None = None


@dataclass
class AttributeRecord:
    tag: str
    text: str
    insert: Point | None = None
    layer: str | None = None


@dataclass
class BlockRecord:
    id: str
    name: str
    layer: str
    insert: Point
    rotation: float | None = None
    xscale: float | None = None
    yscale: float | None = None
    handle: str | None = None
    attributes: list[AttributeRecord] = field(default_factory=list)


@dataclass
class GeometryRecord:
    id: str
    kind: str
    layer: str
    bounds: Bounds | None
    handle: str | None = None
    points: list[Point] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LinkRecord:
    text_id: str
    target_id: str
    target_kind: str
    distance: float
    same_layer: bool
    score: float


@dataclass
class LayerSummary:
    name: str
    entity_count: int = 0
    text_count: int = 0
    block_count: int = 0
    geometry_count: int = 0
    type_counts: dict[str, int] = field(default_factory=dict)


@dataclass
class CadAnalysis:
    source_file: str
    format: str
    dxf_version: str | None
    entity_counts: dict[str, int]
    layers: list[LayerSummary]
    texts: list[TextRecord]
    blocks: list[BlockRecord]
    geometries: list[GeometryRecord]
    links: list[LinkRecord]
    notes: list[str] = field(default_factory=list)


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    return value
