-- ========================================
-- 斯坦陵布什大学政策创新实验室消息源注册脚本
-- Policy Innovation Lab, Stellenbosch University
-- ========================================

-- 1. 创建消息表
CREATE TABLE IF NOT EXISTS `mp_stellenbosch_messages` (
    -- 核心必备字段
    `id` VARCHAR(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '消息ID（UUID）',
    `source_id` VARCHAR(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '来源ID',
    `external_id` VARCHAR(200) DEFAULT NULL COMMENT '外部唯一标识（从URL路径提取slug）',
    `title` VARCHAR(500) NOT NULL COMMENT '标题',
    `content` TEXT NOT NULL COMMENT '正文内容（从详情页提取）',
    `summary` TEXT DEFAULT NULL COMMENT '中文摘要（翻译后）',
    `provider` VARCHAR(500) DEFAULT NULL COMMENT '作者（From JSON-LD schema）',
    `published_at` DATETIME DEFAULT NULL COMMENT '发布时间',
    `crawled_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
    `url` VARCHAR(500) NOT NULL COMMENT '原文链接（用于去重）',

    -- 扩展字段
    `region` VARCHAR(50) DEFAULT 'ZA' COMMENT '地区（ZA=South Africa 南非）',
    `category` VARCHAR(100) DEFAULT NULL COMMENT '分类（从articleSection提取）',
    `language` VARCHAR(10) DEFAULT 'en' COMMENT '语言（en）',
    `word_count` INT DEFAULT NULL COMMENT '字数统计（从JSON-LD schema提取）',
    `metadata` JSON DEFAULT NULL COMMENT '其他元数据（JSON对象）',

    -- 主键和索引
    PRIMARY KEY (`id`),
    UNIQUE KEY `idx_url` (`url`),
    KEY `idx_source_id` (`source_id`),
    KEY `idx_published_at` (`published_at`),
    KEY `idx_crawled_at` (`crawled_at`),
    KEY `idx_source_published` (`source_id`, `published_at`),
    KEY `idx_external_id` (`external_id`),
    KEY `idx_category` (`category`),

    -- 外键约束
    CONSTRAINT `fk_stellenbosch_source`
        FOREIGN KEY (`source_id`)
        REFERENCES `mp_message_sources` (`id`)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='斯坦陵布什大学政策创新实验室新闻文章表';

-- 2. 注册消息源配置
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
    'stellenbosch_policy_lab',
    'stellenbosch',
    'news',
    '斯坦陵布什大学政策创新实验室',
    JSON_OBJECT(
        'url', 'https://policyinnovationlab.sun.ac.za/news/',
        'mysql_table', 'mp_stellenbosch_messages',
        'chroma_collection', 'stellenbosch_policy_lab',
        'interval', 86400,
        'region', 'ZA',
        'language', 'en',
        'collector_module', 'backend.sources.stellenbosch.collector.StellenboschCollector'
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

-- 3. 验证注册
SELECT
    id,
    name,
    display_name,
    category,
    is_active,
    JSON_EXTRACT(config, '$.mysql_table') AS mysql_table,
    JSON_EXTRACT(config, '$.chroma_collection') AS chroma_collection,
    JSON_EXTRACT(config, '$.url') AS url,
    schedule
FROM mp_message_sources
WHERE name = 'stellenbosch_policy_lab';

-- 4. 检查表是否创建成功
SHOW TABLES LIKE 'mp_stellenbosch_messages';

-- 5. 查看表结构
SHOW CREATE TABLE mp_stellenbosch_messages;
