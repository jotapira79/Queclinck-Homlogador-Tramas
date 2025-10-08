"""Módulos de ingesta para homologador Queclink."""

from .sqlite_gtinf import ensure_db, ingest_lines  # noqa: F401

__all__ = ["ensure_db", "ingest_lines"]
