"""Parser para mensajes GTINF homologado por modelo (usando spec YAML)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import re
import yaml

from ..parser import _split
from ..specs.loader import get_spec_path

_GTINF_HEADERS = {"+RESP:GTINF", "+BUFF:GTINF"}

def _load_spec_for(device_name: str) -> Dict[str, Any]:
    spec_path = get_spec_path("GTINF", device_name)  # p.ej. queclink/specs/gtinf_gv310lau.yml
    return yaml.safe_load(Path(spec_path).read_text(encoding="utf-8"))

def _columns_from_spec(spec: Dict[str, Any]) -> List[str]:
    cols: List[str] = []
    for section in spec["schema"]["sections"]:
        for f in section["fields"]:
            cols.append(f["name"])
    return cols

def _split_header_message(first_token: str) -> Optional[Dict[str, str]]:
    # first_token es "+RESP:GTINF" o "+BUFF:GTINF"
    if first_token not in _GTINF_HEADERS:
        return None
    if first_token.startswith("+RESP:"):
        return {"header": "+RESP:GT", "message": "INF"}
    if first_token.startswith("+BUFF:"):
        return {"header": "+BUFF:GT", "message": "INF"}
    return None

def parse_gtinf(line: str, source: str = "RESP", device: Optional[str] = None) -> Dict[str, Any]:
    """
    Parsea un mensaje +RESP/+BUFF:GTINF y devuelve un dict homologado
    con las columnas EXACTAS definidas en la spec del modelo.
    """
    parts = _split(line)
    if not parts:
        return {}

    first = parts[0].strip()
    if first not in _GTINF_HEADERS:
        return {}

    # Detectar modelo desde el 4° campo si no viene por parámetro
    device_name = (device or (parts[3].strip() if len(parts) > 3 else "")).strip()
    if not device_name:
        # Por defecto puedes fijar un modelo o devolver vacío
        return {}

    spec = _load_spec_for(device_name)
    columns = _columns_from_spec(spec)

    # Reconstruir "header" y "message" de la spec a partir del primer token
    hm = _split_header_message(first)
    if hm is None:
        return {}

    # Ahora mapeamos por posición:
    # spec espera: header, message, full_protocol_version, imei, device_name, ...
    values: List[Optional[str]] = []

    # 1) header + message
    values.append(hm["header"])    # header
    values.append(hm["message"])   # message

    # 2) El resto de campos de la línea, desde parts[1] hasta el penúltimo (último es count_hex)
    # Nota: la spec tuya ya incluye "count_hex" en la última sección (tail)
    middle = parts[1:]  # ya sin el primer token
    # Si la línea trae '$' ya fue removido en _split()
    # Aseguramos longitud según columnas esperadas
    # columns[0], columns[1] ya ocupados; completamos desde columns[2:]
    need = len(columns) - 2
    middle = middle[:need] + [None] * max(0, need - len(middle))

    values.extend(middle)

    # Construimos el dict homologado (solo columnas de negocio)
    homologated = dict(zip(columns, values[:len(columns)]))

    # Importante: NO añadir aquí campos genéricos (raw, report, spec_path, etc.)
    # Para mantener DB limpia 1:1 con protocolo.

    return homologated

__all__ = ["parse_gtinf"]
