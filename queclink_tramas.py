"""CLI para homologar tramas Queclink usando las especificaciones YAML."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Iterable, Optional

from queclink.ingestor_sqlite import SQLiteIngestor
from queclink.parser import identify_head, load_spec, model_from_imei, parse_line

_LOGGER = logging.getLogger(__name__)


def _split_fields(line: str) -> list[str]:
    payload = line.strip()
    if payload.endswith("$"):
        payload = payload[:-1]
    if not payload:
        return []
    return [part.strip() for part in payload.split(",")]


def _process_line(
    raw_line: str,
    ingestor: SQLiteIngestor,
    *,
    line_number: int,
) -> bool:
    head = identify_head(raw_line)
    if not head:
        _LOGGER.warning("Línea %s: encabezado no reconocido", line_number)
        return False

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
        record = parse_line(raw_line, head.source, model, head.report, spec=spec)
    except Exception as exc:  # pragma: no cover - errores de parsing específicos
        _LOGGER.warning("Línea %s: error al parsear la trama (%s)", line_number, exc)
        return False

    ingestor.insert(model, head.report, record, spec=spec)
    return True


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
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    logging.basicConfig(level=log_level, format="[%(levelname)s] %(message)s")

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"[ERROR] No se encontró el archivo de entrada: {input_path}", file=sys.stderr)
        return 1

    ingestor = SQLiteIngestor(output_path)
    inserted = 0
    try:
        for line_number, line in enumerate(_iter_lines(input_path), start=1):
            if _process_line(line, ingestor, line_number=line_number):
                inserted += 1
    finally:
        ingestor.close()

    print(f"[OK] {inserted} tramas homologadas en {output_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

