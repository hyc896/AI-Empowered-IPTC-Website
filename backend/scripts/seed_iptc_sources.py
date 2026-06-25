# -*- coding: utf-8 -*-
"""
Seed the current IPTC-oriented message sources.

This script registers collector modules that already exist in backend/sources.
It is safe to run repeatedly: existing source rows are merged, not deleted.
By default it enables national domestic sources and leaves Shanghai-specific
sources disabled until they are introduced as a dedicated source group.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import datetime
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BACKEND_DIR))


NATIONAL_SOURCE_NAMES = [
    "people_theory",
    "qstheory",
    "gmw_theory",
    "cssn",
    "cssn_phil",
    "studytimes",
    "people",
    "xinhua",
    "gmw",
    "cctv_news",
    "wenming",
    "thepaper",
    "cnr_local",
    "jyb",
    "eol",
    "stdaily",
    "wenlv_china",
    "cas_news",
    "rednet",
    "zhejiang_online",
    "sichuan_online",
    "dazhong_daily",
    "chinanews_minsheng",
    "china_mil",
    "huanqiu",
    "huanqiu_mil",
    "guancha",
    "ctnews",
]


SHANGHAI_SOURCE_NAMES = [
    "shanghai_observer",
    "thepaper_shanghai",
    "eastday",
    "people_sh_red",
    "shanghai_zhdj",
    "shanghai_party_history",
    "xinhua_shanghai",
]


LEGACY_SOURCE_NAMES = {
    "arxiv",
    "guardian",
    "techinasia",
    "gcg_ai",
    "wired",
    "lanacion",
    "axios",
    "venturebeat",
    "investing_com_news",
    "inteligencia_argentina",
    "cnbc",
    "financial_times",
    "ars_technica",
    "der_spiegel",
    "le_monde",
    "times_of_india",
    "techcrunch",
    "the_hindu",
    "partnership_ai",
    "govai",
    "securities_times",
    "kr36",
    "tonghuashun",
    "nikkei_asia_ai",
    "bloomberg",
    "wsj_tech",
}


def _display_name(name: str) -> str:
    return name.replace("_", " ").title()


SPECIAL_SOURCE_CONFIGS = {
    "shanghai_observer": {
        "auto_collect_enabled": True,
        "config": {
            "url": "https://www.shobserver.com/",
            "provider": "上观新闻",
            "category": "上海新闻",
        },
    },
    "thepaper_shanghai": {
        # 澎湃上海在服务器上偶发详情页超时，保留手动触发，暂不进入自动调度。
        "auto_collect_enabled": False,
        "config": {
            "url": "https://www.thepaper.cn/list_25488",
            "provider": "澎湃新闻上海频道",
            "category": "上海新闻",
        },
    },
    "eastday": {
        # 东方网内容面太广且历史上容易超时，先作为全国候选池外的手动源保留。
        "auto_collect_enabled": False,
        "config": {
            "url": "https://news.eastday.com/",
            "provider": "东方网",
            "category": "上海新闻",
        },
    },
    "people_sh_red": {
        "auto_collect_enabled": True,
        "config": {
            "urls": ["http://sh.people.com.cn/GB/138654/index.html"],
            "base_url": "http://sh.people.com.cn",
            "provider": "人民网上海党建频道",
            "category": "红色教育",
        },
    },
    "shanghai_zhdj": {
        "display_name": "上海智慧党建",
        "mysql_table": "mp_shanghai_local_messages",
        "collector_module": "backend.sources.shanghai_local.collector",
        "chroma_collection": "mp_shanghai_local_messages",
        "source_type": "news",
        "auto_collect_enabled": True,
        "interval": 1800,
        "config": {
            "urls": [
                "https://www.shzhdj.sh.cn/djWeb/djweb/web/djweb/webindex/index.action",
                "https://www.shzhdj.sh.cn/djWeb/djweb/web/djweb/newestindex/newestindex.action",
            ],
            "base_url": "https://www.shzhdj.sh.cn",
            "provider": "上海智慧党建",
            "category": "党建实践",
            "region": "中国/上海",
            "language": "zh",
            "max_articles": 20,
            "request_timeout": 15,
            "include_url_patterns": ["newinfo.action?articleid="],
        },
    },
    "shanghai_party_history": {
        "display_name": "上海党史网",
        "mysql_table": "mp_shanghai_local_messages",
        "collector_module": "backend.sources.shanghai_local.collector",
        "chroma_collection": "mp_shanghai_local_messages",
        "source_type": "news",
        "auto_collect_enabled": True,
        "interval": 3600,
        "config": {
            "urls": ["https://www.ccphistory.org.cn/"],
            "base_url": "https://www.ccphistory.org.cn",
            "provider": "上海党史网",
            "category": "党史红色文化",
            "region": "中国/上海",
            "language": "zh",
            "max_articles": 20,
            "request_timeout": 15,
            "include_url_patterns": ["/content/"],
        },
    },
    "xinhua_shanghai": {
        "display_name": "新华网上海频道",
        "mysql_table": "mp_shanghai_local_messages",
        "collector_module": "backend.sources.shanghai_local.collector",
        "chroma_collection": "mp_shanghai_local_messages",
        "source_type": "news",
        "auto_collect_enabled": True,
        "interval": 3600,
        "config": {
            "urls": ["http://sh.news.cn/main/index.htm"],
            "base_url": "http://sh.news.cn",
            "provider": "新华网上海频道",
            "category": "上海新闻",
            "region": "中国/上海",
            "language": "zh",
            "max_articles": 20,
            "request_timeout": 20,
            "include_url_patterns": ["sh.news.cn/", "/c.html"],
        },
    },
}


def _seed_config(name: str) -> dict:
    region = "\u4e2d\u56fd"
    seed = {
        "region": region,
        "language": "zh",
        "interval": 3600,
        "mysql_table": f"mp_{name}_messages",
        "collector_module": f"backend.sources.{name}.collector",
        "chroma_collection": f"mp_{name}_messages",
        "source_type": "iptc_national",
        "auto_collect_enabled": True,
        "config": {
            "region": region,
            "language": "zh",
            "max_articles": 20,
        },
    }
    special = SPECIAL_SOURCE_CONFIGS.get(name)
    if special:
        seed = {**seed, **special}
        seed["config"] = {**seed.get("config", {}), **special.get("config", {})}
    return seed


def _merge_config(seed: dict, existing: dict | None) -> dict:
    existing = existing or {}
    merged = {**existing, **seed}
    merged["config"] = {**existing.get("config", {}), **seed.get("config", {})}
    return merged


def seed_sources(
    activate_existing: bool = False,
    disable_legacy: bool = False,
    include_shanghai: bool = False,
) -> None:
    from backend.database.connection import create_session, init_database
    from backend.database.entities import MessageSource

    if not init_database():
        raise RuntimeError("database initialization failed")

    inserted = 0
    updated = 0
    unchanged = 0
    disabled = 0
    selected_sources = NATIONAL_SOURCE_NAMES + (SHANGHAI_SOURCE_NAMES if include_shanghai else [])

    with create_session() as db:
        now = datetime.now()
        for name in selected_sources:
            seed = _seed_config(name)
            source = db.query(MessageSource).filter(MessageSource.name == name).first()

            if source is None:
                source = MessageSource(
                    id=str(uuid.uuid4()),
                    name=name,
                    adapter_name=name,
                    category=seed["source_type"],
                    display_name=seed.get("display_name") or _display_name(name),
                    config=seed,
                    schedule=None,
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
                db.add(source)
                inserted += 1
                continue

            merged_config = _merge_config(seed, source.config)
            changed = merged_config != (source.config or {})

            if not source.adapter_name:
                source.adapter_name = name
                changed = True
            if not source.category:
                source.category = seed["source_type"]
                changed = True
            if not source.display_name:
                source.display_name = merged_config.get("display_name") or _display_name(name)
                changed = True
            if activate_existing and not source.is_active:
                source.is_active = True
                changed = True

            if changed:
                source.config = merged_config
                source.updated_at = now
                updated += 1
            else:
                unchanged += 1

        if disable_legacy:
            legacy_sources = db.query(MessageSource).filter(MessageSource.name.in_(LEGACY_SOURCE_NAMES)).all()
            for source in legacy_sources:
                if source.is_active:
                    source.is_active = False
                    source.updated_at = now
                    disabled += 1

            if not include_shanghai:
                shanghai_sources = db.query(MessageSource).filter(MessageSource.name.in_(SHANGHAI_SOURCE_NAMES)).all()
                for source in shanghai_sources:
                    if source.is_active:
                        source.is_active = False
                        source.updated_at = now
                        disabled += 1

    print(
        "IPTC sources seeded: "
        f"inserted={inserted}, updated={updated}, unchanged={unchanged}, disabled={disabled}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--activate-existing",
        action="store_true",
        help="Reactivate existing IPTC source rows if they are disabled.",
    )
    parser.add_argument(
        "--disable-legacy",
        action="store_true",
        help="Disable legacy Message Platform sources and, by default, Shanghai-specific sources.",
    )
    parser.add_argument(
        "--include-shanghai",
        action="store_true",
        help="Also seed and activate Shanghai-specific sources.",
    )
    args = parser.parse_args()
    seed_sources(
        activate_existing=args.activate_existing,
        disable_legacy=args.disable_legacy,
        include_shanghai=args.include_shanghai,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
