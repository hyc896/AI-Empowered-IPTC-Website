-- AISI (AI Security Institute) 消息源注册SQL脚本
-- 英国政府AI安全研究机构

-- 1. 创建消息表
CREATE TABLE IF NOT EXISTS mp_aisi_messages (
    id VARCHAR(36) COLLATE utf8mb4_unicode_ci PRIMARY KEY COMMENT '消息ID（UUID）',
    source_id VARCHAR(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '来源ID',
    external_id VARCHAR(200) COMMENT '外部唯一标识（从URL路径提取slug）',
    title VARCHAR(500) NOT NULL COMMENT '标题',
    content TEXT NOT NULL COMMENT '正文内容（从详情页提取完整内容）',
    summary TEXT COMMENT '中文摘要（翻译后）',
    provider VARCHAR(500) COMMENT '作者（多个用逗号分隔）',
    published_at DATETIME COMMENT '发布时间',
    crawled_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
    url VARCHAR(500) NOT NULL UNIQUE COMMENT '原文链接（用于去重）',
    region VARCHAR(50) DEFAULT 'UK' COMMENT '地区（UK=United Kingdom 英国）',
    content_type VARCHAR(100) COMMENT '内容类型（Research/Blog/Technical Report）',
    language VARCHAR(10) DEFAULT 'en' COMMENT '语言（en）',
    categories JSON COMMENT '分类标签（JSON数组，如Safeguards, Control, Alignment等）',
    metadata JSON COMMENT '其他元数据（JSON对象）',

    CONSTRAINT fk_aisi_source FOREIGN KEY (source_id)
        REFERENCES mp_message_sources(id) ON DELETE CASCADE,

    INDEX idx_source_id (source_id),
    INDEX idx_published_at (published_at),
    INDEX idx_crawled_at (crawled_at),
    INDEX idx_source_published (source_id, published_at),
    INDEX idx_url (url),
    INDEX idx_external_id (external_id),
    INDEX idx_content_type (content_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='AI Security Institute（英国政府AI安全研究机构）研究与博客表';

-- 2. 注册消息源
INSERT INTO mp_message_sources (
    id,
    name,
    adapter_name,
    category,
    display_name,
    config,
    schedule,
    is_active,
    created_at,
    updated_at
) VALUES (
    UUID(),
    'aisi',
    'aisi',
    'think_tank',
    'AI Security Institute (AISI)',
    JSON_OBJECT(
        'url', 'https://www.aisi.gov.uk/research',
        'region', 'UK',
        'language', 'en',
        'interval', 86400,
        'mysql_table', 'mp_aisi_messages',
        'chroma_collection', 'aisi_research',
        'collector_module', 'backend.sources.aisi.collector.AISICollector'
    ),
    '0 2 * * *',
    1,
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
    JSON_EXTRACT(config, '$.mysql_table') as mysql_table,
    JSON_EXTRACT(config, '$.chroma_collection') as chroma_collection
FROM mp_message_sources
WHERE name = 'aisi';
