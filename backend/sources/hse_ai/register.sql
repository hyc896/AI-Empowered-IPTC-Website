-- HSE University AI Research Centre 消息源注册脚本
-- 俄罗斯高等经济学院AI研究中心

USE message_platform;

-- 1. 创建消息表
CREATE TABLE IF NOT EXISTS mp_hse_ai_messages (
    id VARCHAR(36) PRIMARY KEY COMMENT '消息ID（UUID）',
    source_id VARCHAR(36) NOT NULL COMMENT '来源ID',
    external_id VARCHAR(200) COMMENT '外部唯一标识（从URL提取的数字ID）',
    title VARCHAR(500) NOT NULL COMMENT '标题',
    content TEXT NOT NULL COMMENT '正文内容（英文）',
    summary TEXT COMMENT '摘要（中文翻译）',
    provider VARCHAR(500) COMMENT '作者或主要人物（多个用逗号分隔）',
    published_at DATETIME COMMENT '发布时间',
    crawled_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
    url VARCHAR(500) NOT NULL UNIQUE COMMENT '原文链接（用于去重）',
    region VARCHAR(50) DEFAULT 'RU' COMMENT '地区（RU=Russia）',
    category VARCHAR(100) COMMENT '分类（Research & Expertise等）',
    language VARCHAR(10) DEFAULT 'en' COMMENT '语言（en）',
    tags JSON COMMENT '关键词标签（JSON数组）',
    metadata JSON COMMENT '其他元数据（JSON对象）',

    FOREIGN KEY (source_id) REFERENCES mp_message_sources(id) ON DELETE CASCADE,

    INDEX idx_source_id (source_id),
    INDEX idx_published_at (published_at),
    INDEX idx_crawled_at (crawled_at),
    INDEX idx_source_published (source_id, published_at),
    INDEX idx_url (url),
    INDEX idx_external_id (external_id),
    INDEX idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='HSE University AI Research Centre 新闻消息表';

-- 2. 注册消息源到 mp_message_sources 表
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
    'hse_ai',
    'hse_ai',
    'news',
    'HSE University AI Research Centre',
    JSON_OBJECT(
        'url', 'https://cs.hse.ru/en/aicenter/news/',
        'interval', 86400,
        'mysql_table', 'mp_hse_ai_messages',
        'chroma_collection', 'hse_ai_news',
        'collector_module', 'backend.sources.hse_ai.collector',
        'collector_class', 'HSEAICollector',
        'region', 'RU',
        'language', 'en',
        'description', 'HSE University AI Research Centre news and research updates'
    ),
    '0 2 * * *',
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
    JSON_EXTRACT(config, '$.region') AS region,
    created_at
FROM mp_message_sources
WHERE name = 'hse_ai';

-- 4. 验证表创建
SHOW CREATE TABLE mp_hse_ai_messages;
