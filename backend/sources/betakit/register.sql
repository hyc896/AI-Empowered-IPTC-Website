-- BetaKit Canadian Tech News 注册脚本
-- 执行前请确保MySQL数据库连接正常

USE message_platform;

-- 1. 创建BetaKit消息表
CREATE TABLE IF NOT EXISTS `mp_betakit_messages` (
    `id` VARCHAR(36) NOT NULL COMMENT '消息ID（UUID）',
    `source_id` VARCHAR(36) NOT NULL COMMENT '来源ID',
    `external_id` VARCHAR(200) DEFAULT NULL COMMENT '外部唯一标识（从RSS guid提取的post ID或URL slug）',
    `title` VARCHAR(500) NOT NULL COMMENT '标题',
    `content` TEXT NOT NULL COMMENT '正文内容（从RSS content:encoded清理HTML后提取）',
    `summary` TEXT DEFAULT NULL COMMENT '摘要（中文翻译，来自RSS description）',
    `provider` VARCHAR(500) DEFAULT NULL COMMENT '作者（RSS dc:creator字段）',
    `published_at` DATETIME DEFAULT NULL COMMENT '发布时间（RSS pubDate字段）',
    `crawled_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
    `url` VARCHAR(500) NOT NULL COMMENT '原文链接（用于去重）',

    -- 新增必备字段（2025年强制要求）
    `region` VARCHAR(200) DEFAULT NULL COMMENT '地区（中文格式，主要为"加拿大"或"加拿大/省份"）',
    `industry_tags` TEXT DEFAULT NULL COMMENT '行业标签（逗号分隔，最多3个）',
    `ai_tag` VARCHAR(50) DEFAULT NULL COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',

    -- 扩展字段
    `category` VARCHAR(100) DEFAULT NULL COMMENT '分类（ai/machine-learning/funding/startups等）',
    `language` VARCHAR(10) DEFAULT 'en' COMMENT '语言（en，可能包含法语）',
    `tags` JSON DEFAULT NULL COMMENT 'RSS category标签列表（JSON数组）',

    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_url` (`url`),
    KEY `idx_source_id` (`source_id`),
    KEY `idx_published_at` (`published_at`),
    KEY `idx_crawled_at` (`crawled_at`),
    KEY `idx_source_published` (`source_id`, `published_at`),
    KEY `idx_external_id` (`external_id`),
    KEY `idx_category` (`category`),
    KEY `idx_region` (`region`),
    KEY `idx_ai_tag` (`ai_tag`),
    CONSTRAINT `fk_betakit_source_id` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='BetaKit加拿大科技新闻与创业生态消息表';

-- 2. 注册消息源到message_sources表
INSERT INTO `mp_message_sources` (
    `id`,
    `name`,
    `adapter_name`,
    `category`,
    `display_name`,
    `config`,
    `is_active`,
    `created_at`,
    `updated_at`
) VALUES (
    UUID(),
    'betakit',
    'betakit',
    'news',
    'BetaKit加拿大科技新闻',
    JSON_OBJECT(
        'mysql_table', 'mp_betakit_messages',
        'chroma_collection', 'betakit_tech_news',
        'collector_module', 'backend.sources.betakit.collector',
        'collector_class', 'BetaKitCollector',
        'interval', 86400,
        'region', '加拿大',
        'language', 'en',
        'feeds', JSON_ARRAY('ai', 'machine-learning', 'funding', 'startups'),
        'description', 'BetaKit是加拿大领先的科技创业新闻平台，专注报道加拿大AI、机器学习、创投融资和创业生态'
    ),
    1,
    NOW(),
    NOW()
) ON DUPLICATE KEY UPDATE
    `display_name` = VALUES(`display_name`),
    `config` = VALUES(`config`),
    `updated_at` = NOW();

-- 3. 验证注册结果
SELECT
    id,
    name,
    display_name,
    category,
    is_active,
    JSON_EXTRACT(config, '$.mysql_table') AS mysql_table,
    JSON_EXTRACT(config, '$.chroma_collection') AS chroma_collection,
    JSON_EXTRACT(config, '$.feeds') AS feeds
FROM mp_message_sources
WHERE name = 'betakit';

-- 4. 检查表是否创建成功
SHOW TABLES LIKE 'mp_betakit_messages';

-- 5. 查看表结构
SHOW CREATE TABLE mp_betakit_messages;
