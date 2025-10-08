"""Utilidades para crear e ingerir tramas en SQLite."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Optional

from queclink.ingestor_sqlite import ingest_gtinf_line, insert_parsed_record, init_db

from queclink.parser import parse_line

_GTINF_PREFIXES = ("+RESP:GTINF", "+BUFF:GTINF")


def ensure_db(path: str | Path) -> sqlite3.Connection:
    """Crear (si es necesario) una base de datos SQLite para las tramas."""

    db_path = Path(path)
    if db_path != Path(":memory:"):
        db_path.parent.mkdir(parents=True, exist_ok=True)
    return init_db(str(db_path))


def ingest_lines(
    conn: sqlite3.Connection,
    lines: Iterable[str],
    *,
    message: Optional[str] = None,
) -> int:
    """Ingerir líneas preparseadas en la base de datos.

    Args:
        conn: Conexión SQLite devuelta por :func:`ensure_db`.
        lines: Iterable de líneas crudas (strings).
        message: Opcional, filtra por tipo de reporte ("GTINF" o "GTERI").

    Returns:
        Número de tramas insertadas en la base de datos.
    """

    expected_report = message.upper() if message else None
    inserted = 0

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        header = line.split(",", 1)[0].strip()
        if header in _GTINF_PREFIXES:
            if expected_report and expected_report != "GTINF":
                continue
            if ingest_gtinf_line(conn, line):
                inserted += 1
            continue

        parsed = parse_line(line)
        if not parsed:
            continue

        report = str(parsed.get("report") or "").upper()
        if expected_report and report != expected_report:
            continue
        if not report:
            continue

        device = (
            parsed.get("model")
            or parsed.get("device")
            or parsed.get("device_name")
        )
        if not device:
            continue

        normalized_device = str(device).upper()
        record = dict(parsed)
        record.setdefault("raw_line", line)
        record.setdefault("device", normalized_device)
        record.setdefault("model", normalized_device)

        if insert_parsed_record(conn, normalized_device, report, record) is not None:
            inserted += 1

    return inserted


__all__ = ["ensure_db", "ingest_lines"]
