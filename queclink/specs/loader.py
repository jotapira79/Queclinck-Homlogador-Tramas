# Cargador auxiliar para especificaciones de mensajes Queclink.
"""Funciones utilitarias para obtener definiciones estructuradas de mensajes."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

_SPEC_CACHE: Dict[str, Dict[str, Any]] = {}


def load_spec(name: str) -> Dict[str, Any]:
    """Cargar una especificación de mensaje por nombre.

    Por ahora es un marcador de posición que devuelve un diccionario vacío y
    permite agregar la lógica real en iteraciones futuras.
    """

    normalized = name.strip().lower()
    if not normalized:
        raise ValueError("El nombre de la especificación no puede estar vacío")
    if normalized not in _SPEC_CACHE:
        # Placeholder: en el futuro se podrían leer archivos JSON/YAML.
        _SPEC_CACHE[normalized] = {"name": normalized, "source": None, "path": Path()}
    return dict(_SPEC_CACHE[normalized])
