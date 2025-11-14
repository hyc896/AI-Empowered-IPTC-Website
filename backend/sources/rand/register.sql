-- RAND Corporation - Artificial Intelligence 消息源注册SQL
-- 兰德公司人工智能研究消息源

-- ============================================================
-- 1. 创建消息表
-- ============================================================

CREATE TABLE IF NOT EXISTS `mp_rand_messages` (
    `id` varchar(36) NOT NULL COMMENT '消息ID（UUID）',
    `source_id` varchar(36) NOT NULL COMMENT '来源ID',
    `external_id` varchar(100) DEFAULT NULL COMMENT '外部唯一标识（RAND content-id，如RRA4180-1）',
    `title` varchar(500) NOT NULL COMMENT '文章标题',
    `content` text NOT NULL COMMENT '文章正文内容',
    `summary` text DEFAULT NULL COMMENT '中文摘要（翻译后）',
    `provider` varchar(500) DEFAULT NULL COMMENT '作者列表（逗号分隔）',
    `published_at` datetime DEFAULT NULL COMMENT '发布时间',
    `crawled_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
    `url` varchar(500) NOT NULL COMMENT '文章链接（用于去重）',
    `region` varchar(50) DEFAULT 'US' COMMENT '地区（US）',
    `category` varchar(100) DEFAULT NULL COMMENT '出版类型（RESEARCH/COMMENTARY/DATA VIZ等）',
    `language` varchar(10) DEFAULT 'en' COMMENT '语言（en）',
    `metadata` json DEFAULT NULL COMMENT '其他元数据（JSON对象）',

    PRIMARY KEY (`id`),
    UNIQUE KEY `idx_url` (`url`),
    KEY `idx_source_id` (`source_id`),
    KEY `idx_published_at` (`published_at`),
    KEY `idx_crawled_at` (`crawled_at`),
    KEY `idx_source_published` (`source_id`, `published_at`),
    KEY `idx_external_id` (`external_id`),
    KEY `idx_category` (`category`),

    CONSTRAINT `fk_rand_messages_source_id`
        FOREIGN KEY (`source_id`)
        REFERENCES `mp_message_sources` (`id`)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='RAND Corporation - Artificial Intelligence 消息表';


-- ============================================================
-- 2. 注册消息源
-- ============================================================

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
    'rand_ai',
    'rand',
    'think_tank',
    'RAND Corporation - Artificial Intelligence',
    JSON_OBJECT(
        'url', 'https://www.rand.org/topics/featured/artificial-intelligence.html',
        'mysql_table', 'mp_rand_messages',
        'chroma_collection', 'rand_ai',
        'collector_module', 'backend.sources.rand.collector',
        'region', 'US',
        'timezone', 'America/Los_Angeles',
        'language', 'en'
    ),
    '0 0 */12 * * *',
    1,
    NOW(),
    NOW()
) ON DUPLICATE KEY UPDATE
    `display_name` = VALUES(`display_name`),
    `config` = VALUES(`config`),
    `schedule` = VALUES(`schedule`),
    `is_active` = VALUES(`is_active`),
    `updated_at` = NOW();


-- ============================================================
-- 3. 验证注册结果
-- ============================================================

SELECT
    id,
    name,
    display_name,
    category,
    is_active,
    JSON_EXTRACT(config, '$.url') AS url,
    JSON_EXTRACT(config, '$.mysql_table') AS mysql_table,
    JSON_EXTRACT(config, '$.chroma_collection') AS chroma_collection,
    schedule,
    created_at
FROM mp_message_sources
WHERE name = 'rand_ai';
