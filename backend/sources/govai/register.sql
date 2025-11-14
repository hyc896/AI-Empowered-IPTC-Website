-- GovAI (Centre for the Governance of AI) 消息源注册脚本
-- 人工智能治理中心研究论文采集器

-- 1. 创建GovAI消息表
CREATE TABLE IF NOT EXISTS `mp_govai_messages` (
    `id` VARCHAR(36) NOT NULL COMMENT '消息ID（UUID）',
    `source_id` VARCHAR(36) NOT NULL COMMENT '来源ID',
    `external_id` VARCHAR(100) DEFAULT NULL COMMENT '外部唯一标识（从URL路径提取）',
    `title` VARCHAR(500) NOT NULL COMMENT '论文标题',
    `content` TEXT NOT NULL COMMENT '论文摘要/正文内容',
    `summary` TEXT DEFAULT NULL COMMENT '中文摘要（翻译后）',
    `provider` VARCHAR(500) DEFAULT NULL COMMENT '作者列表（逗号分隔）',
    `published_at` DATETIME DEFAULT NULL COMMENT '发布时间',
    `crawled_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
    `url` VARCHAR(500) NOT NULL COMMENT '论文链接（用于去重）',
    `region` VARCHAR(50) DEFAULT 'GLOBAL' COMMENT '地区（GLOBAL）',
    `category` VARCHAR(100) DEFAULT NULL COMMENT '研究分类（Survey Research/Technical AI Governance等）',
    `language` VARCHAR(10) DEFAULT 'en' COMMENT '语言（en）',
    `metadata` JSON DEFAULT NULL COMMENT '其他元数据（JSON对象）',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_url` (`url`),
    KEY `idx_source_id` (`source_id`),
    KEY `idx_published_at` (`published_at`),
    KEY `idx_crawled_at` (`crawled_at`),
    KEY `idx_source_published` (`source_id`, `published_at`),
    KEY `idx_external_id` (`external_id`),
    KEY `idx_category` (`category`),
    CONSTRAINT `fk_govai_source` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='GovAI研究论文表';

-- 2. 注册GovAI消息源
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
    'govai',
    'govai',
    'news',
    'Centre for the Governance of AI',
    JSON_OBJECT(
        'url', 'https://www.governance.ai/research',
        'mysql_table', 'mp_govai_messages',
        'chroma_collection', 'govai_research',
        'collector_module', 'backend.sources.govai.collector',
        'collector_class', 'GovAICollector',
        'interval', 86400,
        'region', 'GLOBAL',
        'language', 'en',
        'timezone', 'UTC'
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

-- 3. 验证注册结果
SELECT
    id,
    name,
    display_name,
    category,
    is_active,
    JSON_EXTRACT(config, '$.mysql_table') AS mysql_table,
    JSON_EXTRACT(config, '$.chroma_collection') AS chroma_collection
FROM mp_message_sources
WHERE name = 'govai';
