-- Tech in Asia消息源注册脚本

-- 1. 创建消息表
CREATE TABLE IF NOT EXISTS mp_techinasia_messages (
    id VARCHAR(36) PRIMARY KEY COMMENT '消息ID（UUID）',
    source_id VARCHAR(36) NOT NULL COMMENT '来源ID',
    external_id VARCHAR(200) COMMENT '外部唯一标识（从URL slug提取）',
    title VARCHAR(500) NOT NULL COMMENT '标题',
    content TEXT NOT NULL COMMENT '正文内容（从详情页提取完整文章）',
    summary TEXT COMMENT '摘要（RSS description翻译为中文）',
    provider VARCHAR(500) COMMENT '作者（多个用逗号分隔）',
    published_at DATETIME COMMENT '发布时间',
    crawled_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
    url VARCHAR(500) NOT NULL UNIQUE COMMENT '原文链接（用于去重）',

    region VARCHAR(200) COMMENT '地区（中文格式，如''新加坡''、''印度尼西亚''、''全球''等）',
    industry_tags TEXT COMMENT '行业标签（逗号分隔，最多3个）',
    ai_tag VARCHAR(50) COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',

    category VARCHAR(100) COMMENT '分类（AI/Investments/Startups/Fintech等）',
    language VARCHAR(10) DEFAULT 'en' COMMENT '语言（en）',
    metadata JSON COMMENT '其他元数据（JSON对象）',

    FOREIGN KEY (source_id) REFERENCES mp_message_sources(id) ON DELETE CASCADE,

    INDEX idx_source_id (source_id),
    INDEX idx_published_at (published_at),
    INDEX idx_crawled_at (crawled_at),
    INDEX idx_source_published (source_id, published_at),
    INDEX idx_url (url),
    INDEX idx_external_id (external_id),
    INDEX idx_category (category),
    INDEX idx_region (region)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Tech in Asia科技新闻（东南亚科技创投新闻）';

-- 2. 注册消息源
INSERT INTO mp_message_sources (
    id,
    name,
    display_name,
    adapter_name,
    category,
    is_active,
    config,
    created_at,
    updated_at
) VALUES (
    UUID(),
    'techinasia',
    'Tech in Asia',
    'techinasia',
    'news',
    1,
    JSON_OBJECT(
        'collector_module', 'backend.sources.techinasia.collector',
        'collector_class', 'TechInAsiaCollector',
        'interval', 3600,
        'mysql_table', 'mp_techinasia_messages',
        'chroma_collection', 'techinasia',
        'region', 'Southeast Asia',
        'language', 'en',
        'rss_url', 'https://feeds.feedburner.com/techinasia'
    ),
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
    adapter_name,
    category,
    is_active,
    JSON_EXTRACT(config, '$.mysql_table') AS mysql_table,
    JSON_EXTRACT(config, '$.chroma_collection') AS chroma_collection,
    JSON_EXTRACT(config, '$.interval') AS interval_seconds
FROM mp_message_sources
WHERE name = 'techinasia';
