"""Utilidades para localizar especificaciones de mensajes Queclink."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


def get_spec_path(report: str, device: str) -> str:
    """Devolver la ruta relativa al archivo de especificación."""
    if not report or not device:
        raise ValueError("Se requieren el nombre del reporte y del dispositivo")
    report_norm = report.strip().lower()
    device_norm = device.strip().lower()
    if not report_norm or not device_norm:
        raise ValueError("Los parámetros report y device no pueden ser vacíos")
    return str(Path("spec") / device_norm / f"{report_norm}.yml")


def load_yaml(path: str) -> Dict[str, Any]:
    """Cargar un archivo YAML de especificación."""
    # TODO: implementar carga real cuando se definan validaciones
    raise NotImplementedError("TODO: implementar lectura de YAML de especificaciones")


__all__ = ["get_spec_path", "load_yaml"]
