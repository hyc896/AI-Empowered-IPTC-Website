-- OECD AI Policy Observatory 消息源注册脚本
-- 创建时间：2025-11-11

USE message_platform;

-- 1. 创建OECD AI消息表
CREATE TABLE IF NOT EXISTS mp_oecd_ai_messages (
    id VARCHAR(36) PRIMARY KEY COMMENT '消息ID（UUID）',
    source_id VARCHAR(36) NOT NULL COMMENT '来源ID',
    external_id VARCHAR(100) COMMENT '外部唯一标识（从URL路径提取）',
    title VARCHAR(500) NOT NULL COMMENT '文章标题',
    content TEXT NOT NULL COMMENT '文章正文内容',
    summary TEXT COMMENT '中文摘要（翻译后）',
    provider VARCHAR(500) COMMENT '作者列表（逗号分隔）',
    published_at DATETIME COMMENT '发布时间',
    crawled_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
    url VARCHAR(500) NOT NULL UNIQUE COMMENT '文章链接（用于去重）',

    region VARCHAR(50) DEFAULT 'GLOBAL' COMMENT '地区（GLOBAL）',
    category VARCHAR(100) COMMENT '文章分类（Academia/Civil society/Intergovernmental等）',
    language VARCHAR(10) DEFAULT 'en' COMMENT '语言（en）',
    metadata JSON COMMENT '其他元数据（JSON对象）',

    FOREIGN KEY (source_id) REFERENCES mp_message_sources(id) ON DELETE CASCADE,

    INDEX idx_source_id (source_id),
    INDEX idx_published_at (published_at),
    INDEX idx_crawled_at (crawled_at),
    INDEX idx_source_published (source_id, published_at),
    INDEX idx_url (url),
    INDEX idx_external_id (external_id),
    INDEX idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='OECD人工智能政策观察站博客表';

-- 2. 注册消息源到message_sources表
INSERT INTO mp_message_sources (
    id,
    name,
    adapter_name,
    category,
    display_name,
    config,
    schedule,
    is_active,
    last_crawled_at,
    created_at,
    updated_at
) VALUES (
    UUID(),
    'oecd_ai',
    'oecd_ai',
    'news',
    'OECD AI Policy Observatory',
    JSON_OBJECT(
        'url', 'https://oecd.ai/en/wonk',
        'mysql_table', 'mp_oecd_ai_messages',
        'chroma_collection', 'oecd_ai',
        'interval', 86400,
        'region', 'GLOBAL',
        'timezone', 'Europe/Paris',
        'language', 'en',
        'collector_module', 'backend.sources.oecd_ai.collector'
    ),
    '0 0 * * *',
    1,
    NULL,
    NOW(),
    NOW()
) ON DUPLICATE KEY UPDATE
    display_name = VALUES(display_name),
    config = VALUES(config),
    schedule = VALUES(schedule),
    updated_at = NOW();

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
WHERE name = 'oecd_ai';
