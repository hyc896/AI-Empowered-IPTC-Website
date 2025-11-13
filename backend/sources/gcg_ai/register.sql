-- ======================================================================
-- Global Center on AI Governance (GCG) 消息源注册脚本
-- 南非/非洲AI治理研究中心
-- ======================================================================

-- 创建消息表
CREATE TABLE IF NOT EXISTS mp_gcg_ai_messages (
    id VARCHAR(36) PRIMARY KEY COMMENT '消息ID（UUID）',
    source_id VARCHAR(36) NOT NULL COMMENT '来源ID',
    external_id VARCHAR(200) COMMENT '外部唯一标识（从URL路径提取slug）',
    title VARCHAR(500) NOT NULL COMMENT '标题',
    content TEXT NOT NULL COMMENT '正文内容（从详情页提取的简介）',
    summary TEXT COMMENT '中文摘要（翻译后）',
    provider VARCHAR(500) COMMENT '作者（多个用逗号分隔）',
    published_at DATETIME COMMENT '发布时间',
    crawled_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
    url VARCHAR(500) NOT NULL UNIQUE COMMENT '原文链接（用于去重）',
    region VARCHAR(50) DEFAULT 'ZA' COMMENT '地区（ZA=South Africa/Africa 南非/非洲）',
    category VARCHAR(100) COMMENT '出版物类型（Policy Brief/Report/Article/Analysis/Toolkit等）',
    language VARCHAR(10) DEFAULT 'en' COMMENT '语言（en）',
    tags JSON COMMENT '标签列表（如Technology、Public Policy等）',
    pdf_url VARCHAR(500) COMMENT 'PDF下载链接（如果有）',
    metadata JSON COMMENT '其他元数据（JSON对象）',

    CONSTRAINT fk_gcg_ai_source FOREIGN KEY (source_id)
        REFERENCES mp_message_sources(id) ON DELETE CASCADE,

    INDEX idx_source_id (source_id),
    INDEX idx_published_at (published_at),
    INDEX idx_crawled_at (crawled_at),
    INDEX idx_source_published (source_id, published_at),
    INDEX idx_url (url),
    INDEX idx_external_id (external_id),
    INDEX idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='GCG AI治理研究中心文章表';

-- 注册消息源
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
    'gcg_ai',
    'gcg_ai',
    'research',
    'Global Center on AI Governance (GCG)',
    JSON_OBJECT(
        'url', 'https://www.globalcenter.ai/research',
        'mysql_table', 'mp_gcg_ai_messages',
        'chroma_collection', 'gcg_ai_research',
        'interval', 604800,
        'region', 'ZA',
        'language', 'en',
        'collector_module', 'backend.sources.gcg_ai.collector',
        'collector_class', 'GCGAICollector'
    ),
    '0 0 * * 0',
    1,
    NULL,
    NOW(),
    NOW()
) ON DUPLICATE KEY UPDATE
    display_name = VALUES(display_name),
    config = VALUES(config),
    updated_at = NOW();

-- 验证注册结果
SELECT
    id,
    name,
    display_name,
    category,
    is_active,
    JSON_EXTRACT(config, '$.mysql_table') as mysql_table,
    JSON_EXTRACT(config, '$.chroma_collection') as chroma_collection
FROM mp_message_sources
WHERE name = 'gcg_ai';

-- 验证表创建
SHOW CREATE TABLE mp_gcg_ai_messages;
