# Paquete principal para los analizadores de mensajes Queclink.
"""Herramientas de análisis y compatibilidad para mensajes de equipos Queclink."""

from __future__ import annotations

import sys
import types

from .parser import parse_gteri, parse_gtinf, parse_line

__all__ = ["parse_line", "parse_gteri", "parse_gtinf"]

# Registramos módulos en sys.modules para mantener compatibilidad con
# importaciones antiguas como ``from queclink.gteri import parse_gteri``.
_gteri_module = types.ModuleType(__name__ + ".gteri")
_gteri_module.parse_gteri = parse_gteri
sys.modules[_gteri_module.__name__] = _gteri_module

_gtinf_module = types.ModuleType(__name__ + ".gtinf")
_gtinf_module.parse_gtinf = parse_gtinf
sys.modules[_gtinf_module.__name__] = _gtinf_module
