# -*- coding: utf-8 -*-
"""
消息平台数据库初始化脚本
创建核心表结构和基本消息源配置
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database.connection import init_database, create_session
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def main():
    """初始化数据库"""

    logger.info("=" * 80)
    logger.info("消息平台数据库初始化")
    logger.info("=" * 80)

    # 初始化数据库连接
    logger.info("\n[1/5] 初始化数据库连接...")
    init_database()

    with create_session() as db:
        # 1. 创建消息源配置表
        logger.info("\n[2/5] 创建mp_message_sources表...")
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS `mp_message_sources` (
              `id` VARCHAR(36) NOT NULL COMMENT '消息源ID（UUID）',
              `name` VARCHAR(100) NOT NULL COMMENT '源名称',
              `adapter_name` VARCHAR(100) NOT NULL COMMENT '适配器名称',
              `category` VARCHAR(50) COMMENT '业务类别',
              `display_name` VARCHAR(100) COMMENT '显示名称',
              `config` JSON COMMENT '适配器配置',
              `schedule` VARCHAR(50) COMMENT '定时任务cron表达式',
              `is_active` TINYINT(1) DEFAULT 1 COMMENT '是否启用',
              `last_crawled_at` DATETIME COMMENT '最后抓取时间',
              `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
              `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
              PRIMARY KEY (`id`),
              UNIQUE KEY `uk_name` (`name`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='消息源配置表'
        """))
        db.commit()
        logger.info("  ✓ mp_message_sources表创建成功")

        # 2. 创建同花顺消息表
        logger.info("\n[3/5] 创建mp_tonghuashun_messages表...")
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS `mp_tonghuashun_messages` (
              `id` VARCHAR(36) NOT NULL COMMENT '消息ID',
              `source_id` VARCHAR(36) NOT NULL COMMENT '来源ID',
              `seq` VARCHAR(50) NOT NULL COMMENT '同花顺seq',
              `title` VARCHAR(500) NOT NULL COMMENT '标题',
              `content` TEXT NOT NULL COMMENT '正文内容',
              `summary` TEXT COMMENT '摘要',
              `digest` VARCHAR(500) COMMENT '摘要简短版',
              `url` VARCHAR(500) NOT NULL COMMENT '原文链接',
              `provider` VARCHAR(500) COMMENT '信息提供方',
              `image_url` VARCHAR(1000) COMMENT '图片链接',
              `published_at` DATETIME COMMENT '发布时间',
              `crawled_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
              `industry_tags` VARCHAR(500) COMMENT '行业标签',
              `region` VARCHAR(100) COMMENT '地区',
              PRIMARY KEY (`id`),
              UNIQUE KEY `uk_url` (`url`),
              KEY `idx_seq` (`seq`),
              KEY `idx_source_id` (`source_id`),
              KEY `idx_published_at` (`published_at`),
              KEY `idx_source_published` (`source_id`, `published_at`),
              KEY `idx_crawled_at` (`crawled_at`),
              CONSTRAINT `fk_tonghuashun_source` FOREIGN KEY (`source_id`)
                REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='同花顺消息表'
        """))
        db.commit()
        logger.info("  ✓ mp_tonghuashun_messages表创建成功")

        # 3. 创建36氪消息表
        logger.info("\n[4/5] 创建mp_kr36_messages表...")
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS `mp_kr36_messages` (
              `id` VARCHAR(36) NOT NULL COMMENT '消息ID',
              `source_id` VARCHAR(36) NOT NULL COMMENT '来源ID',
              `item_id` VARCHAR(50) NOT NULL COMMENT '36氪item_id',
              `title` VARCHAR(500) NOT NULL COMMENT '标题',
              `content` TEXT NOT NULL COMMENT '正文内容',
              `summary` TEXT COMMENT '摘要',
              `published_at` DATETIME COMMENT '发布时间',
              `kr_route` VARCHAR(500) COMMENT '36氪页面路由',
              `source_url` VARCHAR(500) COMMENT '原文链接',
              `image_url` VARCHAR(1000) COMMENT '图片链接',
              `crawled_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
              `comment_count` INT DEFAULT 0 COMMENT '评论数',
              `has_relevant` TINYINT(1) DEFAULT 0 COMMENT '是否有相关内容',
              PRIMARY KEY (`id`),
              UNIQUE KEY `uk_item_id` (`item_id`),
              KEY `idx_source_id` (`source_id`),
              KEY `idx_published_at` (`published_at`),
              KEY `idx_source_published` (`source_id`, `published_at`),
              KEY `idx_crawled_at` (`crawled_at`),
              CONSTRAINT `fk_kr36_source` FOREIGN KEY (`source_id`)
                REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='36氪快讯表'
        """))
        db.commit()
        logger.info("  ✓ mp_kr36_messages表创建成功")

        # 4. 注册消息源
        logger.info("\n[5/5] 注册消息源配置...")

        # 注册同花顺
        db.execute(text("""
            INSERT INTO `mp_message_sources` (
              `id`, `name`, `adapter_name`, `category`, `display_name`,
              `config`, `schedule`, `is_active`, `created_at`, `updated_at`
            ) VALUES (
              UUID(), 'tonghuashun', 'tonghuashun_collector', 'newsflash', '同花顺7x24快讯',
              JSON_OBJECT(
                'url', 'https://news.10jqka.com.cn/realtimenews.html',
                'interval', 15,
                'mysql_table', 'mp_tonghuashun_messages',
                'chroma_collection', 'mp_tonghuashun'
              ),
              '0 */1 * * * *', 1, NOW(), NOW()
            ) ON DUPLICATE KEY UPDATE
              `adapter_name` = VALUES(`adapter_name`),
              `display_name` = VALUES(`display_name`),
              `config` = VALUES(`config`),
              `updated_at` = CURRENT_TIMESTAMP
        """))
        logger.info("  ✓ 同花顺消息源注册成功")

        # 注册36氪
        db.execute(text("""
            INSERT INTO `mp_message_sources` (
              `id`, `name`, `adapter_name`, `category`, `display_name`,
              `config`, `schedule`, `is_active`, `created_at`, `updated_at`
            ) VALUES (
              UUID(), 'kr36', 'kr36_collector', 'newsflash', '36氪快讯',
              JSON_OBJECT(
                'url', 'https://www.36kr.com/newsflashes',
                'interval', 180,
                'mysql_table', 'mp_kr36_messages',
                'chroma_collection', 'mp_kr36'
              ),
              '0 */3 * * * *', 1, NOW(), NOW()
            ) ON DUPLICATE KEY UPDATE
              `adapter_name` = VALUES(`adapter_name`),
              `display_name` = VALUES(`display_name`),
              `config` = VALUES(`config`),
              `updated_at` = CURRENT_TIMESTAMP
        """))
        logger.info("  ✓ 36氪消息源注册成功")

        db.commit()

        # 验证结果
        logger.info("\n" + "=" * 80)
        logger.info("验证注册结果")
        logger.info("=" * 80)

        result = db.execute(text("""
            SELECT
              name,
              display_name,
              category,
              is_active,
              JSON_EXTRACT(config, '$.mysql_table') AS mysql_table,
              JSON_EXTRACT(config, '$.chroma_collection') AS chroma_collection
            FROM mp_message_sources
            ORDER BY name
        """))

        rows = result.fetchall()
        if rows:
            logger.info(f"\n已注册 {len(rows)} 个消息源:")
            for row in rows:
                logger.info(f"  - {row[1]} (名称: {row[0]})")
                logger.info(f"    分类: {row[2]}, 状态: {'启用' if row[3] else '禁用'}")
                logger.info(f"    MySQL表: {row[4]}, ChromaDB集合: {row[5]}")
        else:
            logger.warning("  ⚠ 未找到消息源配置")

    logger.info("\n" + "=" * 80)
    logger.info("✓ 数据库初始化完成！")
    logger.info("=" * 80)
    logger.info("\n提示：现在可以启动消息平台服务了")
    logger.info("  python backend/main.py")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(f"\n✗ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
