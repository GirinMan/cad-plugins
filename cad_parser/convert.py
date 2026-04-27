from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from cad_parser.converters import CadConversionError, convert_dwg_to_dxf, detect_converters


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert DWG files to canonical DXF for CAD analysis.")
    parser.add_argument("inputs", nargs="*", type=Path)
    parser.add_argument("--input-dir", type=Path, help="Convert DWG files from this directory.")
    parser.add_argument("--pattern", default="*.dwg")
    parser.add_argument("--recursive", action="store_true")
    parser.add_argument("--out", type=Path, help="Destination DXF file for single-input conversion.")
    parser.add_argument("--converted-dir", type=Path, default=Path("data/intermediate"))
    parser.add_argument("--converter", choices=["auto", "oda", "libredwg"], default="auto")
    parser.add_argument("--dxf-version", default="R2018")
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--no-validate", action="store_true")
    parser.add_argument("--manifest", type=Path, help="Write conversion results as JSON.")
    parser.add_argument("--keep-going", action="store_true", help="Continue batch conversion after a failed file.")
    parser.add_argument("--oda-path", type=Path)
    parser.add_argument("--dwgread-path", type=Path)
    parser.add_argument("--check", action="store_true", help="Show converter availability and exit.")
    args = parser.parse_args()

    if args.check:
        for item in detect_converters(oda_path=args.oda_path, dwgread_path=args.dwgread_path):
            status = "available" if item.available else "missing"
            location = f" ({item.path})" if item.path else ""
            detail = f" - {item.detail}" if item.detail else ""
            print(f"{item.name}: {status}{location}{detail}")
        return 0

    inputs = _resolve_inputs(args.inputs, args.input_dir, args.pattern, args.recursive)
    if not inputs:
        parser.error("at least one input or --input-dir is required unless --check is used")
    if args.out and len(inputs) != 1:
        parser.error("--out can only be used with a single input")

    results: list[dict[str, object]] = []
    failed = False
    for source in inputs:
        output_file = args.out if args.out else None
        try:
            result = convert_dwg_to_dxf(
                source,
                args.converted_dir,
                converter=args.converter,
                dxf_version=args.dxf_version,
                replace=args.replace,
                output_file=output_file,
                oda_path=args.oda_path,
                dwgread_path=args.dwgread_path,
                validate=not args.no_validate,
            )
            record = _result_record(result)
            results.append(record)
            _print_result(record)
        except CadConversionError as exc:
            failed = True
            record = {"source_file": str(source), "ok": False, "error": str(exc)}
            results.append(record)
            print(f"source={source}")
            print(f"ok=false")
            print(f"error={exc}")
            if not args.keep_going:
                break

    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return 1 if failed else 0


def _resolve_inputs(inputs: list[Path], input_dir: Path | None, pattern: str, recursive: bool) -> list[Path]:
    resolved = list(inputs)
    if input_dir:
        iterator = input_dir.rglob(pattern) if recursive else input_dir.glob(pattern)
        resolved.extend(sorted(path for path in iterator if path.is_file()))
    return resolved


def _result_record(result) -> dict[str, object]:
    record = asdict(result)
    record["source_file"] = str(result.source_file)
    record["dxf_file"] = str(result.dxf_file)
    if result.validation:
        record["validation"]["dxf_file"] = str(result.validation.dxf_file)
    record["ok"] = True
    return record


def _print_result(record: dict[str, object]) -> None:
    print(f"source={record['source_file']}")
    print(f"dxf={record['dxf_file']}")
    print(f"converter={record['converter']}")
    print("ok=true")
    validation = record.get("validation")
    if isinstance(validation, dict):
        print(f"readable={str(validation.get('readable')).lower()}")
        print(f"layers={validation.get('layer_count')}")
        print(f"texts={validation.get('text_count')}")
        print(f"blocks={validation.get('block_count')}")
        print(f"geometries={validation.get('geometry_count')}")
    for note in record.get("notes", []):
        print(f"note={note}")


if __name__ == "__main__":
    raise SystemExit(main())
