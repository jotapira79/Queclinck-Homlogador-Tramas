"""Shim de compatibilidad para los analizadores de tramas Queclink."""

# DEPRECATION: migrado a queclink.parser

from queclink.parser import parse_gteri, parse_gtinf, parse_line

__all__ = ["parse_line", "parse_gteri", "parse_gtinf"]

parse_line_to_record = parse_line
