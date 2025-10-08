"""Shim de compatibilidad para los analizadores de tramas Queclink."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, Optional

from queclink.parser import parse_gteri, parse_gtinf, parse_line
from src.ingestors.sqlite_gtinf import ensure_db, ingest_lines

__all__ = ["parse_line", "parse_gteri", "parse_gtinf", "parse_line_to_record"]


parse_line_to_record = parse_line


def _read_lines(path: Path) -> Iterable[str]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            yield line


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Homologador CLI para tramas Queclink GTINF/GTERI",
    )
    parser.add_argument(
        "--in",
        dest="input",
        required=True,
        help="Archivo de texto con las tramas a homologar.",
    )
    parser.add_argument(
        "--out",
        dest="output",
        required=True,
        help="Ruta donde se almacenará la base de datos SQLite resultante.",
    )
    parser.add_argument(
        "--message",
        dest="message",
        choices=["GTINF", "GTERI"],
        help="Filtrar el procesamiento solo a un tipo de trama específico.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    output_path = Path(args.output)
    message_filter = args.message

    if not input_path.exists():
        print(f"[ERROR] No se encontró el archivo de entrada: {input_path}", file=sys.stderr)
        return 1

    print(f"[INFO] Creando base de datos en {output_path}")
    conn = ensure_db(output_path)

    print(f"[INFO] Procesando tramas desde {input_path}")
    if message_filter:
        print(f"[INFO] Filtrando únicamente tramas {message_filter}")

    try:
        inserted = ingest_lines(conn, _read_lines(input_path), message=message_filter)
    finally:
        conn.close()

    print(f"[OK] {inserted} tramas insertadas en {output_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover - compatibilidad CLI
    sys.exit(main())
