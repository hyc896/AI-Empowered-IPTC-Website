-- ============================================================
-- CSIS AI Topic（战略与国际研究中心-AI主题）消息源注册脚本
-- ============================================================

-- 创建消息表
CREATE TABLE IF NOT EXISTS mp_csis_messages (
    id VARCHAR(36) COLLATE utf8mb4_unicode_ci PRIMARY KEY COMMENT '消息ID（UUID）',
    source_id VARCHAR(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '来源ID',
    external_id VARCHAR(100) COMMENT '外部唯一标识（从URL路径提取）',
    title VARCHAR(500) NOT NULL COMMENT '文章标题',
    content TEXT NOT NULL COMMENT '文章正文内容',
    summary TEXT COMMENT '中文摘要（翻译后）',
    provider VARCHAR(500) COMMENT '作者列表（逗号分隔）',
    published_at DATETIME COMMENT '发布时间',
    crawled_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
    url VARCHAR(500) NOT NULL UNIQUE COMMENT '文章链接（用于去重）',
    region VARCHAR(50) DEFAULT 'US' COMMENT '地区（US）',
    category VARCHAR(100) COMMENT '内容类型（Event/Commentary/Report/Podcast Episode等）',
    language VARCHAR(10) DEFAULT 'en' COMMENT '语言（en）',
    metadata JSON COMMENT '其他元数据（JSON对象）',

    INDEX idx_source_id (source_id),
    INDEX idx_published_at (published_at),
    INDEX idx_crawled_at (crawled_at),
    INDEX idx_source_published (source_id, published_at),
    INDEX idx_url (url),
    INDEX idx_external_id (external_id),
    INDEX idx_category (category),

    FOREIGN KEY (source_id) REFERENCES mp_message_sources(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='CSIS AI Topic文章表';

-- 插入消息源配置
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
    'csis',
    'CSISCollector',
    'news',
    'CSIS AI Topic',
    JSON_OBJECT(
        'url', 'https://www.csis.org/topics/artificial-intelligence',
        'mysql_table', 'mp_csis_messages',
        'chroma_collection', 'csis',
        'collector_module', 'backend.sources.csis.collector',
        'region', 'US',
        'timezone', 'America/New_York',
        'language', 'en',
        'interval', 86400
    ),
    '0 0 * * *',
    1,
    NOW(),
    NOW()
) ON DUPLICATE KEY UPDATE
    adapter_name = VALUES(adapter_name),
    category = VALUES(category),
    display_name = VALUES(display_name),
    config = VALUES(config),
    schedule = VALUES(schedule),
    updated_at = NOW();

-- 验证注册结果
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
WHERE name = 'csis';
