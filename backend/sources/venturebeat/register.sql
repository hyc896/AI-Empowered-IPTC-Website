-- VentureBeat科技媒体消息源注册脚本
-- 数据来源：
--   - AI栏目：https://venturebeat.com/category/ai
--   - 数据基础设施栏目：https://venturebeat.com/category/data-infrastructure
--   - 安全栏目：https://venturebeat.com/category/security

-- 1. 创建VentureBeat消息表
CREATE TABLE IF NOT EXISTS mp_venturebeat_messages (
    id VARCHAR(36) PRIMARY KEY COMMENT '消息ID（UUID）',
    source_id VARCHAR(36) NOT NULL COMMENT '来源ID',
    external_id VARCHAR(200) COMMENT '外部唯一标识（从URL路径提取slug）',
    title VARCHAR(500) NOT NULL COMMENT '标题',
    content TEXT NOT NULL COMMENT '正文内容（从详情页提取的完整文章）',
    summary TEXT COMMENT '中文摘要（翻译后）',
    provider VARCHAR(500) COMMENT '作者（多个用逗号分隔）',
    published_at DATETIME COMMENT '发布时间',
    crawled_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
    url VARCHAR(500) NOT NULL UNIQUE COMMENT '原文链接（用于去重）',

    -- 新增必备字段（2025年强制要求）
    region VARCHAR(200) COMMENT '地区（中文格式，如"美国"、"美国/加利福尼亚州"、"全球"等）',
    industry_tags TEXT COMMENT '行业标签（逗号分隔，最多3个，涉及AI必须包含"人工智能"标签）',

    -- 扩展字段
    category VARCHAR(100) COMMENT '文章分类（AI/Data Infrastructure/Security）',
    language VARCHAR(10) DEFAULT 'en' COMMENT '语言（en）',
    excerpt TEXT COMMENT '摘要（从列表页提取的excerpt）',
    featured_image VARCHAR(500) COMMENT '特色图片URL',
    tags JSON COMMENT '标签列表（JSON数组）',
    metadata JSON COMMENT '其他元数据（JSON对象）',

    -- 外键约束
    CONSTRAINT fk_venturebeat_source FOREIGN KEY (source_id) REFERENCES mp_message_sources(id) ON DELETE CASCADE,

    -- 索引
    INDEX idx_source_id (source_id),
    INDEX idx_published_at (published_at),
    INDEX idx_crawled_at (crawled_at),
    INDEX idx_source_published (source_id, published_at),
    INDEX idx_url (url),
    INDEX idx_external_id (external_id),
    INDEX idx_category (category),
    INDEX idx_region (region)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='VentureBeat科技媒体（美国AI、数据基础设施、安全领域新闻）消息表';

-- 2. 注册VentureBeat消息源
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
    'venturebeat',
    'venturebeat',
    'news',
    'VentureBeat科技媒体',
    JSON_OBJECT(
        'mysql_table', 'mp_venturebeat_messages',
        'chroma_collection', 'venturebeat',
        'collector_module', 'backend.sources.venturebeat.collector',
        'collector_class', 'VentureBeatCollector',
        'categories', JSON_ARRAY('ai', 'data-infrastructure', 'security'),
        'region', 'US',
        'language', 'en',
        'interval', 86400
    ),
    '0 0 * * *',
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
    JSON_EXTRACT(config, '$.categories') AS categories
FROM mp_message_sources
WHERE name = 'venturebeat';
