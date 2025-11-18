-- ===================================================================
-- The Guardian AI与科技新闻采集器注册脚本
-- ===================================================================
-- 执行前请确认：
-- 1. MySQL服务运行正常
-- 2. 数据库message_platform存在
-- 3. 字符集设置正确（utf8mb4）
-- ===================================================================

USE message_platform;

-- 1. 创建消息表
CREATE TABLE IF NOT EXISTS mp_guardian_messages (
    id VARCHAR(36) PRIMARY KEY COMMENT '消息ID（UUID）',
    source_id VARCHAR(36) NOT NULL COMMENT '来源ID',
    external_id VARCHAR(200) COMMENT '外部唯一标识（RSS guid）',
    title VARCHAR(500) NOT NULL COMMENT '标题',
    content TEXT NOT NULL COMMENT '正文内容（RSS description或summary）',
    summary TEXT COMMENT '摘要（中文翻译）',
    provider VARCHAR(500) COMMENT '作者（多个用逗号分隔）',
    published_at DATETIME COMMENT '发布时间',
    crawled_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
    url VARCHAR(500) NOT NULL UNIQUE COMMENT '原文链接（用于去重）',

    region VARCHAR(200) COMMENT '地区（中文格式，如英国、全球等）',
    industry_tags TEXT COMMENT '行业标签（逗号分隔，最多3个）',
    ai_tag VARCHAR(50) COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',

    category VARCHAR(100) COMMENT '分类（AI/Technology/Security等）',
    language VARCHAR(10) DEFAULT 'en' COMMENT '语言（en）',

    FOREIGN KEY (source_id) REFERENCES mp_message_sources(id) ON DELETE CASCADE,

    INDEX idx_source_id (source_id),
    INDEX idx_published_at (published_at),
    INDEX idx_crawled_at (crawled_at),
    INDEX idx_source_published (source_id, published_at),
    INDEX idx_url (url),
    INDEX idx_external_id (external_id),
    INDEX idx_category (category),
    INDEX idx_region (region)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='The Guardian AI与科技新闻消息表';

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
    'guardian',
    'guardian',
    'news',
    'The Guardian (UK)',
    JSON_OBJECT(
        'interval', 3600,
        'mysql_table', 'mp_guardian_messages',
        'chroma_collection', 'guardian_news',
        'collector_module', 'backend.sources.guardian.collector.GuardianCollector',
        'region', 'UK',
        'language', 'en',
        'rss_feeds', JSON_ARRAY(
            JSON_OBJECT(
                'url', 'https://www.theguardian.com/technology/artificialintelligenceai/rss',
                'category', 'AI'
            ),
            JSON_OBJECT(
                'url', 'https://www.theguardian.com/uk/technology/rss',
                'category', 'Technology'
            ),
            JSON_OBJECT(
                'url', 'https://www.theguardian.com/technology/data-computer-security/rss',
                'category', 'Security'
            )
        )
    ),
    '0 */1 * * *',
    1,
    NOW(),
    NOW()
) ON DUPLICATE KEY UPDATE
    display_name = VALUES(display_name),
    config = VALUES(config),
    schedule = VALUES(schedule),
    is_active = VALUES(is_active),
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
    JSON_LENGTH(JSON_EXTRACT(config, '$.rss_feeds')) AS rss_feed_count,
    schedule,
    created_at
FROM mp_message_sources
WHERE name = 'guardian';

-- 4. 验证表结构
SHOW CREATE TABLE mp_guardian_messages\G

-- 5. 查询表中已有消息数量
SELECT COUNT(*) AS message_count FROM mp_guardian_messages;
