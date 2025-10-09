"""SQLite ingestion utilities constrained by the YAML specs."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from .parser import FieldSpec, Spec, load_spec


def _type_to_sql(field: FieldSpec) -> str:
    field_type = field.type.lower()
    if field_type in {"int", "integer", "enum", "bool", "boolean"}:
        return "INTEGER"
    if field_type in {"float", "double", "decimal"}:
        return "REAL"
    return "TEXT"


def _normalize_value(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return int(value)
    return value


@dataclass
class SQLiteIngestor:
    db_path: Path

    def __post_init__(self) -> None:
        self.connection = sqlite3.connect(str(self.db_path))

    def close(self) -> None:
        self.connection.close()

    def ensure_table(self, model: str, message: str, spec: Optional[Spec] = None) -> Sequence[FieldSpec]:
        spec = spec or load_spec(model, message)
        fields = spec.fields
        table = spec.table_name
        conn = self.connection

        existing = self._table_columns(table)
        if not existing:
            columns_sql = ", ".join(f'"{field.name}" {_type_to_sql(field)}' for field in fields)
            conn.execute(f"CREATE TABLE IF NOT EXISTS {table} ({columns_sql})")
        else:
            for field in fields:
                if field.name not in existing:
                    conn.execute(
                        f"ALTER TABLE {table} ADD COLUMN \"{field.name}\" {_type_to_sql(field)}"
                    )
        conn.commit()
        return fields

    def insert(self, model: str, message: str, record: dict, spec: Optional[Spec] = None) -> None:
        spec = spec or load_spec(model, message)
        fields = self.ensure_table(model, message, spec)
        table = spec.table_name
        columns = [field.name for field in fields]
        placeholders = ", ".join(["?"] * len(columns))
        values = [_normalize_value(record.get(column)) for column in columns]
        column_names = ", ".join(f'"{col}"' for col in columns)
        sql = f"INSERT INTO {table} ({column_names}) VALUES ({placeholders})"
        self.connection.execute(sql, values)
        self.connection.commit()

    def _table_columns(self, table: str) -> set[str]:
        cursor = self.connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        if not cursor.fetchone():
            return set()
        info = self.connection.execute(f"PRAGMA table_info({table})")
        return {row[1] for row in info.fetchall()}


__all__ = ["SQLiteIngestor"]

