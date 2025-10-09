"""Herramientas para ingerir tramas homologadas en una base SQLite."""

from __future__ import annotations

import json
import logging
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, MutableMapping, Optional, Sequence

from .messages.gtinf import parse_gtinf as _parse_gtinf
from .parser import detect_model_from_identifiers, parse_line
from .specs.loader import get_spec_path, load_spec_columns_from_path

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
    "message": "TEXT",
    "device_name": "TEXT",
    "model": "TEXT",
    "version": "TEXT",
    "report_type": "TEXT",
    "number": "INTEGER",
    "eri_mask": "TEXT",
    "external_power_mv": "INTEGER",
    "ext_power_mv": "INTEGER",
    "gnss_accuracy_level": "REAL",
    "gnss_acc": "REAL",
    "speed_kmh": "REAL",
    "azimuth_deg": "INTEGER",
    "altitude_m": "REAL",
    "longitude_deg": "REAL",
    "latitude_deg": "REAL",
    "lon": "REAL",
    "lat": "REAL",
    "gnss_utc_time": "TEXT",
    "gnss_utc": "TEXT",
    "utc": "TEXT",
    "mcc": "TEXT",
    "mnc": "TEXT",
    "lac": "TEXT",
    "cell_id": "TEXT",
    "position_append_mask": "TEXT",
    "pos_append_mask": "TEXT",
    "sats_in_use": "INTEGER",
    "satellites": "INTEGER",
    "sats": "INTEGER",
    "hdop": "REAL",
    "vdop": "REAL",
    "pdop": "REAL",
    "dop1": "REAL",
    "dop2": "REAL",
    "dop3": "REAL",
    "gnss_trigger_type": "INTEGER",
    "gnss_jamming_state": "INTEGER",
    "hour_meter": "TEXT",
    "mileage_km": "REAL",
    "analog_in_1": "REAL",
    "analog_in_1_raw": "TEXT",
    "analog_in_1_mv": "REAL",
    "analog_in_1_pct": "REAL",
    "analog_in_2": "REAL",
    "analog_in_2_raw": "TEXT",
    "analog_in_2_mv": "REAL",
    "analog_in_2_pct": "REAL",
    "analog_in_3": "REAL",
    "analog_in_3_raw": "TEXT",
    "analog_in_3_mv": "REAL",
    "analog_in_3_pct": "REAL",
    "backup_battery_pct": "REAL",
    "backup_batt_pct": "REAL",
    "backup_battery_pct_raw": "REAL",
    "device_status": "TEXT",
    "device_status_raw": "TEXT",
    "device_status_len_bits": "INTEGER",
    "uart_device_type": "INTEGER",
    "uart_device_type_label": "TEXT",
    "digital_fuel_sensor_data": "TEXT",
    "digital_fuel_sensor_data_items": "TEXT",
    "rf433_block": "TEXT",
    "ble_block": "TEXT",
    "ble_count": "INTEGER",
    "gnss_fix": "INTEGER",
    "is_last_fix": "INTEGER",
    "spec_path": "TEXT",
    "raw": "TEXT",
    "is_buff": "INTEGER",
    "send_time": "TEXT",
    "count_hex": "TEXT",
    "count_dec": "INTEGER",
    "validation_warnings": "TEXT",
    "reserved_1": "TEXT",
    "reserved_2": "TEXT",
    "reserved_3": "TEXT",
    "rat_band": "TEXT",
    "rat": "INTEGER",
    "band": "TEXT",
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

_GTINF_HEADERS = {"+RESP:GTINF", "+BUFF:GTINF"}

_LOGGER = logging.getLogger(__name__)


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


def _normalize_spec_path(spec_path: str | Path) -> str:
    return str(Path(spec_path))


@lru_cache(maxsize=64)
def _columns_from_spec(spec_path: str | Path) -> Sequence[str]:
    return tuple(load_spec_columns_from_path(spec_path))


def ensure_table_from_spec(
    conn: sqlite3.Connection,
    table: str,
    spec_path: str | Path,
) -> Sequence[str]:
    """Crear una tabla con columnas basadas en una spec YAML si no existe."""

    normalized = _normalize_spec_path(spec_path)
    columns = _columns_from_spec(normalized)
    if not columns:
        raise ValueError(f"La spec {normalized} no define columnas")

    column_defs = ", ".join(f'"{column}" TEXT' for column in columns)
    conn.execute(f"CREATE TABLE IF NOT EXISTS {table} ({column_defs})")
    conn.commit()
    return columns


def insert_row_from_spec(
    conn: sqlite3.Connection,
    table: str,
    spec_path: str | Path,
    row: Mapping[str, Any],
) -> Optional[int]:
    """Insertar una fila respetando el orden de columnas definido en una spec."""

    columns = ensure_table_from_spec(conn, table, spec_path)
    placeholders = ", ".join("?" for _ in columns)
    values = [row.get(column) for column in columns]
    cursor = conn.execute(
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
        values,
    )
    conn.commit()
    return cursor.lastrowid


def _split_payload(line: str) -> list[str]:
    payload = line.strip()
    if payload.endswith("$"):
        payload = payload[:-1]
    return payload.split(",") if payload else []


def ingest_gtinf_line(conn: sqlite3.Connection, line: str) -> bool:
    """Procesar e insertar una trama GTINF basada en su spec específica."""

    parts = _split_payload(line)
    if not parts:
        return False

    header = parts[0].strip()
    if header not in _GTINF_HEADERS:
        return False

    if len(parts) < 4:
        _LOGGER.warning("Trama GTINF sin campos suficientes para determinar el modelo: %s", line)
        return False

    imei = parts[2].strip() if len(parts) > 2 else ""
    reported_device = parts[3].strip()
    model = detect_model_from_identifiers(imei, reported_device)
    if not model:
        _LOGGER.warning(
            "No se pudo determinar el modelo GTINF por prefijo de IMEI en la trama: %s",
            line,
        )
        return False

    model = model.strip().upper()

    try:
        spec_path = get_spec_path("GTINF", model)
    except ValueError:
        _LOGGER.warning(
            "No se encontró spec para GTINF del modelo %s (prefijo IMEI %s)",
            model,
            imei[:8] if imei else "",
        )
        return False

    spec_file = Path(spec_path)
    if not spec_file.exists():
        _LOGGER.warning(
            "No se encontró spec para GTINF del modelo %s en %s", model, spec_path
        )
        return False

    row = _parse_gtinf(line, device=model)
    if not row:
        return False

    table = f"gtinf_{model.lower()}"
    insert_row_from_spec(conn, table, spec_file, row)
    return True


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
            if normalized_report == "GTINF":
                if ingest_gtinf_line(conn, raw_line):
                    inserted += 1
                continue

            parsed = parse_line(raw_line)
            if not parsed:
                continue
            record: Dict[str, Any] = dict(parsed)
            record.setdefault("raw_line", raw_line)
            if (
                insert_parsed_record(
                    conn, normalized_model, normalized_report, record
                )
                is not None
            ):
                inserted += 1
    return inserted


if __name__ == "__main__":
    connection = init_db(":memory:")
    print("Tablas creadas:")
    for model in MODELS:
        for report in REPORTS:
            table = _table_name(model, report)
            print(f" - {table}")
