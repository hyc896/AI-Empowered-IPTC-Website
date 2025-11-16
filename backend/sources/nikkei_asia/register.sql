-- Nikkei Asia AI板块消息源注册SQL
-- 使用方式：在MySQL中执行此脚本

-- 1. 创建消息表
CREATE TABLE IF NOT EXISTS mp_nikkei_asia_ai_messages (
    id VARCHAR(36) PRIMARY KEY COMMENT '消息ID（UUID）',
    source_id VARCHAR(36) NOT NULL COMMENT '来源ID',
    external_id VARCHAR(200) COMMENT '外部唯一标识（文章ID或slug）',
    title VARCHAR(500) NOT NULL COMMENT '标题',
    content TEXT NOT NULL COMMENT '正文内容（subhead描述）',
    summary TEXT COMMENT '中文摘要（翻译后）',
    provider VARCHAR(500) COMMENT '作者',
    published_at DATETIME COMMENT '发布时间',
    crawled_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
    url VARCHAR(500) NOT NULL UNIQUE COMMENT '原文链接（用于去重）',
    region VARCHAR(50) DEFAULT 'JP' COMMENT '地区（JP=Japan 日本）',
    category VARCHAR(100) COMMENT '分类（Artificial Intelligence）',
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Nikkei Asia AI板块（日经亚洲人工智能新闻）消息表';

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
    'nikkei_asia_ai',
    'nikkei_asia',
    'news',
    'Nikkei Asia AI',
    JSON_OBJECT(
        'mysql_table', 'mp_nikkei_asia_ai_messages',
        'chroma_collection', 'nikkei_asia_ai',
        'collector_module', 'backend.sources.nikkei_asia',
        'url', 'https://asia.nikkei.com/Business/Technology/Artificial-intelligence',
        'interval', 3600,
        'source_type', 'news'
    ),
    '0 */1 * * *',
    TRUE,
    NOW(),
    NOW()
);

-- 查询验证
SELECT
    id,
    name,
    display_name,
    category,
    JSON_EXTRACT(config, '$.mysql_table') as mysql_table,
    JSON_EXTRACT(config, '$.chroma_collection') as chroma_collection,
    JSON_EXTRACT(config, '$.interval') as `interval`,
    is_active
FROM mp_message_sources
WHERE name = 'nikkei_asia_ai';
