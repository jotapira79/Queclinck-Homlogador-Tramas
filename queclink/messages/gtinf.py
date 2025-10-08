"""Parser para mensajes GTINF."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from ..parser import _common_enrich, _split, _to_iso
from ..specs.loader import get_spec_path

_GTINF_HEADERS = {"+RESP:GTINF", "+BUFF:GTINF"}
_TIMESTAMP_RE = re.compile(r"\d{14}")


def parse_gtinf(line: str, source: str = "RESP", device: Optional[str] = None) -> Dict[str, Any]:
    """Parsear un mensaje +RESP/+BUFF:GTINF."""
    parts = _split(line)
    if not parts:
        return {}

    header = parts[0].strip()
    if header not in _GTINF_HEADERS:
        return {}

    detected_source: Optional[str]
    if header.startswith("+RESP:"):
        detected_source = "RESP"
    elif header.startswith("+BUFF:"):
        detected_source = "BUFF"
    else:
        detected_source = None

    protocol_version = parts[1].strip() if len(parts) > 1 and parts[1] else None
    imei = parts[2].strip() if len(parts) > 2 and parts[2] else None

    device_name = device.strip() if device else None
    if not device_name and len(parts) > 3:
        candidate = parts[3].strip()
        if candidate:
            device_name = candidate

    count_hex = parts[-1].strip() if parts[-1] else None
    timestamps = _TIMESTAMP_RE.findall(line) if line else []
    send_time_raw = timestamps[-1] if timestamps else None
    send_time_iso = _to_iso(send_time_raw) if send_time_raw else None

    data: Dict[str, Any] = {
        "raw": line,
        "header": header,
        "report": "GTINF",
    }
    if imei:
        data["imei"] = imei
    if device_name:
        data["device"] = device_name.upper()
    if protocol_version:
        data["protocol_version"] = protocol_version
    if count_hex:
        data["count_hex"] = count_hex
    if send_time_raw:
        data["send_time_raw"] = send_time_raw
    if send_time_iso:
        data["send_time_iso"] = send_time_iso

    if device_name:
        try:
            data["spec_path"] = get_spec_path("GTINF", device_name)
        except ValueError:
            data["spec_path"] = None

    return _common_enrich(data, detected_source or source, protocol_version, count_hex)


__all__ = ["parse_gtinf"]
