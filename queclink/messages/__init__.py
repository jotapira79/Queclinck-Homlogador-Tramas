# Subpaquete para mensajes individuales de Queclink.
"""Colección de analizadores específicos por tipo de mensaje."""

from .gteri import parse_gteri
from .gtinf import parse_gtinf

__all__ = ["parse_gteri", "parse_gtinf"]
