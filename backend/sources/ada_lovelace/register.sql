-- Ada Lovelace Institute 消息源注册脚本

-- 1. 创建消息表
CREATE TABLE IF NOT EXISTS `mp_ada_lovelace_messages` (
    `id` VARCHAR(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '消息ID（UUID）',
    `source_id` VARCHAR(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '来源ID',
    `external_id` VARCHAR(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '外部唯一标识（从URL路径提取slug）',
    `title` VARCHAR(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '标题',
    `content` TEXT COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '正文内容（从详情页提取完整文章）',
    `summary` TEXT COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '中文摘要（翻译后）',
    `provider` VARCHAR(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '作者（多个用逗号分隔）',
    `published_at` DATETIME DEFAULT NULL COMMENT '发布时间',
    `crawled_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
    `url` VARCHAR(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '原文链接（用于去重）',
    `region` VARCHAR(50) COLLATE utf8mb4_unicode_ci DEFAULT 'UK' COMMENT '地区（UK=United Kingdom 英国）',
    `category` VARCHAR(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '内容类型（Commentary/Report/Blog Post等）',
    `language` VARCHAR(10) COLLATE utf8mb4_unicode_ci DEFAULT 'en' COMMENT '语言（en）',
    `tags` JSON DEFAULT NULL COMMENT '标签列表（如AI policy、Data governance等）',
    `reading_time` INT DEFAULT NULL COMMENT '预计阅读时间（分钟）',
    `metadata` JSON DEFAULT NULL COMMENT '其他元数据（JSON对象）',
    PRIMARY KEY (`id`),
    UNIQUE KEY `idx_url` (`url`),
    KEY `idx_source_id` (`source_id`),
    KEY `idx_published_at` (`published_at`),
    KEY `idx_crawled_at` (`crawled_at`),
    KEY `idx_source_published` (`source_id`, `published_at`),
    KEY `idx_external_id` (`external_id`),
    KEY `idx_category` (`category`),
    CONSTRAINT `fk_ada_lovelace_source` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Ada Lovelace Institute博客文章表';

-- 2. 注册消息源
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
    'ada_lovelace',
    'ada_lovelace',
    'news',
    'Ada Lovelace Institute',
    JSON_OBJECT(
        'url', 'https://www.adalovelaceinstitute.org/blog/',
        'mysql_table', 'mp_ada_lovelace_messages',
        'chroma_collection', 'ada_lovelace',
        'region', 'UK',
        'language', 'en',
        'collector_module', 'backend.sources.ada_lovelace.collector',
        'collector_class', 'AdaLovelaceCollector'
    ),
    '0 0 * * *',
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
    JSON_EXTRACT(config, '$.mysql_table') AS mysql_table,
    JSON_EXTRACT(config, '$.chroma_collection') AS chroma_collection,
    created_at
FROM mp_message_sources
WHERE name = 'ada_lovelace';
