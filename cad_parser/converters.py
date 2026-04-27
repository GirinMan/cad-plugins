from __future__ import annotations

from collections import Counter
import os
import platform
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import ezdxf
from ezdxf.addons import odafc

ODA_PATH_ENV = "CAD_PARSER_ODA_PATH"
DWGREAD_PATH_ENV = "CAD_PARSER_DWGREAD_PATH"
TEXT_TYPES = {"TEXT", "MTEXT", "ATTRIB", "ATTDEF"}
GEOMETRY_TYPES = {"LINE", "LWPOLYLINE", "POLYLINE", "CIRCLE", "ARC", "POINT", "HATCH", "DIMENSION", "SPLINE", "ELLIPSE"}


class CadConversionError(RuntimeError):
    """Raised when a CAD file cannot be converted by installed local tools."""


@dataclass(frozen=True)
class ConverterAvailability:
    name: str
    available: bool
    path: str | None = None
    detail: str | None = None


@dataclass(frozen=True)
class ConversionValidation:
    dxf_file: Path
    readable: bool
    file_size: int
    dxf_version: str | None = None
    entity_counts: dict[str, int] = field(default_factory=dict)
    layer_count: int = 0
    text_count: int = 0
    block_count: int = 0
    geometry_count: int = 0
    error: str | None = None


@dataclass(frozen=True)
class ConversionResult:
    source_file: Path
    dxf_file: Path
    converter: str
    notes: list[str]
    diagnostics: list[ConverterAvailability] = field(default_factory=list)
    validation: ConversionValidation | None = None


def prepare_analysis_input(
    source: str | Path,
    out_dir: str | Path,
    converter: str = "auto",
    dxf_version: str = "R2018",
    replace: bool = False,
    oda_path: str | Path | None = None,
    dwgread_path: str | Path | None = None,
    validate: bool = True,
) -> ConversionResult:
    """Return a DXF path suitable for annotation-aware parsing."""
    source_path = Path(source)
    suffix = source_path.suffix.lower()
    if suffix == ".dxf":
        return ConversionResult(source_path, source_path, "none", ["Input is already DXF."])
    if suffix != ".dwg":
        raise CadConversionError(f"Unsupported CAD extension for conversion: {suffix}")
    return convert_dwg_to_dxf(
        source_path,
        out_dir,
        converter=converter,
        dxf_version=dxf_version,
        replace=replace,
        oda_path=oda_path,
        dwgread_path=dwgread_path,
        validate=validate,
    )


def convert_dwg_to_dxf(
    source: str | Path,
    out_dir: str | Path,
    converter: str = "auto",
    dxf_version: str = "R2018",
    replace: bool = False,
    output_file: str | Path | None = None,
    oda_path: str | Path | None = None,
    dwgread_path: str | Path | None = None,
    validate: bool = True,
) -> ConversionResult:
    source_path = Path(source)
    out_path = Path(output_file) if output_file else Path(out_dir) / f"{source_path.stem}.dxf"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists() and not replace:
        validation = validate_dxf_file(out_path) if validate else None
        if validation and not validation.readable:
            raise CadConversionError(f"Existing converted DXF is not readable: {validation.error}. Pass --replace to regenerate it.")
        return ConversionResult(
            source_path,
            out_path,
            "existing",
            ["Using existing converted DXF. Pass the replace flag to regenerate it."],
            validation=validation,
        )

    candidates = _converter_candidates(converter)
    errors: list[str] = []
    for candidate in candidates:
        try:
            if candidate == "oda":
                _convert_with_oda(source_path, out_path, dxf_version=dxf_version, replace=replace, oda_path=oda_path)
            elif candidate == "libredwg":
                _convert_with_libredwg(source_path, out_path, replace=replace, dwgread_path=dwgread_path)
            else:
                raise CadConversionError(f"Unknown converter: {candidate}")
            validation = validate_dxf_file(out_path) if validate else None
            if validation and not validation.readable:
                raise CadConversionError(f"Converted DXF is not readable: {validation.error}")
            notes = [f"Converted DWG to DXF with {candidate}."]
            if validation:
                notes.append(
                    "Validated DXF: "
                    f"{validation.layer_count} layers, "
                    f"{validation.text_count} text entities, "
                    f"{validation.block_count} block inserts."
                )
            return ConversionResult(source_path, out_path, candidate, notes, validation=validation)
        except CadConversionError as exc:
            errors.append(f"{candidate}: {exc}")

    detail = "; ".join(errors) if errors else "no converter candidates were available"
    raise CadConversionError(f"Could not convert DWG to DXF ({detail}).")


def _converter_candidates(converter: str) -> list[str]:
    if converter == "auto":
        return ["oda", "libredwg"]
    if converter in {"oda", "libredwg"}:
        return [converter]
    raise CadConversionError(f"Unsupported converter: {converter}")


def detect_converters(
    oda_path: str | Path | None = None,
    dwgread_path: str | Path | None = None,
) -> list[ConverterAvailability]:
    return [
        _detect_oda(oda_path),
        _detect_libredwg(dwgread_path),
    ]


def validate_dxf_file(path: str | Path) -> ConversionValidation:
    dxf_path = Path(path)
    file_size = dxf_path.stat().st_size if dxf_path.exists() else 0
    if not dxf_path.exists():
        return ConversionValidation(dxf_path, False, file_size, error="DXF file does not exist.")
    if file_size == 0:
        return ConversionValidation(dxf_path, False, file_size, error="DXF file is empty.")
    try:
        doc = ezdxf.readfile(dxf_path)
        entities = list(doc.modelspace())
    except Exception as exc:
        return ConversionValidation(dxf_path, False, file_size, error=f"{type(exc).__name__}: {exc}")

    entity_counts = Counter(entity.dxftype() for entity in entities)
    layers = {getattr(entity.dxf, "layer", "0") or "0" for entity in entities}
    return ConversionValidation(
        dxf_path,
        True,
        file_size,
        dxf_version=getattr(doc, "dxfversion", None),
        entity_counts=dict(entity_counts.most_common()),
        layer_count=len(layers),
        text_count=sum(count for kind, count in entity_counts.items() if kind in TEXT_TYPES),
        block_count=entity_counts.get("INSERT", 0),
        geometry_count=sum(count for kind, count in entity_counts.items() if kind in GEOMETRY_TYPES),
    )


def _convert_with_oda(
    source: Path,
    destination: Path,
    dxf_version: str,
    replace: bool,
    oda_path: str | Path | None = None,
) -> None:
    resolved_path = _resolve_oda_path(oda_path)
    if not resolved_path:
        raise CadConversionError(
            f"ODA File Converter is not installed or discoverable. "
            f"Set --oda-path or {ODA_PATH_ENV}."
        )
    _configure_oda_path(resolved_path)
    try:
        _run_oda_conversion(resolved_path, source, destination, dxf_version=dxf_version, replace=replace)
    except Exception as exc:
        raise CadConversionError(str(exc)) from exc


def _convert_with_libredwg(
    source: Path,
    destination: Path,
    replace: bool,
    dwgread_path: str | Path | None = None,
) -> None:
    dwgread = _resolve_dwgread_path(dwgread_path)
    if not dwgread:
        raise CadConversionError(f"LibreDWG dwgread is not installed or discoverable. Set --dwgread-path or {DWGREAD_PATH_ENV}.")
    if destination.exists() and replace:
        destination.unlink()
    command = [dwgread, "-O", "DXF", "-o", str(destination), str(source)]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip()
        raise CadConversionError(stderr or f"dwgread exited with {completed.returncode}")
    if not destination.exists():
        raise CadConversionError("dwgread completed without creating the destination DXF.")


def _detect_oda(oda_path: str | Path | None = None) -> ConverterAvailability:
    resolved = _resolve_oda_path(oda_path)
    if resolved:
        return ConverterAvailability("oda", True, resolved)
    return ConverterAvailability("oda", False, detail=f"Set --oda-path or {ODA_PATH_ENV}.")


def _detect_libredwg(dwgread_path: str | Path | None = None) -> ConverterAvailability:
    resolved = _resolve_dwgread_path(dwgread_path)
    if resolved:
        return ConverterAvailability("libredwg", True, resolved)
    return ConverterAvailability("libredwg", False, detail=f"Set --dwgread-path or {DWGREAD_PATH_ENV}.")


def _resolve_oda_path(oda_path: str | Path | None = None) -> str | None:
    explicit = _existing_file(oda_path)
    if explicit:
        return explicit
    env_path = _existing_file(os.environ.get(ODA_PATH_ENV))
    if env_path:
        return env_path

    configured = _existing_file(_configured_oda_path())
    if configured:
        return configured

    on_path = shutil.which("ODAFileConverter")
    if on_path:
        return on_path

    windows_default = _existing_file(r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe")
    if windows_default:
        return windows_default
    mac_default = _existing_file("/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter")
    if mac_default:
        return mac_default
    return None


def _resolve_dwgread_path(dwgread_path: str | Path | None = None) -> str | None:
    explicit = _existing_file(dwgread_path)
    if explicit:
        return explicit
    env_path = _existing_file(os.environ.get(DWGREAD_PATH_ENV))
    if env_path:
        return env_path
    return shutil.which("dwgread")


def _configure_oda_path(executable: str) -> None:
    section = "odafc-addon"
    key = "win_exec_path" if platform.system() == "Windows" else "unix_exec_path"
    ezdxf.options.set(section, key, executable)


def _run_oda_conversion(
    executable: str,
    source: Path,
    destination: Path,
    dxf_version: str,
    replace: bool,
) -> None:
    version = odafc.map_version(dxf_version)
    if destination.exists():
        if replace:
            destination.unlink()
        else:
            raise CadConversionError(f"Target file already exists: {destination}")

    # ODA's filename filter can miss decomposed Unicode names on macOS.
    # Copy to an ASCII temp name and move the produced DXF to the requested path.
    with tempfile.TemporaryDirectory(prefix="cad_parser_oda_") as tmp:
        input_dir = Path(tmp) / "input"
        output_dir = Path(tmp) / "output"
        input_dir.mkdir()
        output_dir.mkdir()
        temp_source = input_dir / "source.dwg"
        shutil.copy2(source, temp_source)
        command = [
            executable,
            str(input_dir),
            str(output_dir),
            version,
            "DXF",
            "0",
            "1",
            "*.dwg",
        ]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            stderr = completed.stderr.strip() or completed.stdout.strip()
            raise CadConversionError(stderr or f"ODA File Converter exited with {completed.returncode}")
        outputs = sorted(output_dir.glob("*.dxf"))
        if not outputs:
            raise CadConversionError("ODA File Converter completed without creating a DXF.")
        shutil.move(str(outputs[0]), destination)


def _configured_oda_path() -> str | None:
    key = "win_exec_path" if platform.system() == "Windows" else "unix_exec_path"
    try:
        return ezdxf.options.get("odafc-addon", key).strip('"')
    except Exception:
        return None


def _existing_file(path: str | Path | None) -> str | None:
    if not path:
        return None
    expanded = Path(path).expanduser()
    return str(expanded) if expanded.is_file() else None
