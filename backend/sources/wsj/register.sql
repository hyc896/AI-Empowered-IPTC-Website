-- ==========================================
-- Wall Street Journal Technology 消息源注册脚本
-- ==========================================

-- 创建消息表
CREATE TABLE IF NOT EXISTS mp_wsj_messages (
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
    region VARCHAR(200) COMMENT '地区（中文格式，从文章内容提取，如"美国"、"全球"等）',
    industry_tags TEXT COMMENT '行业标签（逗号分隔，最多3个，涉及AI必须包含"人工智能"标签）',
    ai_tag VARCHAR(50) COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',
    category VARCHAR(100) COMMENT '文章分类（RSS的category字段）',
    language VARCHAR(10) DEFAULT 'en' COMMENT '语言（en=英文）',
    media_content VARCHAR(500) COMMENT '媒体内容URL（RSS的media:content字段）',
    tags JSON COMMENT '标签列表（JSON数组）',
    metadata JSON COMMENT '其他元数据（JSON对象）',

    -- 外键约束
    CONSTRAINT fk_wsj_source FOREIGN KEY (source_id)
        REFERENCES mp_message_sources(id) ON DELETE CASCADE,

    -- 索引
    INDEX idx_source_id (source_id),
    INDEX idx_published_at (published_at),
    INDEX idx_crawled_at (crawled_at),
    INDEX idx_source_published (source_id, published_at),
    INDEX idx_url (url),
    INDEX idx_external_id (external_id),
    INDEX idx_category (category),
    INDEX idx_region (region),
    INDEX idx_ai_tag (ai_tag)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='华尔街日报科技新闻消息表';

-- 插入消息源配置
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
    'wsj_tech',
    'wsj',
    'news',
    '华尔街日报科技版',
    JSON_OBJECT(
        'mysql_table', 'mp_wsj_messages',
        'chroma_collection', 'wsj_tech',
        'collector_module', 'backend.sources.wsj.collector',
        'region', '美国',
        'language', 'en',
        'interval', 3600
    ),
    '0 */1 * * *',
    1,
    NOW(),
    NOW()
);
