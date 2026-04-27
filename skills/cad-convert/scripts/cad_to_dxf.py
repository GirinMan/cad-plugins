#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

ODA_PATH_ENV = "CAD_PARSER_ODA_PATH"
DWGREAD_PATH_ENV = "CAD_PARSER_DWGREAD_PATH"
TEXT_TYPES = {"TEXT", "MTEXT", "ATTRIB", "ATTDEF"}
GEOMETRY_TYPES = {"LINE", "LWPOLYLINE", "POLYLINE", "CIRCLE", "ARC", "POINT", "HATCH", "DIMENSION", "SPLINE", "ELLIPSE"}
ODA_VERSION_MAP = {
    "R12": "ACAD12",
    "R13": "ACAD13",
    "R14": "ACAD14",
    "R2000": "ACAD2000",
    "R2004": "ACAD2004",
    "R2007": "ACAD2007",
    "R2010": "ACAD2010",
    "R2013": "ACAD2013",
    "R2018": "ACAD2018",
    "AC1015": "ACAD2000",
    "AC1032": "ACAD2018",
}


class ConvertError(RuntimeError):
    pass


@dataclass
class Validation:
    readable: bool
    file_size: int
    dxf_version: str | None = None
    layer_count: int = 0
    text_count: int = 0
    block_count: int = 0
    geometry_count: int = 0
    entity_counts: dict[str, int] | None = None
    error: str | None = None


@dataclass
class Record:
    source_file: str
    dxf_file: str | None
    converter: str | None
    ok: bool
    validation: Validation | None = None
    error: str | None = None


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert DWG/DXF inputs to canonical DXF with validation.")
    parser.add_argument("inputs", nargs="*", type=Path)
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--pattern", default="*.dwg")
    parser.add_argument("--recursive", action="store_true")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("data/intermediate"))
    parser.add_argument("--converter", choices=["auto", "oda", "libredwg"], default="auto")
    parser.add_argument("--dxf-version", default="R2018")
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--keep-going", action="store_true")
    parser.add_argument("--no-validate", action="store_true")
    parser.add_argument("--oda-path", type=Path)
    parser.add_argument("--dwgread-path", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.check:
        print_check("oda", resolve_oda(args.oda_path), ODA_PATH_ENV)
        print_check("libredwg", resolve_dwgread(args.dwgread_path), DWGREAD_PATH_ENV)
        return 0

    inputs = resolve_inputs(args.inputs, args.input_dir, args.pattern, args.recursive)
    if not inputs:
        parser.error("provide at least one input or --input-dir")
    if args.out and len(inputs) != 1:
        parser.error("--out can only be used with one input")

    records: list[Record] = []
    failed = False
    for source in inputs:
        try:
            destination = args.out or args.out_dir / f"{source.stem}.dxf"
            record = canonicalize(
                source,
                destination,
                converter=args.converter,
                dxf_version=args.dxf_version,
                replace=args.replace,
                validate=not args.no_validate,
                oda_path=args.oda_path,
                dwgread_path=args.dwgread_path,
            )
        except ConvertError as exc:
            failed = True
            record = Record(str(source), None, None, False, error=str(exc))
            if not args.keep_going:
                records.append(record)
                print_record(record)
                break
        records.append(record)
        print_record(record)

    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps([asdict(record) for record in records], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 1 if failed else 0


def canonicalize(
    source: Path,
    destination: Path,
    converter: str,
    dxf_version: str,
    replace: bool,
    validate: bool,
    oda_path: Path | None,
    dwgread_path: Path | None,
) -> Record:
    if not source.exists():
        raise ConvertError(f"source does not exist: {source}")
    suffix = source.suffix.lower()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if suffix == ".dxf":
        if destination.resolve() != source.resolve():
            if destination.exists() and not replace:
                raise ConvertError(f"destination exists: {destination}")
            shutil.copy2(source, destination)
            used = "copy"
        else:
            used = "existing"
    elif suffix == ".dwg":
        used = convert_dwg(source, destination, converter, dxf_version, replace, oda_path, dwgread_path)
    else:
        raise ConvertError(f"unsupported extension: {suffix}")
    validation = validate_dxf(destination) if validate else None
    if validation and not validation.readable:
        raise ConvertError(f"DXF validation failed: {validation.error}")
    return Record(str(source), str(destination), used, True, validation=validation)


def convert_dwg(source: Path, destination: Path, converter: str, dxf_version: str, replace: bool, oda_path: Path | None, dwgread_path: Path | None) -> str:
    if destination.exists():
        if replace:
            destination.unlink()
        else:
            raise ConvertError(f"destination exists: {destination}")
    errors: list[str] = []
    candidates = ["oda", "libredwg"] if converter == "auto" else [converter]
    for candidate in candidates:
        try:
            if candidate == "oda":
                run_oda(source, destination, dxf_version, oda_path)
            elif candidate == "libredwg":
                run_libredwg(source, destination, dwgread_path)
            else:
                raise ConvertError(f"unknown converter: {candidate}")
            return candidate
        except ConvertError as exc:
            errors.append(f"{candidate}: {exc}")
    raise ConvertError("; ".join(errors))


def run_oda(source: Path, destination: Path, dxf_version: str, oda_path: Path | None) -> None:
    executable = resolve_oda(oda_path)
    if not executable:
        raise ConvertError(f"ODA File Converter missing; set --oda-path or {ODA_PATH_ENV}")
    version = ODA_VERSION_MAP.get(dxf_version.upper(), dxf_version.upper())
    with tempfile.TemporaryDirectory(prefix="cad_convert_oda_") as tmp:
        input_dir = Path(tmp) / "input"
        output_dir = Path(tmp) / "output"
        input_dir.mkdir()
        output_dir.mkdir()
        temp_source = input_dir / "source.dwg"
        shutil.copy2(source, temp_source)
        command = [executable, str(input_dir), str(output_dir), version, "DXF", "0", "1", "*.dwg"]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise ConvertError((completed.stderr or completed.stdout or f"exit {completed.returncode}").strip())
        outputs = sorted(output_dir.glob("*.dxf"))
        if not outputs:
            raise ConvertError("ODA completed without creating DXF")
        shutil.move(str(outputs[0]), destination)


def run_libredwg(source: Path, destination: Path, dwgread_path: Path | None) -> None:
    executable = resolve_dwgread(dwgread_path)
    if not executable:
        raise ConvertError(f"LibreDWG dwgread missing; set --dwgread-path or {DWGREAD_PATH_ENV}")
    completed = subprocess.run([executable, "-O", "DXF", "-o", str(destination), str(source)], capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise ConvertError((completed.stderr or completed.stdout or f"exit {completed.returncode}").strip())
    if not destination.exists():
        raise ConvertError("dwgread completed without creating DXF")


def validate_dxf(path: Path) -> Validation:
    size = path.stat().st_size if path.exists() else 0
    if not path.exists():
        return Validation(False, size, error="file does not exist")
    if size == 0:
        return Validation(False, size, error="file is empty")
    try:
        import ezdxf

        doc = ezdxf.readfile(path)
        entities = list(doc.modelspace())
    except ModuleNotFoundError as exc:
        if exc.name == "ezdxf":
            return Validation(True, size, error="ezdxf not installed; structural validation skipped")
        return Validation(False, size, error=f"{type(exc).__name__}: {exc}")
    except Exception as exc:
        return Validation(False, size, error=f"{type(exc).__name__}: {exc}")
    counts = Counter(entity.dxftype() for entity in entities)
    layers = {getattr(entity.dxf, "layer", "0") or "0" for entity in entities}
    return Validation(
        True,
        size,
        dxf_version=getattr(doc, "dxfversion", None),
        layer_count=len(layers),
        text_count=sum(count for kind, count in counts.items() if kind in TEXT_TYPES),
        block_count=counts.get("INSERT", 0),
        geometry_count=sum(count for kind, count in counts.items() if kind in GEOMETRY_TYPES),
        entity_counts=dict(counts.most_common()),
    )


def resolve_inputs(inputs: list[Path], input_dir: Path | None, pattern: str, recursive: bool) -> list[Path]:
    resolved = list(inputs)
    if input_dir:
        iterator = input_dir.rglob(pattern) if recursive else input_dir.glob(pattern)
        resolved.extend(sorted(path for path in iterator if path.is_file()))
    return resolved


def resolve_oda(path: Path | None) -> str | None:
    return first_existing(
        path,
        os.environ.get(ODA_PATH_ENV),
        shutil.which("ODAFileConverter"),
        r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe",
        "/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter",
    )


def resolve_dwgread(path: Path | None) -> str | None:
    return first_existing(path, os.environ.get(DWGREAD_PATH_ENV), shutil.which("dwgread"))


def first_existing(*paths: object) -> str | None:
    for path in paths:
        if not path:
            continue
        candidate = Path(path).expanduser()
        if candidate.is_file():
            return str(candidate)
    return None


def print_check(name: str, path: str | None, env: str) -> None:
    status = "available" if path else "missing"
    detail = f" ({path})" if path else f" - set {env} or pass an explicit path"
    print(f"{name}: {status}{detail}")


def print_record(record: Record) -> None:
    print(f"source={record.source_file}")
    print(f"ok={str(record.ok).lower()}")
    if record.dxf_file:
        print(f"dxf={record.dxf_file}")
    if record.converter:
        print(f"converter={record.converter}")
    if record.validation:
        print(f"readable={str(record.validation.readable).lower()}")
        print(f"layers={record.validation.layer_count}")
        print(f"texts={record.validation.text_count}")
        print(f"blocks={record.validation.block_count}")
        print(f"geometries={record.validation.geometry_count}")
    if record.error:
        print(f"error={record.error}")


if __name__ == "__main__":
    raise SystemExit(main())
