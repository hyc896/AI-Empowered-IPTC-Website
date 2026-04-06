# -*- coding: utf-8 -*-
"""
将爬取到的上海红色场馆数据导入到数据库
数据来源：venues_raw.json（612个场所类场馆，来自红途平台）
"""

import json
import uuid
import sys
from pathlib import Path

# 设置项目根路径，确保能 import database 模块
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 直接写死连接字符串，避免依赖.env加载路径问题
DATABASE_URL = "mysql+pymysql://root:Hyc174513@localhost:3306/iptc_practice"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)

from database.entities import Venue


def import_venues():
    raw_path = Path(__file__).parent / "venues_raw.json"
    with open(raw_path, "r", encoding="utf-8") as f:
        venues_data = json.load(f)

    print(f"读取到 {len(venues_data)} 条场馆数据")

    db = SessionLocal()
    try:
        # 检查当前数据库中已有多少条
        existing_count = db.query(Venue).filter(Venue.source == "红途").count()
        print(f"数据库中已有 {existing_count} 条红途场馆")

        if existing_count > 0:
            ans = input(f"已有 {existing_count} 条记录，是否跳过已存在的（按guid去重）？[Y/n] ").strip().lower()
            if ans == 'n':
                print("取消导入")
                return

        # 获取已有的 source_url 集合，用于去重
        existing_urls = set(
            row[0] for row in db.query(Venue.source_url).filter(Venue.source == "红途").all()
        )
        print(f"已有 source_url 数量：{len(existing_urls)}")

        inserted = 0
        skipped = 0

        for item in venues_data:
            guid = item.get("guid", "")
            source_url = f"https://red.library.sh.cn/minglu/#/result?guid={guid}" if guid else ""

            # 按 source_url 去重
            if source_url and source_url in existing_urls:
                skipped += 1
                continue

            # 处理图片列表
            media_list = item.get("mediaList") or []
            images = [m["filePath"] for m in media_list if m.get("filePath")]

            # 处理坐标
            try:
                lat = float(item["lat"]) if item.get("lat") else None
            except (ValueError, TypeError):
                lat = None
            try:
                lon = float(item["lon"]) if item.get("lon") else None
            except (ValueError, TypeError):
                lon = None

            venue = Venue(
                id=str(uuid.uuid4()),
                name=item.get("titleChs") or item.get("title") or "未命名",
                category=item.get("typeName"),          # 遗址 / 旧址 / 设施
                address=item.get("address") or "",
                latitude=lat,
                longitude=lon,
                description=item.get("description"),
                opening_hours=None,                      # 原始数据无此字段
                contact_phone=None,                      # 原始数据无此字段
                official_website=None,                   # 所有记录的 website 字段值相同，不导入
                related_knowledge_points=None,
                images=images if images else None,
                source="红途",
                source_url=source_url,
                is_verified=False,
                is_active=True,
            )
            db.add(venue)
            inserted += 1

            # 每100条提交一次，避免单次事务过大
            if inserted % 100 == 0:
                db.commit()
                print(f"  已提交 {inserted} 条...")

        db.commit()
        print(f"\n导入完成：新增 {inserted} 条，跳过（重复）{skipped} 条")

    except Exception as e:
        db.rollback()
        print(f"导入出错：{e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import_venues()
