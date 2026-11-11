"""Additively copy the legacy taxwise.db contents into the configured PostgreSQL DB.

Run this one-off utility only after applying schema.sql to the Supabase database.
It never modifies or deletes the SQLite source and skips PostgreSQL rows whose
primary keys exist with identical contents, making retries safe without
silently overwriting conflicting target data.
"""

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from psycopg import sql
from dotenv import load_dotenv

from database import get_db_connection

TABLES = (
    "users",
    "tax_profiles",
    "financial_inputs",
    "tax_rules",
    "recommendations",
    "documents",
    "chat_history",
)
TIMESTAMP_COLUMNS = {"created_at", "updated_at", "last_updated", "timestamp"}


def _convert_value(column: str, value: Any) -> Any:
    if value is not None and column in TIMESTAMP_COLUMNS and isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return value
    return value


def migrate(sqlite_path: Path) -> dict[str, tuple[int, int]]:
    if not sqlite_path.is_file():
        raise FileNotFoundError(f"SQLite source database does not exist: {sqlite_path}")

    source_uri = f"{sqlite_path.resolve().as_uri()}?mode=ro"
    source = sqlite3.connect(source_uri, uri=True)
    source.row_factory = sqlite3.Row
    try:
        available_tables = {
            row["name"]
            for row in source.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        missing_tables = set(TABLES) - available_tables
        if missing_tables:
            raise RuntimeError(
                "SQLite source is missing expected tables: "
                + ", ".join(sorted(missing_tables))
            )

        counts: dict[str, tuple[int, int]] = {}
        with get_db_connection() as target:
            for table in TABLES:
                rows = source.execute(f'SELECT * FROM "{table}"').fetchall()
                columns = [
                    row["name"]
                    for row in source.execute(f'PRAGMA table_info("{table}")').fetchall()
                ]
                insert = sql.SQL(
                    "INSERT INTO {} ({}) VALUES ({}) ON CONFLICT (id) DO NOTHING RETURNING id"
                ).format(
                    sql.Identifier("public", table),
                    sql.SQL(", ").join(map(sql.Identifier, columns)),
                    sql.SQL(", ").join(sql.Placeholder() for _ in columns),
                )
                select_existing = sql.SQL("SELECT {} FROM {} WHERE id = %s").format(
                    sql.SQL(", ").join(map(sql.Identifier, columns)),
                    sql.Identifier("public", table),
                )
                inserted_count = 0
                skipped_count = 0
                cursor = target.cursor()
                for row in rows:
                    values = tuple(_convert_value(column, row[column]) for column in columns)
                    cursor.execute(insert, values)
                    if cursor.fetchone():
                        inserted_count += 1
                        continue

                    cursor.execute(select_existing, (row["id"],))
                    existing = cursor.fetchone()
                    if existing is None or tuple(existing[column] for column in columns) != values:
                        raise RuntimeError(
                            f"Conflicting PostgreSQL row in {table} with id {row['id']}; "
                            "no migration changes were committed."
                        )
                    skipped_count += 1
                counts[table] = (inserted_count, skipped_count)

                target.execute(
                    sql.SQL(
                        """
                        SELECT setval(
                            pg_get_serial_sequence(%s, 'id'),
                            COALESCE(MAX(id), 1),
                            MAX(id) IS NOT NULL
                        )
                        FROM {}
                        """
                    ).format(sql.Identifier("public", table)),
                    (f"public.{table}",),
                )
        return counts
    finally:
        source.close()


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "sqlite_path",
        nargs="?",
        type=Path,
        default=Path(__file__).with_name("taxwise.db"),
        help="Path to the existing SQLite database (default: ./taxwise.db)",
    )
    args = parser.parse_args()
    counts = migrate(args.sqlite_path)
    for table, (inserted, skipped) in counts.items():
        print(f"{table}: {inserted} row(s) inserted; {skipped} identical row(s) skipped")
    print("Migration finished. The SQLite source was not modified.")


if __name__ == "__main__":
    main()
