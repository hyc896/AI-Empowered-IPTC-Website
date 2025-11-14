-- ============================================================
-- Safe AI Forum (SAIF) 消息源注册脚本
-- 英国AI安全论坛 - 研究报告与政策指南
-- ============================================================

-- 创建消息表
CREATE TABLE IF NOT EXISTS `mp_saif_messages` (
    `id` VARCHAR(36) NOT NULL COMMENT '消息ID（UUID）',
    `source_id` VARCHAR(36) NOT NULL COMMENT '来源ID',
    `external_id` VARCHAR(200) DEFAULT NULL COMMENT '外部唯一标识（从URL路径提取slug）',
    `title` VARCHAR(500) NOT NULL COMMENT '标题',
    `content` TEXT NOT NULL COMMENT '正文内容（摘要或完整内容）',
    `summary` TEXT DEFAULT NULL COMMENT '中文摘要（翻译后）',
    `provider` VARCHAR(500) DEFAULT NULL COMMENT '作者（多个用逗号分隔）',
    `published_at` DATETIME DEFAULT NULL COMMENT '发布时间',
    `crawled_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
    `url` VARCHAR(500) NOT NULL COMMENT '原文链接（用于去重）',
    `region` VARCHAR(50) DEFAULT 'UK' COMMENT '地区（UK=United Kingdom 英国）',
    `content_type` VARCHAR(100) DEFAULT NULL COMMENT '内容类型（Research/Policy Guide/Primer/Report等）',
    `language` VARCHAR(10) DEFAULT 'en' COMMENT '语言（en/zh=中英双语出版物）',
    `pdf_url` VARCHAR(500) DEFAULT NULL COMMENT 'PDF下载链接',
    `updated_at` DATETIME DEFAULT NULL COMMENT '文章更新时间',
    `metadata` JSON DEFAULT NULL COMMENT '其他元数据（JSON对象）',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_url` (`url`),
    KEY `idx_source_id` (`source_id`),
    KEY `idx_published_at` (`published_at`),
    KEY `idx_crawled_at` (`crawled_at`),
    KEY `idx_source_published` (`source_id`, `published_at`),
    KEY `idx_external_id` (`external_id`),
    KEY `idx_content_type` (`content_type`),
    CONSTRAINT `fk_saif_source` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Safe AI Forum研究报告表';

-- 注册消息源
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
    'saif',
    'saif',
    'research',
    'Safe AI Forum (UK)',
    JSON_OBJECT(
        'url', 'https://saif.org/research/',
        'mysql_table', 'mp_saif_messages',
        'chroma_collection', 'saif',
        'interval', 86400,
        'region', 'UK',
        'language', 'en',
        'collector_module', 'backend.sources.saif.collector.SAIFCollector'
    ),
    '0 2 * * *',
    1,
    NOW(),
    NOW()
) ON DUPLICATE KEY UPDATE
    `display_name` = VALUES(`display_name`),
    `config` = VALUES(`config`),
    `schedule` = VALUES(`schedule`),
    `is_active` = VALUES(`is_active`),
    `updated_at` = NOW();

-- 验证注册结果
SELECT
    id,
    name,
    display_name,
    category,
    is_active,
    JSON_EXTRACT(config, '$.mysql_table') as mysql_table,
    JSON_EXTRACT(config, '$.chroma_collection') as chroma_collection,
    JSON_EXTRACT(config, '$.url') as url
FROM mp_message_sources
WHERE name = 'saif';
