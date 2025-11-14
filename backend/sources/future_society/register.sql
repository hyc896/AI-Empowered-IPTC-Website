-- The Future Society 消息源注册脚本
-- 跨大西洋AI治理智库（美国+比利时）

-- 1. 创建消息表
CREATE TABLE IF NOT EXISTS mp_future_society_messages (
    id VARCHAR(36) PRIMARY KEY COMMENT '消息ID（UUID）',
    source_id VARCHAR(36) NOT NULL COMMENT '来源ID',
    external_id VARCHAR(200) COMMENT '外部唯一标识（从URL路径提取slug）',
    title VARCHAR(500) NOT NULL COMMENT '标题',
    content TEXT NOT NULL COMMENT '正文内容（从详情页提取完整内容）',
    summary TEXT COMMENT '中文摘要（翻译后）',
    provider VARCHAR(500) COMMENT '作者（多个用逗号分隔）',
    published_at DATETIME COMMENT '发布时间',
    crawled_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
    url VARCHAR(500) NOT NULL UNIQUE COMMENT '原文链接（用于去重）',
    region VARCHAR(50) DEFAULT 'GLOBAL' COMMENT '地区（US+BE，设为GLOBAL）',
    content_type VARCHAR(100) COMMENT '内容类型（Report/Policy Brief/Article等）',
    language VARCHAR(10) DEFAULT 'en' COMMENT '语言（en）',
    categories JSON COMMENT '分类标签（JSON数组，如AI Governance, EU AI Act等）',
    metadata JSON COMMENT '其他元数据（JSON对象，包括pdf_url等）',

    -- 外键约束
    CONSTRAINT fk_future_society_source FOREIGN KEY (source_id)
        REFERENCES mp_message_sources(id) ON DELETE CASCADE,

    -- 索引
    INDEX idx_source_id (source_id),
    INDEX idx_published_at (published_at),
    INDEX idx_crawled_at (crawled_at),
    INDEX idx_source_published (source_id, published_at),
    INDEX idx_url (url),
    INDEX idx_external_id (external_id),
    INDEX idx_content_type (content_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='The Future Society AI治理研究报告与政策简报表';

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
    'future_society',
    'future_society',
    'ai_governance',
    'The Future Society',
    JSON_OBJECT(
        'url', 'https://thefuturesociety.org/resources/',
        'mysql_table', 'mp_future_society_messages',
        'chroma_collection', 'future_society',
        'interval', 86400,
        'region', 'GLOBAL',
        'language', 'en',
        'description', '跨大西洋AI治理智库（美国+比利时），专注EU AI Act、全球AI治理、国家AI战略等研究',
        'collector_module', 'backend.sources.future_society.collector.FutureSocietyCollector'
    ),
    '0 2 * * *',
    1,
    NOW(),
    NOW()
) ON DUPLICATE KEY UPDATE
    display_name = VALUES(display_name),
    config = VALUES(config),
    updated_at = NOW();

-- 3. 验证安装
SELECT
    id,
    name,
    display_name,
    category,
    is_active,
    JSON_EXTRACT(config, '$.mysql_table') as mysql_table,
    JSON_EXTRACT(config, '$.chroma_collection') as chroma_collection
FROM mp_message_sources
WHERE name = 'future_society';
