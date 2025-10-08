"""Herramientas para ingerir tramas homologadas en una base SQLite."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, MutableMapping, Optional

from .parser import parse_line

MODELS = ("GV310LAU", "GV58LAU", "GV350CEU")
REPORTS = ("GTERI", "GTINF")

BASE_COLUMNS: Mapping[str, str] = {
    "model": "TEXT",
    "report": "TEXT",
    "imei": "TEXT",
    "device": "TEXT",
    "source": "TEXT",
    "protocol_version": "TEXT",
    "send_time_raw": "TEXT",
    "send_time_iso": "TEXT",
    "count_hex": "TEXT",
    "raw_line": "TEXT",
}

GTERI_COLUMNS: Mapping[str, str] = {
    "header": "TEXT",
    "prefix": "TEXT",
    "device_name": "TEXT",
    "model": "TEXT",
    "version": "TEXT",
    "report_type": "TEXT",
    "number": "INTEGER",
    "eri_mask": "TEXT",
    "ext_power_mv": "INTEGER",
    "gnss_acc": "REAL",
    "speed_kmh": "REAL",
    "azimuth_deg": "INTEGER",
    "altitude_m": "REAL",
    "lon": "REAL",
    "lat": "REAL",
    "gnss_utc": "TEXT",
    "utc": "TEXT",
    "mcc": "TEXT",
    "mnc": "TEXT",
    "lac": "TEXT",
    "cell_id": "TEXT",
    "pos_append_mask": "TEXT",
    "raw_after_pam": "TEXT",
    "send_time": "TEXT",
    "satellites": "INTEGER",
    "sats": "INTEGER",
    "is_buff": "INTEGER",
    "count_dec": "INTEGER",
    "dop1": "REAL",
    "dop2": "REAL",
    "dop3": "REAL",
    "gnss_trigger_type": "INTEGER",
    "gnss_jamming_state": "INTEGER",
    "hour_meter": "TEXT",
    "mileage_km": "REAL",
    "analog_in_1": "REAL",
    "analog_in_2": "REAL",
    "analog_in_3": "REAL",
    "device_status": "TEXT",
    "uart_device_type": "INTEGER",
    "gnss_fix": "INTEGER",
    "is_last_fix": "INTEGER",
    "spec_path": "TEXT",
    "raw": "TEXT",
}

GTINF_COLUMNS: Mapping[str, str] = {
    "raw": "TEXT",
    "header": "TEXT",
    "spec_path": "TEXT",
}

REPORT_SCHEMAS: Mapping[str, Mapping[str, str]] = {
    "GTERI": GTERI_COLUMNS,
    "GTINF": GTINF_COLUMNS,
}


def _table_name(model: str, report: str) -> str:
    return f"{model.strip().lower()}_{report.strip().lower()}"


def _normalize_path(path: str | Path) -> str:
    return str(path)


def _column_type(report: str, column: str) -> str:
    if column in BASE_COLUMNS:
        return BASE_COLUMNS[column]
    return REPORT_SCHEMAS.get(report, {}).get(column, "TEXT")


def _existing_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}


def _ensure_columns(
    conn: sqlite3.Connection,
    table: str,
    report: str,
    columns: Iterable[str],
) -> None:
    existing = _existing_columns(conn, table)
    for column in columns:
        if column == "id" or column in existing:
            continue
        col_type = _column_type(report, column)
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    conn.commit()


def init_db(path: str | Path) -> sqlite3.Connection:
    """Crear la base SQLite y todas las tablas requeridas."""

    conn = sqlite3.connect(_normalize_path(path))
    for model in MODELS:
        for report in REPORTS:
            table = _table_name(model, report)
            column_defs = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
            seen: set[str] = set()
            for column, col_type in BASE_COLUMNS.items():
                if column in seen:
                    continue
                column_defs.append(f"{column} {col_type}")
                seen.add(column)
            for column, col_type in REPORT_SCHEMAS[report].items():
                if column in seen:
                    continue
                column_defs.append(f"{column} {col_type}")
                seen.add(column)
            conn.execute(
                f"CREATE TABLE IF NOT EXISTS {table} ({', '.join(column_defs)})"
            )
    conn.commit()
    _create_telemetry_view(conn)
    return conn


def _create_telemetry_view(conn: sqlite3.Connection) -> None:
    """Crear una vista unificada con las columnas base de todas las tablas."""

    base_columns = list(BASE_COLUMNS.keys())
    column_list = ", ".join(base_columns)
    selects: list[str] = []
    for model in MODELS:
        for report in REPORTS:
            table = _table_name(model, report)
            selects.append(f"SELECT {column_list} FROM {table}")
    union_sql = " UNION ALL ".join(selects)
    conn.execute("DROP VIEW IF EXISTS telemetry_messages")
    conn.execute(f"CREATE VIEW telemetry_messages AS {union_sql}")
    conn.commit()


def _normalize_value(value: Any) -> Any:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value)
    return value


def insert_parsed_record(
    conn: sqlite3.Connection,
    model: str,
    report: str,
    parsed_dict: MutableMapping[str, Any],
) -> Optional[int]:
    """Insertar un diccionario parseado en la tabla correspondiente."""

    if not parsed_dict:
        return None

    normalized_model = model.strip().upper()
    normalized_report = report.strip().upper()
    table = _table_name(normalized_model, normalized_report)

    parsed_dict.setdefault("model", normalized_model)
    parsed_dict.setdefault("report", normalized_report)
    if "raw_line" not in parsed_dict:
        raw_value = parsed_dict.get("raw")
        if isinstance(raw_value, str):
            parsed_dict["raw_line"] = raw_value
    parsed_dict.setdefault("device", parsed_dict.get("device") or normalized_model)

    _ensure_columns(conn, table, normalized_report, parsed_dict.keys())

    columns = [col for col in parsed_dict.keys() if col != "id"]
    if "raw_line" not in columns:
        columns.append("raw_line")
    columns = list(dict.fromkeys(columns))

    placeholders = ", ".join(["?" for _ in columns])
    values = [
        _normalize_value(parsed_dict.get(column)) if column != "raw_line" else _normalize_value(parsed_dict.get(column))
        for column in columns
    ]

    cursor = conn.execute(
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
        values,
    )
    conn.commit()
    return cursor.lastrowid


def bulk_ingest_from_file(
    conn: sqlite3.Connection,
    model: str,
    report: str,
    file_path: str | Path,
) -> int:
    """Ingerir un archivo de texto línea por línea."""

    normalized_model = model.strip().upper()
    normalized_report = report.strip().upper()
    inserted = 0
    with open(file_path, "r", encoding="utf-8") as fh:
        for raw_line in fh:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            parsed = parse_line(raw_line)
            if not parsed:
                continue
            record: Dict[str, Any] = dict(parsed)
            record.setdefault("raw_line", raw_line)
            if insert_parsed_record(conn, normalized_model, normalized_report, record) is not None:
                inserted += 1
    return inserted


if __name__ == "__main__":
    connection = init_db(":memory:")
    print("Tablas creadas:")
    for model in MODELS:
        for report in REPORTS:
            table = _table_name(model, report)
            print(f" - {table}")
