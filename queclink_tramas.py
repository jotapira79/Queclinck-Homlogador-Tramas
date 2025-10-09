"""CLI para homologar tramas Queclink usando las especificaciones YAML."""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from pathlib import Path
from typing import Iterable, Optional

from queclink.ingestor_sqlite import SQLiteIngestor
from queclink.parser import HeadInfo, identify_head, load_spec, model_from_imei, parse_line
from queclink.parser import Spec

_LOGGER = logging.getLogger(__name__)


def _split_fields(line: str) -> list[str]:
    payload = line.strip()
    if payload.endswith("$"):
        payload = payload[:-1]
    if not payload:
        return []
    return [part.strip() for part in payload.split(",")]


def _normalize_report_name(message: str) -> str:
    normalized = (message or "").strip().upper()
    if not normalized:
        return normalized
    if not normalized.startswith("GT"):
        normalized = f"GT{normalized}"
    return normalized


def _prepare_line_for_parsing(raw_line: str, head: HeadInfo) -> str:
    report = head.report or ""
    if not report.startswith("GT"):
        return raw_line
    suffix = report[2:]
    for prefix in ("+RESP:GT", "+BUFF:GT"):
        marker = f"{prefix}{suffix}"
        if raw_line.startswith(marker):
            return raw_line.replace(marker, f"{prefix},{suffix}", 1)
    return raw_line


def _process_line(
    raw_line: str,
    ingestor: SQLiteIngestor,
    *,
    line_number: int,
    expected_report: Optional[str] = None,
) -> bool:
    head = identify_head(raw_line)
    if not head:
        _LOGGER.warning("Línea %s: encabezado no reconocido", line_number)
        return False

    if expected_report:
        normalized = _normalize_report_name(expected_report)
        if head.report.upper() != normalized:
            _LOGGER.debug(
                "Línea %s: se omitió trama %s por no coincidir con --message=%s",
                line_number,
                head.report,
                normalized,
            )
            return False

    normalized_line = _prepare_line_for_parsing(raw_line, head)

    fields = _split_fields(raw_line)
    if len(fields) < 3:
        _LOGGER.warning("Línea %s: trama sin IMEI", line_number)
        return False

    imei = fields[2]
    model = model_from_imei(imei)
    if not model:
        _LOGGER.warning("Línea %s: prefijo IMEI no homologado (%s)", line_number, imei)
        return False

    try:
        spec = load_spec(model, head.report)
    except FileNotFoundError:
        _LOGGER.warning(
            "Línea %s: no se encontró la spec para %s/%s", line_number, model, head.report
        )
        return False

    try:
        record = parse_line(normalized_line, head.source, model, head.report, spec=spec)
    except Exception as exc:  # pragma: no cover - errores de parsing específicos
        if head.report.upper() == "GTINF":
            record = _relaxed_gtinf_parse(normalized_line, spec)
            if record is None:
                _LOGGER.warning("Línea %s: error al parsear la trama (%s)", line_number, exc)
                return False
            _LOGGER.debug(
                "Línea %s: se aplicó parsing relajado para GTINF (%s)", line_number, exc
            )
        else:
            _LOGGER.warning("Línea %s: error al parsear la trama (%s)", line_number, exc)
            return False

    ingestor.insert(model, head.report, record, spec=spec)
    return True


def _safe_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _get_token(tokens: list[str], index: int) -> Optional[str]:
    if index < 0 or index >= len(tokens):
        return None
    value = tokens[index].strip()
    return value or None


def _build_gteri_record(tokens: list[str], raw_line: str) -> Optional[dict[str, object]]:
    if not tokens:
        return None
    prefix = tokens[0].upper()
    if not prefix.startswith("+RESP:GTERI") and not prefix.startswith("+BUFF:GTERI"):
        return None

    record: dict[str, object] = {
        "prefix": tokens[0],
        "message": "GTERI",
        "is_buff": 1 if prefix.startswith("+BUFF") else 0,
        "imei": _get_token(tokens, 2),
        "model": (_get_token(tokens, 3) or "").upper() or None,
        "report_type": _get_token(tokens, 6),
        "speed_kmh": _safe_float(_get_token(tokens, 9)),
        "azimuth_deg": _safe_int(_get_token(tokens, 10)),
        "altitude_m": _safe_float(_get_token(tokens, 11)),
        "lon": _safe_float(_get_token(tokens, 12)),
        "lat": _safe_float(_get_token(tokens, 13)),
        "gnss_utc": _get_token(tokens, 14),
        "mcc": _get_token(tokens, 15),
        "mnc": _get_token(tokens, 16),
        "lac": _get_token(tokens, 17),
        "cell_id": _get_token(tokens, 18),
        "pos_append_mask": _get_token(tokens, 19),
        "send_time": _get_token(tokens, len(tokens) - 2),
        "count_hex": _get_token(tokens, len(tokens) - 1),
        "raw_line": raw_line,
    }
    return record


def _ensure_gteri_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS gteri_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prefix TEXT,
            message TEXT,
            imei TEXT,
            model TEXT,
            report_type TEXT,
            is_buff INTEGER,
            lon REAL,
            lat REAL,
            speed_kmh REAL,
            azimuth_deg INTEGER,
            altitude_m REAL,
            gnss_utc TEXT,
            send_time TEXT,
            count_hex TEXT,
            mcc TEXT,
            mnc TEXT,
            lac TEXT,
            cell_id TEXT,
            pos_append_mask TEXT,
            raw_line TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_gteri_records_imei ON gteri_records(imei)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_gteri_records_time ON gteri_records(send_time)"
    )
    conn.commit()


def _insert_gteri_record(conn: sqlite3.Connection, record: dict[str, object]) -> None:
    columns = [
        "prefix",
        "message",
        "imei",
        "model",
        "report_type",
        "is_buff",
        "lon",
        "lat",
        "speed_kmh",
        "azimuth_deg",
        "altitude_m",
        "gnss_utc",
        "send_time",
        "count_hex",
        "mcc",
        "mnc",
        "lac",
        "cell_id",
        "pos_append_mask",
        "raw_line",
    ]
    placeholders = ", ".join(["?"] * len(columns))
    values = [record.get(column) for column in columns]
    conn.execute(
        f"INSERT INTO gteri_records ({', '.join(columns)}) VALUES ({placeholders})",
        values,
    )


def _ingest_gteri_lines(input_path: Path, output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(output_path))
    try:
        _ensure_gteri_table(conn)
        inserted = 0
        for line_number, raw_line in enumerate(_iter_lines(input_path), start=1):
            tokens = _split_fields(raw_line)
            record = _build_gteri_record(tokens, raw_line)
            if record is None:
                _LOGGER.debug(
                    "Línea %s: se omitió trama que no coincide con +RESP/+BUFF:GTERI",
                    line_number,
                )
                continue
            try:
                _insert_gteri_record(conn, record)
            except sqlite3.DatabaseError as exc:
                _LOGGER.warning(
                    "Línea %s: error al insertar trama GTERI (%s)", line_number, exc
                )
                continue
            inserted += 1
        conn.commit()
        return inserted
    finally:
        conn.close()


def _relaxed_gtinf_parse(line: str, spec: Spec) -> Optional[dict[str, object]]:
    tokens = _split_fields(line)
    if len(tokens) < len(spec.fields):
        return None
    record: dict[str, object] = {}
    for field, token in zip(spec.fields, tokens):
        value: Optional[str] = token if token != "" else None
        record[field.name] = value
    record.setdefault("raw_line", line)
    return record


def _iter_lines(path: Path) -> Iterable[str]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                yield stripped


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Homologador de tramas Queclink controlado por especificaciones YAML",
    )
    parser.add_argument("--in", dest="input", required=True, help="Archivo de tramas")
    parser.add_argument(
        "--out",
        dest="output",
        required=True,
        help="Ruta al archivo SQLite donde se guardarán los resultados",
    )
    parser.add_argument(
        "--log-level",
        dest="log_level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Nivel de log a utilizar",
    )
    parser.add_argument(
        "--message",
        dest="message",
        help="Tipo de mensaje a homologar (por ejemplo GTINF, GTERI)",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    logging.basicConfig(level=log_level, format="[%(levelname)s] %(message)s")

    input_path = Path(args.input)
    output_path = Path(args.output)
    expected_report = _normalize_report_name(args.message) if args.message else None

    if not input_path.exists():
        print(f"[ERROR] No se encontró el archivo de entrada: {input_path}", file=sys.stderr)
        return 1

    if expected_report == "GTERI":
        inserted = _ingest_gteri_lines(input_path, output_path)
        print(f"[OK] {inserted} tramas GTERI homologadas en {output_path}")
        return 0

    ingestor = SQLiteIngestor(output_path)
    inserted = 0
    try:
        for line_number, line in enumerate(_iter_lines(input_path), start=1):
            if _process_line(
                line,
                ingestor,
                line_number=line_number,
                expected_report=expected_report,
            ):
                inserted += 1
    finally:
        ingestor.close()

    print(f"[OK] {inserted} tramas homologadas en {output_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

