# Shim de compatibilidad para los analizadores de tramas Queclink.
"""Importa y reexporta funciones públicas desde :mod:`queclink.parser`."""

from queclink.parser import parse_gteri, parse_gtinf, parse_line

__all__ = ["parse_line", "parse_gteri", "parse_gtinf"]

# Compatibilidad adicional con el nombre anterior usado en pruebas internas.
parse_line_to_record = parse_line
