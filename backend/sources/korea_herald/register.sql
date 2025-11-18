-- Korea Herald科技新闻消息源注册脚本
-- 用于注册Korea Herald到message_platform系统

-- 设置字符集
SET NAMES utf8mb4;
SET CHARACTER_SET_CLIENT = utf8mb4;
SET CHARACTER_SET_CONNECTION = utf8mb4;

-- 1. 创建消息表
CREATE TABLE IF NOT EXISTS `mp_korea_herald_messages` (
    `id` VARCHAR(36) NOT NULL COMMENT '消息ID（UUID）',
    `source_id` VARCHAR(36) NOT NULL COMMENT '来源ID',
    `external_id` VARCHAR(200) DEFAULT NULL COMMENT '外部唯一标识（从URL路径提取article ID）',
    `title` VARCHAR(500) NOT NULL COMMENT '标题',
    `content` TEXT NOT NULL COMMENT '正文内容（从详情页提取）',
    `summary` TEXT DEFAULT NULL COMMENT '中文摘要（翻译后）',
    `provider` VARCHAR(500) DEFAULT NULL COMMENT '作者或信息提供方（The Korea Herald / Yonhap等）',
    `published_at` DATETIME DEFAULT NULL COMMENT '发布时间',
    `crawled_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
    `url` VARCHAR(500) NOT NULL COMMENT '原文链接（用于去重）',
    `region` VARCHAR(200) DEFAULT NULL COMMENT '地区（中文格式，多为"韩国"、"全球"等）',
    `industry_tags` TEXT DEFAULT NULL COMMENT '行业标签（逗号分隔，最多3个）',
    `ai_tag` VARCHAR(50) DEFAULT NULL COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',
    `category` VARCHAR(100) DEFAULT NULL COMMENT '分类（Business/Technology/AI等）',
    `language` VARCHAR(10) DEFAULT 'en' COMMENT '语言（en）',
    `metadata` JSON DEFAULT NULL COMMENT '其他元数据（JSON对象）',
    PRIMARY KEY (`id`),
    UNIQUE KEY `url` (`url`),
    KEY `idx_source_id` (`source_id`),
    KEY `idx_published_at` (`published_at`),
    KEY `idx_crawled_at` (`crawled_at`),
    KEY `idx_source_published` (`source_id`, `published_at`),
    KEY `idx_url` (`url`),
    KEY `idx_external_id` (`external_id`),
    KEY `idx_category` (`category`),
    KEY `idx_region` (`region`),
    CONSTRAINT `fk_korea_herald_source` FOREIGN KEY (`source_id`)
        REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Korea Herald科技新闻（韩国科技、半导体、AI领域新闻）消息表';

-- 2. 注册消息源到message_sources表
INSERT INTO `mp_message_sources` (
    `id`,
    `name`,
    `adapter_name`,
    `category`,
    `display_name`,
    `config`,
    `schedule`,
    `is_active`,
    `created_at`,
    `updated_at`
) VALUES (
    UUID(),
    'korea_herald',
    'korea_herald',
    'news',
    'Korea Herald科技新闻',
    JSON_OBJECT(
        'mysql_table', 'mp_korea_herald_messages',
        'chroma_collection', 'korea_herald',
        'collector_module', 'backend.sources.korea_herald.collector',
        'collector_class', 'KoreaHeraldCollector',
        'region', 'KR',
        'language', 'en',
        'interval', 14400,
        'description', 'Korea Herald科技新闻采集器，覆盖韩国科技、半导体（三星/SK Hynix）、AI、创新等领域'
    ),
    '0 */4 * * *',
    1,
    NOW(),
    NOW()
) ON DUPLICATE KEY UPDATE
    `display_name` = VALUES(`display_name`),
    `config` = VALUES(`config`),
    `schedule` = VALUES(`schedule`),
    `is_active` = VALUES(`is_active`),
    `updated_at` = NOW();

-- 3. 验证注册结果
SELECT
    id,
    name,
    display_name,
    category,
    is_active,
    JSON_EXTRACT(config, '$.mysql_table') as mysql_table,
    JSON_EXTRACT(config, '$.chroma_collection') as chroma_collection,
    created_at
FROM mp_message_sources
WHERE name = 'korea_herald';

-- 4. 验证表结构
SHOW CREATE TABLE mp_korea_herald_messages;

-- 注册完成
-- 采集器配置信息：
-- - 消息源名称：korea_herald
-- - 显示名称：Korea Herald科技新闻
-- - 分类：news
-- - 采集间隔：14400秒（4小时）
-- - Cron表达式：0 */4 * * *（每4小时执行一次）
-- - MySQL表：mp_korea_herald_messages
-- - ChromaDB集合：korea_herald
-- - 数据来源：https://www.koreaherald.com/rss/kh_Business
-- - 内容特点：韩国科技、半导体、AI、创新投资等领域新闻
