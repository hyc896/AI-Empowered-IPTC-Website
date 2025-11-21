-- The Hindu Business采集器注册脚本
-- 执行命令（Linux）：
-- mysql -h localhost -P 3306 -u root -p123456 --default-character-set=utf8mb4 message_platform < backend/sources/the_hindu/register.sql

USE message_platform;

-- 1. 创建消息表
CREATE TABLE IF NOT EXISTS mp_the_hindu_messages (
    id VARCHAR(36) PRIMARY KEY COMMENT '消息ID（UUID）',
    source_id VARCHAR(36) NOT NULL COMMENT '来源ID',
    external_id VARCHAR(200) COMMENT '外部唯一标识（RSS的guid字段）',
    title VARCHAR(500) NOT NULL COMMENT '标题（RSS的title字段）',
    content TEXT NOT NULL COMMENT '正文内容（RSS的description字段）',
    summary TEXT COMMENT '中文摘要（翻译后）',
    provider VARCHAR(500) COMMENT '作者（RSS的author字段）',
    published_at DATETIME COMMENT '发布时间（RSS的pubDate字段）',
    crawled_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
    url VARCHAR(500) NOT NULL UNIQUE COMMENT '原文链接（RSS的link字段，用于去重）',

    region VARCHAR(200) COMMENT '地区（中文格式，从文章内容提取）',
    industry_tags TEXT COMMENT '行业标签（逗号分隔，最多3个，涉及AI必须包含"人工智能"标签）',
    ai_tag VARCHAR(50) COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',

    category VARCHAR(100) COMMENT '文章分类（RSS的category字段）',
    language VARCHAR(10) DEFAULT 'en' COMMENT '语言',
    media_content VARCHAR(500) COMMENT '媒体内容URL（RSS的media:content字段）',
    tags JSON COMMENT '标签列表（JSON数组）',
    metadata JSON COMMENT '其他元数据（JSON对象）',

    FOREIGN KEY (source_id) REFERENCES mp_message_sources(id) ON DELETE CASCADE,
    INDEX idx_source_id (source_id),
    INDEX idx_published_at (published_at),
    INDEX idx_crawled_at (crawled_at),
    INDEX idx_source_published (source_id, published_at),
    INDEX idx_url (url),
    INDEX idx_external_id (external_id),
    INDEX idx_category (category),
    INDEX idx_region (region),
    INDEX idx_ai_tag (ai_tag)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='The Hindu Business消息表（RSS Feed采集）';

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
    'The Hindu Business',
    'the_hindu',
    'news',
    'The Hindu Business（印度教徒报商业频道，报道商业科技与产业动态，更新频率高）',
    JSON_OBJECT(
        'mysql_table', 'mp_the_hindu_messages',
        'chroma_collection', 'the_hindu_tech',
        'region', '印度',
        'language', 'en',
        'rss_url', 'https://www.thehindu.com/business/feeder/default.rss',
        'collector_module', 'backend.sources.the_hindu.collector',
        'description', '印度教徒报商业频道，报道商业科技与产业动态，更新频率高'
    ),
    '0 */1 * * *',
    1,
    NOW(),
    NOW()
) ON DUPLICATE KEY UPDATE
    config = VALUES(config),
    updated_at = NOW();

-- 3. 验证注册结果
SELECT
    id,
    name,
    category,
    display_name,
    is_active,
    JSON_EXTRACT(config, '$.mysql_table') as mysql_table,
    JSON_EXTRACT(config, '$.chroma_collection') as chroma_collection,
    JSON_EXTRACT(config, '$.collector_module') as collector_module
FROM mp_message_sources
WHERE name = 'The Hindu Business';

-- 4. 检查表是否创建成功
SHOW CREATE TABLE mp_the_hindu_messages\G
