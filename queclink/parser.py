"""Funciones base para analizar tramas Queclink."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

HeaderDetection = Tuple[str, str, Optional[str]]
_HEADER_RE = re.compile(r"^\+(RESP|BUFF):(GT[A-Z0-9]+)$")


def _split(line: str) -> List[str]:
    """Separar una línea cruda en campos."""
    if not line:
        return []
    payload = line.strip()
    if payload.endswith("$"):
        payload = payload[:-1]
    return payload.split(",") if payload else []


def _detect(parts: Iterable[str]) -> Optional[HeaderDetection]:
    """Detectar tipo de mensaje a partir de los campos iniciales."""
    parts_list = list(parts)
    if not parts_list:
        return None
    header = parts_list[0].strip()
    match = _HEADER_RE.match(header)
    if not match:
        return None
    source, report = match.group(1), match.group(2)
    device: Optional[str] = None
    # Intentamos obtener el nombre del dispositivo del cuarto campo
    if len(parts_list) > 3:
        candidate = parts_list[3].strip()
        if candidate:
            device = candidate
    return source, report, device


def _to_iso(yyyymmddhhmmss: str) -> Optional[str]:
    """Convertir un timestamp YYYYMMDDHHMMSS a formato ISO-8601 UTC."""
    if not yyyymmddhhmmss or len(yyyymmddhhmmss) != 14 or not yyyymmddhhmmss.isdigit():
        return None
    try:
        dt = datetime.strptime(yyyymmddhhmmss, "%Y%m%d%H%M%S")
    except ValueError:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _common_enrich(
    data: Dict[str, Any],
    source: Optional[str],
    protocol_version: Optional[str],
    count_hex: Optional[str],
) -> Dict[str, Any]:
    """Aplicar normalizaciones comunes a los diccionarios parseados."""
    if source:
        data["source"] = source.upper()
    if protocol_version:
        data["protocol_version"] = protocol_version.upper()
    if count_hex:
        data["count_hex"] = count_hex.upper()
    send_time_raw = data.get("send_time_raw")
    if send_time_raw and not data.get("send_time_iso"):
        iso = _to_iso(send_time_raw)
        if iso:
            data["send_time_iso"] = iso
    return data


def parse_line(line: str) -> Dict[str, Any]:
    """Detectar y parsear una línea completa."""
    parts = _split(line)
    detection = _detect(parts)
    if not detection:
        return {}
    source, report, device = detection
    parser = {
        "GTERI": _parse_gteri,
        "GTINF": _parse_gtinf,
    }.get(report)
    if parser is None:
        return {}
    parsed = parser(line, source=source, device=device)
    if report == "GTINF":
        return _enrich_gtinf(parsed, source, device)
    return parsed


def parse_gteri(line: str, source: str = "RESP", device: Optional[str] = None) -> Dict[str, Any]:
    """Parsear un mensaje GTERI."""
    return _parse_gteri(line, source=source, device=device)


def parse_gtinf(line: str, source: str = "RESP", device: Optional[str] = None) -> Dict[str, Any]:
    """Parsear un mensaje GTINF."""
    return _parse_gtinf(line, source=source, device=device)


from .messages.gteri import parse_gteri as _parse_gteri  # noqa: E402
from .messages.gtinf import parse_gtinf as _parse_gtinf  # noqa: E402


def _enrich_gtinf(
    parsed: Dict[str, Any],
    source: Optional[str],
    device: Optional[str],
) -> Dict[str, Any]:
    if not parsed:
        return {}

    enriched: Dict[str, Any] = dict(parsed)
    enriched["message_family"] = parsed.get("message")
    enriched["message"] = "GTINF"
    enriched["report"] = "GTINF"

    if device:
        normalized_device = device.strip().upper()
        enriched["device"] = normalized_device
        enriched.setdefault("device_name", normalized_device)
        enriched.setdefault("model", normalized_device)
    else:
        fallback = str(parsed.get("device_name") or "").upper()
        if fallback:
            enriched.setdefault("device", fallback)
            enriched.setdefault("model", fallback)

    send_time = enriched.get("send_time")
    if send_time:
        enriched.setdefault("send_time_raw", send_time)

    protocol_version = enriched.get("full_protocol_version")
    count_hex = enriched.get("count_hex")
    _common_enrich(enriched, source, protocol_version, count_hex)

    imei = enriched.get("imei") or parsed.get("imei")
    if imei:
        enriched["imei"] = imei

    return enriched

__all__ = ["parse_line", "parse_gteri", "parse_gtinf"]
