# -*- coding: utf-8 -*-
"""
Deployment doctor for the IPTC collector/case-generation service.

Run inside the collector container:
    python -X utf8 backend/scripts/deployment_doctor.py

Or from the 一期 directory locally:
    python -X utf8 backend/scripts/deployment_doctor.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BACKEND_DIR))


def _status(ok: bool) -> str:
    return "OK" if ok else "FAIL"


def _print_check(name: str, ok: bool, detail: str = "") -> None:
    suffix = f" - {detail}" if detail else ""
    print(f"[{_status(ok)}] {name}{suffix}")


def _redact_url(raw: str) -> str:
    if not raw:
        return ""
    try:
        parsed = urlsplit(raw)
        if "@" not in parsed.netloc:
            return raw
        userinfo, hostinfo = parsed.netloc.rsplit("@", 1)
        user = userinfo.split(":", 1)[0]
        return urlunsplit((parsed.scheme, f"{user}:***@{hostinfo}", parsed.path, parsed.query, parsed.fragment))
    except Exception:
        return "<redacted>"


def check_files() -> int:
    failures = 0
    prompt = BACKEND_DIR / "data" / "prompts" / "news_to_case.md"
    kp_json = BACKEND_DIR / "data" / "knowledge_points.json"
    chroma_path = Path(os.getenv("CHROMADB_PATH", str(BACKEND_DIR / "data" / "chromadb_new")))

    checks = [
        ("case prompt", prompt.exists(), str(prompt)),
        ("knowledge_points.json", kp_json.exists(), str(kp_json)),
        ("ChromaDB path", chroma_path.exists(), str(chroma_path)),
    ]
    for name, ok, detail in checks:
        _print_check(name, ok, detail)
        failures += 0 if ok else 1

    if kp_json.exists():
        try:
            import json

            data = json.loads(kp_json.read_text(encoding="utf-8"))
            ok = len(data) > 0
            _print_check("knowledge point count", ok, str(len(data)))
            failures += 0 if ok else 1
        except Exception as exc:
            _print_check("knowledge point count", False, str(exc))
            failures += 1

    return failures


def check_config() -> tuple[int, dict]:
    failures = 0
    try:
        from backend.config.config_manager import ConfigManager

        config_path = PROJECT_ROOT / "config.yaml"
        manager = ConfigManager()
        ok = manager.load_config(str(config_path))
        config = manager.get_config() if ok else {}
        _print_check("config.yaml", ok, str(config_path))
        failures += 0 if ok else 1
    except Exception as exc:
        _print_check("config.yaml", False, str(exc))
        return 1, {}

    celery = config.get("celery", {}) if config else {}
    broker_url = celery.get("broker", {}).get("url", "")
    result_backend = celery.get("result_backend", {}).get("url", "")
    mysql = config.get("database", {}).get("mysql", {}) if config else {}
    chroma = config.get("database", {}).get("chromadb", {}) if config else {}

    _print_check("Celery broker target", bool(broker_url), _redact_url(broker_url))
    _print_check("Celery backend target", bool(result_backend), _redact_url(result_backend))
    _print_check("MySQL target", bool(mysql), f"{mysql.get('host')}:{mysql.get('port')}/{mysql.get('database')}")
    _print_check("ChromaDB mode/path", bool(chroma), f"{chroma.get('mode')} {chroma.get('path')}")

    failures += 0 if broker_url and result_backend and mysql and chroma else 1
    return failures, config


def check_redis(config: dict) -> int:
    broker_url = config.get("celery", {}).get("broker", {}).get("url", "")
    if not broker_url:
        _print_check("Redis ping", False, "missing broker url")
        return 1

    try:
        import redis

        client = redis.from_url(broker_url, socket_connect_timeout=3, socket_timeout=3)
        ok = client.ping()
        _print_check("Redis ping", bool(ok), _redact_url(broker_url))
        return 0 if ok else 1
    except Exception as exc:
        _print_check("Redis ping", False, str(exc))
        return 1


def check_database() -> int:
    failures = 0
    try:
        from backend.database.connection import init_database, create_session
        from backend.database.entities import MessageSource, IPTCCase
        from backend.scripts.seed_iptc_sources import LEGACY_SOURCE_NAMES, NATIONAL_SOURCE_NAMES
        from sqlalchemy import text

        ok = init_database()
        _print_check("database init", ok)
        if not ok:
            return 1

        with create_session() as db:
            source_count = db.query(MessageSource).count()
            active_source_count = db.query(MessageSource).filter(MessageSource.is_active == True).count()
            active_national_count = db.query(MessageSource).filter(
                MessageSource.name.in_(NATIONAL_SOURCE_NAMES),
                MessageSource.is_active == True,
            ).count()
            active_legacy_count = db.query(MessageSource).filter(
                MessageSource.name.in_(LEGACY_SOURCE_NAMES),
                MessageSource.is_active == True,
            ).count()
            case_count = db.query(IPTCCase).count()

            _print_check("mp_message_sources rows", source_count > 0, str(source_count))
            _print_check("active message sources", active_source_count > 0, str(active_source_count))
            _print_check("active national IPTC sources", active_national_count > 0, str(active_national_count))
            _print_check("active legacy Message Platform sources", active_legacy_count == 0, str(active_legacy_count))
            _print_check("iptc_cases rows", True, str(case_count))

            kp_rel_exists = db.execute(text("SHOW TABLES LIKE 'iptc_message_knowledge_relations'")).fetchone() is not None
            _print_check("relation table", kp_rel_exists, "iptc_message_knowledge_relations")

            failures += 0 if (
                source_count > 0
                and active_source_count > 0
                and active_national_count > 0
                and active_legacy_count == 0
                and kp_rel_exists
            ) else 1
    except Exception as exc:
        _print_check("database checks", False, str(exc))
        failures += 1

    return failures


def check_chromadb(config: dict) -> int:
    try:
        import chromadb

        chroma = config.get("database", {}).get("chromadb", {})
        path = chroma.get("path") or os.getenv("CHROMADB_PATH") or str(BACKEND_DIR / "data" / "chromadb_new")
        if not os.path.isabs(path):
            path = str(PROJECT_ROOT / path)
        client = chromadb.PersistentClient(path=path)
        collection = client.get_collection("iptc_knowledge_points")
        count = collection.count()
        _print_check("ChromaDB iptc_knowledge_points", count > 0, f"{count} vectors at {path}")
        return 0 if count > 0 else 1
    except Exception as exc:
        _print_check("ChromaDB iptc_knowledge_points", False, str(exc))
        return 1


def main() -> int:
    print("IPTC deployment doctor")
    print("=" * 60)
    failures = 0
    failures += check_files()
    config_failures, config = check_config()
    failures += config_failures
    if config:
        failures += check_redis(config)
        failures += check_database()
        failures += check_chromadb(config)
    print("=" * 60)
    if failures:
        print(f"FAILED checks: {failures}")
        return 1
    print("All checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
