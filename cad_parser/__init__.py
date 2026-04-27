"""Annotation-aware CAD parsing helpers."""

from cad_parser.converters import CadConversionError, convert_dwg_to_dxf, detect_converters, prepare_analysis_input
from cad_parser.parser import UnsupportedCadFormatError, analyze_cad_file

__all__ = [
    "CadConversionError",
    "UnsupportedCadFormatError",
    "analyze_cad_file",
    "convert_dwg_to_dxf",
    "detect_converters",
    "prepare_analysis_input",
]
