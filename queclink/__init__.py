"""Paquete principal del analizador Queclink."""

from __future__ import annotations

from .parser import parse_gteri, parse_gtinf, parse_line

__all__ = ["parse_line", "parse_gteri", "parse_gtinf"]
