# -*- coding: utf-8 -*-
"""
Idempotent schema migration for the IPTC collector/case-generation database.

Run inside the collector container:
    python -X utf8 backend/scripts/migrate_iptc_schema.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BACKEND_DIR))


def _scalar(conn, sql: str, params: dict | None = None):
    return conn.execute(text(sql), params or {}).scalar()


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    return bool(
        _scalar(
            conn,
            """
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = :table_name
              AND column_name = :column_name
            """,
            {"table_name": table_name, "column_name": column_name},
        )
    )


def _index_exists(conn, table_name: str, index_name: str) -> bool:
    return bool(
        _scalar(
            conn,
            """
            SELECT COUNT(*)
            FROM information_schema.statistics
            WHERE table_schema = DATABASE()
              AND table_name = :table_name
              AND index_name = :index_name
            """,
            {"table_name": table_name, "index_name": index_name},
        )
    )


def migrate() -> None:
    from backend.database.connection import get_engine, init_database

    if not init_database():
        raise RuntimeError("database initialization failed")

    engine = get_engine()
    default_region = "\u5168\u56fd"

    with engine.begin() as conn:
        if not _column_exists(conn, "iptc_cases", "primary_region"):
            conn.execute(
                text(
                    """
                    ALTER TABLE iptc_cases
                    ADD COLUMN primary_region VARCHAR(50) NOT NULL
                    DEFAULT :default_region
                    AFTER published_at
                    """
                ),
                {"default_region": default_region},
            )
            print("[OK] added iptc_cases.primary_region")
        else:
            print("[SKIP] iptc_cases.primary_region already exists")

        if not _column_exists(conn, "iptc_cases", "mentioned_locations"):
            conn.execute(
                text(
                    """
                    ALTER TABLE iptc_cases
                    ADD COLUMN mentioned_locations JSON NULL
                    AFTER primary_region
                    """
                )
            )
            print("[OK] added iptc_cases.mentioned_locations")
        else:
            print("[SKIP] iptc_cases.mentioned_locations already exists")

        if not _index_exists(conn, "iptc_cases", "idx_primary_region"):
            conn.execute(text("CREATE INDEX idx_primary_region ON iptc_cases(primary_region)"))
            print("[OK] added idx_primary_region")
        else:
            print("[SKIP] idx_primary_region already exists")

        result = conn.execute(
            text(
                """
                UPDATE iptc_cases
                SET primary_region = :default_region
                WHERE primary_region IS NULL OR primary_region = ''
                """
            ),
            {"default_region": default_region},
        )
        print(f"[OK] backfilled primary_region rows: {result.rowcount}")

    print("IPTC schema migration completed")


if __name__ == "__main__":
    migrate()
