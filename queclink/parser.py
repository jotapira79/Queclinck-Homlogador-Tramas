# Módulo principal con utilidades de análisis de mensajes Queclink.
"""Funciones de parseo y utilidades CLI para mensajes de equipos Queclink."""
import argparse
import csv
import json
import os
import re
import sqlite3
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Any, Iterable

try:
    import pandas as pd
except Exception:
    pd = None  # Permitimos uso sin pandas si solo se usa .txt

GTERI_PREFIXES = ("+RESP:GTERI", "+BUFF:GTERI")


def extract_gteri_payload(line: str) -> Optional[str]:
    if not line:
        return None
    matches = [line.find(prefix) for prefix in GTERI_PREFIXES]
    matches = [idx for idx in matches if idx != -1]
    if not matches:
        return None
    start = min(matches)
    return line[start:]

def split_fields(payload: str) -> List[str]:
    payload = payload.strip()
    if payload.endswith("$"):
        payload = payload[:-1]
    return [p for p in payload.split(",")]

def detect_model(fields: List[str]) -> Optional[str]:
    if len(fields) > 3:
        return fields[3].strip()
    return None

def is_gteri(line: str) -> bool:
    return extract_gteri_payload(line) is not None

def safe_float(x: Any) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None

def safe_int(x: Any, base: int = 10) -> Optional[int]:
    try:
        if isinstance(x, str) and base == 16:
            x = x.lower().replace("0x", "")
        return int(x, base)
    except Exception:
        return None

@dataclass
class CommonERI:
    prefix: str
    is_buff: int
    full_protocol_version: str
    imei: str
    device_name: str
    eri_mask: Optional[str]
    ext_power_mv: Optional[int]
    report_type: Optional[str]
    number: Optional[int]
    gnss_acc: Optional[float]
    speed_kmh: Optional[float]
    azimuth_deg: Optional[int]
    altitude_m: Optional[float]
    lon: Optional[float]
    lat: Optional[float]
    gnss_utc: Optional[str]
    mcc: Optional[str]
    mnc: Optional[str]
    lac: Optional[str]
    cell_id: Optional[str]
    pos_append_mask: Optional[str]
    raw_after_pam: str
    send_time: Optional[str]
    count_hex: Optional[str]

def parse_common_prefix(fields: List[str]) -> Tuple[CommonERI, int]:
    prefix = fields[0].strip()
    is_buff = 1 if prefix.startswith("+BUFF") else 0
    def get(i: int) -> Optional[str]:
        return fields[i].strip() if i < len(fields) and fields[i] != "" else None
    ce = CommonERI(
        prefix=prefix,
        is_buff=is_buff,
        full_protocol_version=get(1) or "",
        imei=get(2) or "",
        device_name=get(3) or "",
        eri_mask=get(4),
        ext_power_mv=safe_int(get(5)) if get(5) else None,
        report_type=get(6),
        number=safe_int(get(7)) if get(7) else None,
        gnss_acc=safe_float(get(8)) if get(8) else None,
        speed_kmh=safe_float(get(9)) if get(9) else None,
        azimuth_deg=safe_int(get(10)) if get(10) else None,
        altitude_m=safe_float(get(11)) if get(11) else None,
        lon=safe_float(get(12)) if get(12) else None,
        lat=safe_float(get(13)) if get(13) else None,
        gnss_utc=get(14),
        mcc=get(15),
        mnc=get(16),
        lac=get(17),
        cell_id=get(18),
        pos_append_mask=get(19),
        raw_after_pam="",
        send_time=None,
        count_hex=None,
    )
    return ce, 20

def extract_tail(fields: List[str]) -> Tuple[Optional[str], Optional[str]]:
    if len(fields) < 2:
        return None, None
    send_time = fields[-2].strip() if fields[-2] else None
    count_hex = fields[-1].strip() if fields[-1] else None
    if count_hex and count_hex.endswith("$"):
        count_hex = count_hex[:-1]
    return send_time, count_hex

def parse_model_specific(device: str, fields: List[str], start_idx: int) -> Dict[str, Any]:
    remaining = fields[start_idx:-2] if len(fields) >= (start_idx + 2) else fields[start_idx:]
    out: Dict[str, Any] = {}
    def looks_like_hourmeter(s: str) -> bool:
        return bool(re.fullmatch(r"\d{1,7}:\d{2}:\d{2}", s or ""))

    def to_mask_value(val: Optional[str]) -> Optional[int]:
        if not val:
            return None
        try:
            return int(val, 16)
        except ValueError:
            try:
                return int(val)
            except ValueError:
                return None

    mask_value = to_mask_value(fields[start_idx - 1] if start_idx - 1 < len(fields) else None)
    eri_mask_value = to_mask_value(fields[4] if len(fields) > 4 else None)

    def mask_has(bit: int) -> bool:
        return mask_value is not None and (mask_value & bit) != 0

    cursor = 0
    if cursor < len(remaining):
        raw_sat = remaining[cursor]
        if mask_has(0x01):
            out["satellites"] = safe_int(raw_sat) if (raw_sat or "") != "" else None
            cursor += 1
        elif (raw_sat or "") != "" and re.fullmatch(r"\d{1,2}", raw_sat or ""):
            out["satellites"] = safe_int(raw_sat)
            cursor += 1

    dop_values: List[Optional[float]] = []
    dop_pattern = r"\d{1,2}(?:\.\d{1,2})?"
    for idx in range(3):
        if cursor >= len(remaining):
            break
        value = remaining[cursor]
        expected = mask_has(0x02 << idx)
        if (value or "") == "":
            if expected:
                dop_values.append(None)
                cursor += 1
                continue
            break
        if re.fullmatch(dop_pattern, value or ""):
            dop_values.append(safe_float(value))
            cursor += 1
            continue
        if expected:
            dop_values.append(None)
            cursor += 1
            continue
        break

    if dop_values:
        if len(dop_values) > 0:
            out["dop1"] = dop_values[0]
        if len(dop_values) > 1:
            out["dop2"] = dop_values[1]
        if len(dop_values) > 2:
            out["dop3"] = dop_values[2]
    else:
        if cursor < len(remaining) and re.fullmatch(r"\d", remaining[cursor] or ""):
            out["gnss_trigger_type"] = safe_int(remaining[cursor])
            cursor += 1
        if cursor < len(remaining) and re.fullmatch(r"\d", remaining[cursor] or ""):
            out["gnss_jamming_state"] = safe_int(remaining[cursor])
            cursor += 1

    mileage_set = False
    hour_set = False

    if cursor < len(remaining) and looks_like_hourmeter(remaining[cursor] or ""):
        out["hour_meter"] = remaining[cursor]
        cursor += 1
        hour_set = True
    if cursor < len(remaining) and re.fullmatch(r"-?\d+(?:\.\d+)?", remaining[cursor] or ""):
        out["mileage_km"] = safe_float(remaining[cursor])
        cursor += 1
        mileage_set = True
    if not hour_set and cursor < len(remaining) and looks_like_hourmeter(remaining[cursor] or ""):
        out["hour_meter"] = remaining[cursor]
        cursor += 1
        hour_set = True
    if not mileage_set and cursor < len(remaining) and re.fullmatch(r"-?\d+(?:\.\d+)?", remaining[cursor] or ""):
        out["mileage_km"] = safe_float(remaining[cursor])
        cursor += 1
        mileage_set = True
    def skip_empty_values() -> None:
        nonlocal cursor
        while cursor < len(remaining) and (remaining[cursor] or "") == "":
            cursor += 1

    analog_pattern = r"-?\d+(?:\.\d+)?|F\d{1,3}"

    def add_warning(code: str) -> None:
        warnings = out.setdefault("validation_warnings", [])
        if code not in warnings:
            warnings.append(code)

    def parse_analog_value(raw_value: Optional[str], index: int) -> None:
        key = f"analog_in_{index}"
        raw_key = f"{key}_raw"
        mv_key = f"{key}_mv"
        pct_key = f"{key}_pct"
        out[key] = None
        out[raw_key] = None
        out[mv_key] = None
        out[pct_key] = None
        if raw_value is None or (raw_value or "") == "":
            return
        value = (raw_value or "").strip()
        out[raw_key] = value
        if not re.fullmatch(analog_pattern, value or ""):
            add_warning(f"{key}_invalid")
            return
        max_mv = 30000 if index == 3 else 16000
        mv_value: Optional[int] = None
        pct_value: Optional[float] = None
        if value.upper().startswith("F"):
            pct_raw = safe_int(value[1:]) if len(value) > 1 else None
            if pct_raw is None:
                add_warning(f"{key}_invalid")
                return
            pct_clamped = max(0, min(100, pct_raw))
            if pct_clamped != pct_raw:
                add_warning(f"{key}_pct_clamped")
            pct_value = float(pct_clamped)
            mv_value = int(round(max_mv * (pct_value / 100.0)))
        else:
            numeric = safe_float(value)
            if numeric is None:
                add_warning(f"{key}_invalid")
                return
            mv_candidate = int(round(numeric))
            mv_clamped = max(0, min(max_mv, mv_candidate))
            if mv_clamped != mv_candidate:
                add_warning(f"{key}_mv_clamped")
            mv_value = mv_clamped
            pct_value = round((mv_value / max_mv) * 100.0, 2) if max_mv > 0 else None
        out[key] = mv_value
        out[mv_key] = mv_value
        out[pct_key] = pct_value

    for i in range(1, 4):
        if cursor >= len(remaining):
            break
        value = remaining[cursor]
        if i == 3:
            next_val = remaining[cursor + 1] if cursor + 1 < len(remaining) else None
            next_next = remaining[cursor + 2] if cursor + 2 < len(remaining) else None
            if (
                re.fullmatch(r"\d{1,3}", (value or ""))
                and next_val
                and re.fullmatch(r"[0-9A-Fa-f]{6,10}", next_val or "")
                and (next_next is None or re.fullmatch(r"\d{1,2}", next_next or ""))
            ):
                parse_analog_value(None, i)
                break
        parse_analog_value(value, i)
        cursor += 1

    skip_empty_values()
    if cursor < len(remaining) and re.fullmatch(r"-?\d+(?:\.\d+)?", remaining[cursor] or ""):
        raw_val = safe_float(remaining[cursor])
        if raw_val is not None:
            raw_int = int(round(raw_val))
            clamped = max(0, min(100, raw_int))
            out["backup_batt_pct_raw"] = raw_val
            if clamped != raw_int:
                add_warning("backup_batt_pct_clamped")
            out["backup_batt_pct"] = clamped
            cursor += 1
    skip_empty_values()
    if cursor < len(remaining):
        candidate = remaining[cursor] or ""
        upper_candidate = candidate.upper()
        device_status_parsed = False
        if re.fullmatch(r"[0-9A-F]{6}|[0-9A-F]{10}", upper_candidate):
            device_status_parsed = True
            bit_len = 24 if len(upper_candidate) == 6 else 40
            out["device_status"] = upper_candidate
            out["device_status_raw"] = candidate
            out["device_status_len_bits"] = bit_len
        elif re.fullmatch(r"[0-9A-F]{10}-[0-9A-F]{10}", upper_candidate):
            device_status_parsed = True
            hi, lo = upper_candidate.split("-")
            out["device_status"] = upper_candidate
            out["device_status_raw"] = candidate
            out["device_status_len_bits"] = 80
            out["device_status_hi"] = hi
            out["device_status_lo"] = lo
        if device_status_parsed:
            cursor += 1
        elif candidate:
            out["device_status_raw"] = candidate
            add_warning("device_status_invalid")
            cursor += 1
    skip_empty_values()
    if cursor < len(remaining) and re.fullmatch(r"\d{1,2}", remaining[cursor] or ""):
        parsed_uart = safe_int(remaining[cursor])
        if parsed_uart is not None:
            out["uart_device_type"] = parsed_uart
            label_map = {0: "unknown", 1: "type_1", 7: "type_7"}
            out["uart_device_type_label"] = label_map.get(parsed_uart, "invalid")
            if parsed_uart not in label_map:
                add_warning("uart_device_type_invalid")
        cursor += 1
    skip_empty_values()
    if (
        eri_mask_value is not None
        and (eri_mask_value & 0x01) != 0
        and "uart_device_type" in out
        and cursor < len(remaining)
    ):
        dfs_items: List[str] = []
        dfs_truncated = False

        def should_stop(token: Optional[str], has_items: bool) -> bool:
            if token is None:
                return True
            token_str = (token or "").strip()
            if token_str == "":
                return True
            upper = token_str.upper()
            if upper in {"TMPS", "RF433", "RF433B", "BLE", "CAN", "1WIRE"}:
                return True
            if has_items and token_str.isdigit() and len(token_str) <= 2:
                return True
            if has_items and re.fullmatch(r"\d{4,}", token_str):
                return True
            if has_items and re.fullmatch(r"[0-9A-F]{8,}", upper):
                return True
            return False

        while cursor < len(remaining):
            token = remaining[cursor]
            if should_stop(token, bool(dfs_items)):
                break
            if len(dfs_items) < 20:
                dfs_items.append(token or "")
            else:
                dfs_truncated = True
            cursor += 1
        if dfs_items:
            out["digital_fuel_sensor_data"] = dfs_items[0] if len(dfs_items) == 1 else "|".join(dfs_items)
            out["dfs_raw_list"] = json.dumps(dfs_items, ensure_ascii=False)
            out["dfs_count"] = len(dfs_items)
        if dfs_truncated:
            add_warning("digital_fuel_sensor_data_truncated")
    skip_empty_values()
    out["remaining_blob"] = ",".join(remaining[cursor:])
    return out

def parse_line_to_record(line: str) -> Optional[Dict[str, Any]]:
    payload = extract_gteri_payload(line)
    if payload is None:
        return None
    fields = split_fields(payload)
    if len(fields) < 22:
        return None
    ce, nxt = parse_common_prefix(fields)
    send_time, count_hex = extract_tail(fields)
    ce.send_time, ce.count_hex = send_time, count_hex
    model_data = parse_model_specific(ce.device_name, fields, nxt)
    ce.raw_after_pam = model_data.pop("remaining_blob", "")
    base = asdict(ce)
    base.update(model_data)
    base["version"] = base.pop("full_protocol_version")
    base["count_dec"] = safe_int(base.get("count_hex"), 16) if base.get("count_hex") else None
    base["model"] = ce.device_name.upper()
    warnings = base.get("validation_warnings")
    if warnings:
        if not isinstance(warnings, list):
            warnings = [warnings]
        base["validation_warnings"] = warnings
    elif warnings is None:
        base.pop("validation_warnings", None)
    else:
        base["validation_warnings"] = []

    for key in {
        "analog_in_1_raw",
        "analog_in_1_mv",
        "analog_in_1_pct",
        "analog_in_2_raw",
        "analog_in_2_mv",
        "analog_in_2_pct",
        "analog_in_3_raw",
        "analog_in_3_mv",
        "analog_in_3_pct",
        "dfs_raw_list",
        "dfs_count",
        "backup_batt_pct",
        "backup_batt_pct_raw",
        "device_status_raw",
        "device_status_len_bits",
        "device_status_hi",
        "device_status_lo",
        "uart_device_type_label",
        "remaining_blob",
        "lat_lon_valid",
        "validation_warning",
        "validation_warnings_json",
    }:
        base.pop(key, None)
    return base


def parse_line(line: str) -> Optional[Dict[str, Any]]:
    """Parsear una línea cruda de texto y devolver el registro base."""

    return parse_line_to_record(line)


def parse_gteri(raw: str) -> Dict[str, Any]:
    """Parsear un mensaje GTERI normalizando algunas claves comunes."""

    base = parse_line(raw)
    if not base:
        return {}

    data = dict(base)
    data["header"] = data.get("prefix")
    data["device"] = data.get("model") or data.get("device_name")

    def _to_iso(ts: Optional[str]) -> Optional[str]:
        if not ts:
            return ts
        from datetime import datetime

        for fmt in ("%Y%m%d%H%M%S",):
            try:
                return datetime.strptime(ts, fmt).strftime("%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                continue
        return ts

    data["utc"] = _to_iso(data.get("gnss_utc")) if data.get("gnss_utc") else data.get("gnss_utc")
    data["send_time"] = _to_iso(data.get("send_time")) if data.get("send_time") else data.get("send_time")
    data["sats"] = data.get("satellites")

    dop_candidate = data.get("dop1")
    if dop_candidate is None:
        for key in ("dop2", "dop3"):
            val = data.get(key)
            if val is not None:
                dop_candidate = val
                break
    if dop_candidate is not None:
        data["hdop"] = dop_candidate

    if isinstance(data.get("device_status"), str):
        data["device_status"] = data["device_status"].upper()

    mask_lower = str(data.get("pos_append_mask", "")).lower()
    if mask_lower in {"00", "0"}:
        data.setdefault("gnss_fix", False)
        data.setdefault("is_last_fix", True)

    return data


def parse_gtinf(raw: str) -> Dict[str, Any]:
    """Parsear un mensaje GTINF. Implementación provisional."""

    if not raw:
        return {}
    return {"raw": raw}

def iter_messages_from_txt(path: str):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line:
                yield line

def infer_trama_column(df) -> str:
    candidates = [c for c in df.columns if c.lower() in ("trama", "frame", "gteri", "mensaje", "message", "raw")]
    if candidates:
        return candidates[0]
    if len(df.columns) == 1:
        return df.columns[0]
    for c in df.columns:
        s = df[c].astype(str).head(10).tolist()
        if any("+RESP:GTERI" in x or "+BUFF:GTERI" in x for x in s):
            return c
    return df.columns[0]

def read_any(path: str, sheet: Optional[str]=None, col: Optional[str]=None) -> List[str]:
    ext = os.path.splitext(path)[1].lower()
    if ext in (".txt", ".log"):
        return list(iter_messages_from_txt(path))
    if pd is None:
        raise RuntimeError("Se requiere pandas para leer .csv/.xlsx. Instale pandas y openpyxl.")
    if ext == ".csv":
        df = pd.read_csv(path, dtype=str, quoting=csv.QUOTE_MINIMAL, engine="python", encoding="utf-8", errors="ignore")
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(path, dtype=str, sheet_name=sheet if sheet else 0, engine="openpyxl")
    else:
        raise RuntimeError(f"Extensión de archivo no soportada: {ext}")
    trama_col = col if col else infer_trama_column(df)
    return [str(x) for x in df[trama_col].fillna("") if str(x).strip() != ""]

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS gteri_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prefix TEXT,
    is_buff INTEGER,
    version TEXT,
    imei TEXT,
    model TEXT,
    eri_mask TEXT,
    ext_power_mv INTEGER,
    report_type TEXT,
    number INTEGER,
    gnss_acc REAL,
    speed_kmh REAL,
    azimuth_deg INTEGER,
    altitude_m REAL,
    lon REAL,
    lat REAL,
    gnss_utc TEXT,
    mcc TEXT,
    mnc TEXT,
    lac TEXT,
    cell_id TEXT,
    pos_append_mask TEXT,
    satellites INTEGER,
    dop1 REAL,
    dop2 REAL,
    dop3 REAL,
    gnss_trigger_type INTEGER,
    gnss_jamming_state INTEGER,
    mileage_km REAL,
    hour_meter TEXT,
    analog_in_1 TEXT,
    analog_in_2 TEXT,
    analog_in_3 TEXT,
    digital_fuel_sensor_data TEXT,
    device_status TEXT,
    uart_device_type INTEGER,
    send_time TEXT,
    count_hex TEXT,
    count_dec INTEGER
);
CREATE INDEX IF NOT EXISTS idx_model ON gteri_records(model);
CREATE INDEX IF NOT EXISTS idx_imei ON gteri_records(imei);
CREATE INDEX IF NOT EXISTS idx_gnssutc ON gteri_records(gnss_utc);
"""

def ensure_additional_columns(conn: sqlite3.Connection) -> None:
    cur = conn.execute("PRAGMA table_info('gteri_records')")
    columns = {row[1] for row in cur.fetchall()}
    required_columns = {}
    for col, col_type in required_columns.items():
        if col not in columns:
            conn.execute(f"ALTER TABLE gteri_records ADD COLUMN {col} {col_type}")

def insert_records(db_path: str, rows: List[dict]) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        ensure_additional_columns(conn)
        cols = [
            "prefix","is_buff","version","imei","model","eri_mask","ext_power_mv","report_type","number",
            "gnss_acc","speed_kmh","azimuth_deg","altitude_m","lon","lat","gnss_utc","mcc","mnc","lac",
            "cell_id","pos_append_mask","satellites","dop1","dop2","dop3","gnss_trigger_type","gnss_jamming_state",
            "mileage_km","hour_meter","analog_in_1","analog_in_2","analog_in_3",
            "digital_fuel_sensor_data",
            "device_status",
            "uart_device_type",
            "send_time","count_hex","count_dec"
        ]
        placeholders = ",".join(["?"]*len(cols))
        sql = f"INSERT INTO gteri_records({','.join(cols)}) VALUES({placeholders})"
        data = [tuple(r.get(k) for k in cols) for r in rows]
        conn.executemany(sql, data)
        conn.commit()
    finally:
        conn.close()

def process_file(in_path: str, out_db: str, sheet: Optional[str]=None, col: Optional[str]=None, limit: Optional[int]=None):
    messages = read_any(in_path, sheet, col)
    parsed = []
    total = 0
    for line in messages:
        if limit and total >= limit:
            break
        total += 1
        rec = parse_line(line)
        if rec:
            parsed.append(rec)
    if not parsed:
        conn = sqlite3.connect(out_db)
        try:
            conn.executescript(SCHEMA_SQL)
            ensure_additional_columns(conn)
            conn.commit()
        finally:
            conn.close()
        return total, 0
    insert_records(out_db, parsed)
    return total, len(parsed)

def cli():
    ap = argparse.ArgumentParser(description="Procesador de tramas +RESP:GTERI de Queclink (GV310LAU, GV350CEU, GV58LAU) -> SQLite")
    ap.add_argument("--in", dest="in_path", required=True, help="Ruta de entrada (.txt, .csv, .xlsx)")
    ap.add_argument("--out", dest="out_db", required=True, help="Ruta de salida .db (SQLite)")
    ap.add_argument("--sheet", dest="sheet", help="Nombre/índice de hoja para .xlsx")
    ap.add_argument("--col", dest="col", help="Nombre de la columna que contiene las tramas en .csv/.xlsx")
    ap.add_argument("--limit", dest="limit", type=int, help="Procesar solo N filas (útil para pruebas)")
    args = ap.parse_args()
    total, ok = process_file(args.in_path, args.out_db, args.sheet, args.col, args.limit)
    print(f"Leídas: {total} | GTERI válidas: {ok} | DB: {args.out_db}")

if __name__ == "__main__":
    cli()