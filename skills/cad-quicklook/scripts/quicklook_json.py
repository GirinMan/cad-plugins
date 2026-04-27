#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize normalized CAD analysis JSON.")
    parser.add_argument("analysis_json", type=Path)
    parser.add_argument("--top", type=int, default=8)
    args = parser.parse_args()

    data = json.loads(args.analysis_json.read_text(encoding="utf-8"))
    counts = data.get("entity_counts", {})
    layers = data.get("layers", [])
    texts = data.get("texts", [])
    blocks = data.get("blocks", [])
    geometries = data.get("geometries", [])
    source = Path(data.get("source_file", args.analysis_json)).name
    version = data.get("dxf_version") or "unknown"

    print(f"source: {source}")
    print(f"format: {data.get('format', 'unknown')} / {version}")
    print(f"counts: layers={len(layers)}, texts={len(texts)}, blocks={len(blocks)}, geometries={len(geometries)}, links={len(data.get('links', []))}")
    print("entity_counts:")
    for kind, count in list(counts.items())[: args.top]:
        print(f"  {kind}: {count}")
    print("top_layers:")
    for layer in layers[: args.top]:
        print(
            "  "
            f"{layer.get('name')}: entities={layer.get('entity_count', 0)}, "
            f"texts={layer.get('text_count', 0)}, "
            f"blocks={layer.get('block_count', 0)}, "
            f"geometries={layer.get('geometry_count', 0)}"
        )
    print("sample_texts:")
    for text in texts[: min(args.top, 10)]:
        label = str(text.get("text", "")).replace("\n", " ")[:80]
        if label:
            print(f"  [{text.get('layer')}] {label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
