-- Inteligencia Argentina AI分类消息源注册脚本
-- 阿根廷情报与分析网站AI专栏

-- 1. 创建消息表
CREATE TABLE IF NOT EXISTS `mp_inteligencia_argentina_messages` (
    `id` VARCHAR(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '消息ID（UUID）',
    `source_id` VARCHAR(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '来源ID',
    `external_id` VARCHAR(200) DEFAULT NULL COMMENT '外部唯一标识（从URL提取slug）',
    `title` VARCHAR(500) NOT NULL COMMENT '标题',
    `content` TEXT NOT NULL COMMENT '正文内容（从详情页提取的完整文章）',
    `summary` TEXT DEFAULT NULL COMMENT '中文摘要（翻译后）',
    `provider` VARCHAR(500) DEFAULT NULL COMMENT '作者',
    `published_at` DATETIME DEFAULT NULL COMMENT '发布时间',
    `crawled_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
    `url` VARCHAR(500) NOT NULL COMMENT '原文链接（用于去重）',
    `region` VARCHAR(200) DEFAULT NULL COMMENT '地区（中文格式，如阿根廷、阿根廷/布宜诺斯艾利斯、全球等）',
    `industry_tags` TEXT DEFAULT NULL COMMENT '行业标签（逗号分隔，最多3个，涉及AI必须包含人工智能标签）',
    `ai_tag` VARCHAR(50) DEFAULT NULL COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',
    `category` VARCHAR(100) DEFAULT 'inteligencia-artificial' COMMENT '文章分类（固定为AI类）',
    `language` VARCHAR(10) DEFAULT 'es' COMMENT '语言（西班牙语）',
    `excerpt` TEXT DEFAULT NULL COMMENT '摘要（从列表页提取的excerpt）',
    `tags` JSON DEFAULT NULL COMMENT '标签列表（JSON数组）',
    `metadata` JSON DEFAULT NULL COMMENT '其他元数据（JSON对象）',
    PRIMARY KEY (`id`),
    UNIQUE KEY `url` (`url`),
    KEY `idx_source_id` (`source_id`),
    KEY `idx_published_at` (`published_at`),
    KEY `idx_crawled_at` (`crawled_at`),
    KEY `idx_source_published` (`source_id`, `published_at`),
    KEY `idx_url` (`url`),
    KEY `idx_external_id` (`external_id`),
    KEY `idx_region` (`region`),
    KEY `idx_ai_tag` (`ai_tag`),
    CONSTRAINT `fk_inteligencia_argentina_source` FOREIGN KEY (`source_id`)
        REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Inteligencia Argentina AI分类消息表';

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
    'Inteligencia Argentina AI',
    'inteligencia_argentina',
    'news',
    'Inteligencia Argentina AI分类',
    JSON_OBJECT(
        'mysql_table', 'mp_inteligencia_argentina_messages',
        'chroma_collection', 'inteligencia_argentina_ai',
        'collector_module', 'backend.sources.inteligencia_argentina.collector',
        'interval', 3600,
        'region', '阿根廷',
        'language', 'es',
        'url', 'https://inteligenciaargentina.ar/categoria/inteligencia-artificial'
    ),
    '0 */2 * * *',
    1,
    NOW(),
    NOW()
);

-- 3. 验证注册
SELECT
    id,
    name,
    adapter_name,
    category,
    is_active,
    JSON_EXTRACT(config, '$.mysql_table') AS mysql_table,
    JSON_EXTRACT(config, '$.chroma_collection') AS chroma_collection,
    JSON_EXTRACT(config, '$.collector_module') AS collector_module
FROM mp_message_sources
WHERE name = 'Inteligencia Argentina AI';
