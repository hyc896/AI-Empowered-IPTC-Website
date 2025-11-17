-- TechCrunch Tech News 消息源注册脚本
-- 创建表并注册到mp_message_sources

-- Step 1: 创建mp_techcrunch_messages表
CREATE TABLE IF NOT EXISTS mp_techcrunch_messages (
    id VARCHAR(36) PRIMARY KEY COMMENT '消息ID（UUID）',
    source_id VARCHAR(36) NOT NULL COMMENT '来源ID',
    external_id VARCHAR(200) COMMENT '外部唯一标识（从URL提取的post ID或slug）',
    title VARCHAR(500) NOT NULL COMMENT '标题',
    content TEXT NOT NULL COMMENT '正文内容（完整文章内容）',
    summary TEXT COMMENT '摘要（中文翻译）',
    provider VARCHAR(500) COMMENT '作者（多个用逗号分隔）',
    published_at DATETIME COMMENT '发布时间',
    crawled_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
    url VARCHAR(500) NOT NULL UNIQUE COMMENT '原文链接（用于去重）',

    region VARCHAR(200) COMMENT '地区（中文格式，多为全球、美国等）',
    industry_tags TEXT COMMENT '行业标签（逗号分隔，最多3个）',
    ai_tag VARCHAR(50) COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',

    category VARCHAR(100) COMMENT '分类（AI/Security/Robotics/Cloud Computing/Hardware等）',
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='TechCrunch Tech News（全球科技新闻与深度报道）消息表';

-- Step 2: 注册消息源到mp_message_sources表
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
    'techcrunch',
    'techcrunch',
    'news',
    'TechCrunch Tech News',
    JSON_OBJECT(
        'interval', 7200,
        'mysql_table', 'mp_techcrunch_messages',
        'chroma_collection', 'techcrunch_messages',
        'collector_module', 'backend.sources.techcrunch.collector',
        'collector_class', 'TechCrunchCollector',
        'region', 'GLOBAL',
        'language', 'en',
        'categories', JSON_ARRAY(
            'AI',
            'Security',
            'Robotics',
            'Cloud Computing',
            'Hardware',
            'Enterprise',
            'Government & Policy',
            'Privacy',
            'Biotech & Health'
        )
    ),
    '0 */2 * * *',
    1,
    NOW(),
    NOW()
) ON DUPLICATE KEY UPDATE
    display_name = VALUES(display_name),
    config = VALUES(config),
    schedule = VALUES(schedule),
    updated_at = NOW();

-- Step 3: 验证注册结果
SELECT
    id,
    name,
    display_name,
    category,
    is_active,
    JSON_EXTRACT(config, '$.mysql_table') AS mysql_table,
    JSON_EXTRACT(config, '$.chroma_collection') AS chroma_collection,
    JSON_EXTRACT(config, '$.interval') AS interval_seconds,
    schedule
FROM mp_message_sources
WHERE name = 'techcrunch';

-- Step 4: 检查表是否创建成功
SHOW CREATE TABLE mp_techcrunch_messages;
