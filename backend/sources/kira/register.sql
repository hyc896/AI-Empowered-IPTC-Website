-- ========================================
-- KIRA Center 消息源注册脚本
-- ========================================

-- 1. 创建消息表
CREATE TABLE IF NOT EXISTS mp_kira_messages (
    id VARCHAR(36) COLLATE utf8mb4_unicode_ci PRIMARY KEY COMMENT '消息ID（UUID）',
    source_id VARCHAR(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '来源ID',
    external_id VARCHAR(200) COLLATE utf8mb4_unicode_ci COMMENT '外部唯一标识（从URL路径提取slug）',
    title VARCHAR(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '标题',
    content TEXT COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '正文内容（从详情页提取完整内容）',
    summary TEXT COLLATE utf8mb4_unicode_ci COMMENT '中文摘要（翻译后）',
    provider VARCHAR(500) COLLATE utf8mb4_unicode_ci COMMENT '作者（多个用逗号分隔）',
    published_at DATETIME COMMENT '发布时间',
    crawled_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
    url VARCHAR(500) COLLATE utf8mb4_unicode_ci NOT NULL UNIQUE COMMENT '原文链接（用于去重）',

    region VARCHAR(50) COLLATE utf8mb4_unicode_ci DEFAULT 'DE' COMMENT '地区（DE=Germany 德国）',
    content_type VARCHAR(100) COLLATE utf8mb4_unicode_ci COMMENT '内容类型（Blog/Report/Policy Analysis）',
    language VARCHAR(10) COLLATE utf8mb4_unicode_ci DEFAULT 'en' COMMENT '语言（en/de）',
    pdf_url VARCHAR(500) COLLATE utf8mb4_unicode_ci COMMENT 'PDF报告下载链接',
    metadata JSON COMMENT '其他元数据（JSON对象）',

    FOREIGN KEY (source_id) REFERENCES mp_message_sources(id) ON DELETE CASCADE,

    INDEX idx_source_id (source_id),
    INDEX idx_published_at (published_at),
    INDEX idx_crawled_at (crawled_at),
    INDEX idx_source_published (source_id, published_at),
    INDEX idx_url (url),
    INDEX idx_external_id (external_id),
    INDEX idx_content_type (content_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='KIRA Center（德国AI风险与影响研究中心）博客与报告表';

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
    'kira',
    'kira',
    'think_tank',
    'KIRA Center',
    JSON_OBJECT(
        'url', 'https://kira.eu/blog',
        'region', 'DE',
        'language', 'en',
        'mysql_table', 'mp_kira_messages',
        'chroma_collection', 'kira',
        'interval', 86400,
        'collector_module', 'backend.sources.kira.collector.KIRACollector'
    ),
    '0 2 * * *',
    1,
    NOW(),
    NOW()
) ON DUPLICATE KEY UPDATE
    display_name = VALUES(display_name),
    config = VALUES(config),
    updated_at = NOW();

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
WHERE name = 'kira';

-- 4. 验证表结构
SHOW CREATE TABLE mp_kira_messages;
