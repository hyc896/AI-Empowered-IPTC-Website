-- ===================================================================
-- Investing.com General News 消息源注册脚本
-- ===================================================================

-- 1. 创建消息表
CREATE TABLE IF NOT EXISTS mp_investing_com_messages (
    id VARCHAR(36) COLLATE utf8mb4_unicode_ci PRIMARY KEY COMMENT '消息ID（UUID）',
    source_id VARCHAR(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '来源ID',
    external_id VARCHAR(200) COMMENT '外部唯一标识（RSS guid）',
    title VARCHAR(500) NOT NULL COMMENT '标题',
    content TEXT NOT NULL COMMENT '正文内容（description）',
    summary TEXT COMMENT '摘要（同content）',
    provider VARCHAR(500) COMMENT '信息提供方（固定为Investing.com）',
    published_at DATETIME COMMENT '发布时间（pubDate）',
    crawled_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
    url VARCHAR(500) NOT NULL UNIQUE COMMENT '原文链接（用于去重）',

    -- 新增必备字段（2025年强制要求）
    region VARCHAR(200) COMMENT '地区（中文格式，如"美国"、"全球"等）',
    industry_tags TEXT COMMENT '行业标签（逗号分隔，最多3个）',
    ai_tag VARCHAR(50) COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',

    -- 扩展字段
    category VARCHAR(100) COMMENT '分类（General News）',
    language VARCHAR(10) DEFAULT 'en' COMMENT '语言（en）',
    metadata JSON COMMENT '其他元数据（JSON对象）',

    -- 外键
    FOREIGN KEY (source_id) REFERENCES mp_message_sources(id) ON DELETE CASCADE,

    -- 索引
    INDEX idx_source_id (source_id),
    INDEX idx_published_at (published_at),
    INDEX idx_crawled_at (crawled_at),
    INDEX idx_source_published (source_id, published_at),
    INDEX idx_url (url),
    INDEX idx_external_id (external_id),
    INDEX idx_category (category),
    INDEX idx_region (region)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Investing.com General News（全球金融市场综合新闻）消息表';

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
    'investing_com_news',
    'investing_com',
    'news',
    'Investing.com General News',
    JSON_OBJECT(
        'interval', 30,
        'mysql_table', 'mp_investing_com_messages',
        'chroma_collection', 'investing_com_news',
        'url', 'https://www.investing.com/rss/news.rss',
        'collector_module', 'backend.sources.investing_com.collector'
    ),
    '*/1 * * * *',
    1,
    NOW(),
    NOW()
) ON DUPLICATE KEY UPDATE
    config = JSON_OBJECT(
        'interval', 30,
        'mysql_table', 'mp_investing_com_messages',
        'chroma_collection', 'investing_com_news',
        'url', 'https://www.investing.com/rss/news.rss',
        'collector_module', 'backend.sources.investing_com.collector'
    ),
    updated_at = NOW();

-- 3. 验证注册结果
SELECT
    id,
    name,
    display_name,
    category,
    is_active,
    config->>'$.mysql_table' AS mysql_table,
    config->>'$.chroma_collection' AS chroma_collection,
    schedule
FROM mp_message_sources
WHERE name = 'investing_com_news';

-- 4. 验证表结构
SHOW CREATE TABLE mp_investing_com_messages;
