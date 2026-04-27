#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect normalized CAD analysis JSON.")
    parser.add_argument("analysis_json", type=Path)
    parser.add_argument("--layer")
    parser.add_argument("--text")
    parser.add_argument("--block")
    parser.add_argument("--blocks", action="store_true")
    parser.add_argument("--top", type=int, default=20)
    args = parser.parse_args()

    data = json.loads(args.analysis_json.read_text(encoding="utf-8"))
    if args.blocks:
        summarize_blocks(data, args.top)
        return 0
    if args.layer:
        inspect_layer(data, args.layer, args.top)
        return 0
    if args.text:
        inspect_text(data, args.text, args.top)
        return 0
    if args.block:
        inspect_block(data, args.block, args.top)
        return 0
    parser.error("provide --layer, --text, --block, or --blocks")


def inspect_layer(data: dict, layer_query: str, top: int) -> None:
    q = layer_query.lower()
    texts = [item for item in data.get("texts", []) if q in str(item.get("layer", "")).lower()]
    blocks = [item for item in data.get("blocks", []) if q in str(item.get("layer", "")).lower()]
    geometries = [item for item in data.get("geometries", []) if q in str(item.get("layer", "")).lower()]
    print(f"layer_query: {layer_query}")
    print(f"matches: texts={len(texts)}, blocks={len(blocks)}, geometries={len(geometries)}")
    print_samples(texts, top)


def inspect_text(data: dict, text_query: str, top: int) -> None:
    q = text_query.lower()
    matches = [item for item in data.get("texts", []) if q in str(item.get("text", "")).lower()]
    layer_counts = Counter(str(item.get("layer", "")) for item in matches)
    print(f"text_query: {text_query}")
    print(f"matches: {len(matches)}")
    print("top_layers:")
    for layer, count in layer_counts.most_common(10):
        print(f"  {layer}: {count}")
    print_samples(matches, top)


def inspect_block(data: dict, block_query: str, top: int) -> None:
    q = block_query.lower()
    matches = [item for item in data.get("blocks", []) if q in str(item.get("name", "")).lower() or q in str(item.get("layer", "")).lower()]
    layer_counts = Counter(str(item.get("layer", "")) for item in matches)
    print(f"block_query: {block_query}")
    print(f"matches: {len(matches)}")
    for layer, count in layer_counts.most_common(10):
        print(f"  {layer}: {count}")
    for item in matches[:top]:
        point = item.get("insert", {})
        print(f"  [{item.get('layer')}] {item.get('name')} @ ({point.get('x')}, {point.get('y')})")


def summarize_blocks(data: dict, top: int) -> None:
    names = Counter(str(item.get("name", "")) for item in data.get("blocks", []))
    layers = Counter(str(item.get("layer", "")) for item in data.get("blocks", []))
    print("top_block_names:")
    for name, count in names.most_common(top):
        print(f"  {name}: {count}")
    print("top_block_layers:")
    for layer, count in layers.most_common(top):
        print(f"  {layer}: {count}")


def print_samples(items: list[dict], top: int) -> None:
    print("samples:")
    for item in items[:top]:
        point = item.get("insert", {})
        text = str(item.get("text", "")).replace("\n", " ")[:120]
        print(f"  [{item.get('layer')}] {item.get('kind')} @ ({point.get('x')}, {point.get('y')}): {text}")


if __name__ == "__main__":
    raise SystemExit(main())
