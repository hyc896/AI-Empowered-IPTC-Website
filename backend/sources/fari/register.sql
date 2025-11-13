-- FARI - AI for the Common Good Institute 消息源注册
-- 比利时AI公益研究所

-- 创建消息表
CREATE TABLE IF NOT EXISTS mp_fari_messages (
    id VARCHAR(36) PRIMARY KEY COMMENT '消息ID（UUID）',
    source_id VARCHAR(36) NOT NULL COMMENT '来源ID',
    external_id VARCHAR(200) COMMENT '外部唯一标识（从URL路径提取slug）',
    title VARCHAR(500) NOT NULL COMMENT '标题',
    content TEXT NOT NULL COMMENT '正文内容（从详情页提取完整内容）',
    summary TEXT COMMENT '中文摘要（翻译后）',
    provider VARCHAR(500) COMMENT '作者（多个用逗号分隔）',
    published_at DATETIME COMMENT '发布时间',
    crawled_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
    url VARCHAR(500) UNIQUE NOT NULL COMMENT '原文链接（用于去重）',
    region VARCHAR(50) DEFAULT 'BE' COMMENT '地区（BE=Belgium 比利时）',
    content_type VARCHAR(100) COMMENT '内容类型（News/Report/Journal Article/Conference Proceeding/Thesis）',
    language VARCHAR(10) DEFAULT 'en' COMMENT '语言（en）',
    tags JSON COMMENT '主题标签（如Sustainable AI、Data & Robotics等）',
    pdf_url VARCHAR(500) COMMENT 'PDF下载链接（出版物）',
    metadata JSON COMMENT '其他元数据（JSON对象）',

    -- 外键约束
    FOREIGN KEY (source_id) REFERENCES mp_message_sources(id) ON DELETE CASCADE,

    -- 索引
    INDEX idx_source_id (source_id),
    INDEX idx_published_at (published_at),
    INDEX idx_crawled_at (crawled_at),
    INDEX idx_source_published (source_id, published_at),
    INDEX idx_url (url),
    INDEX idx_external_id (external_id),
    INDEX idx_content_type (content_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='FARI - AI for the Common Good Institute 新闻与出版物表';

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
    created_at,
    updated_at
) VALUES (
    UUID(),
    'fari',
    'fari',
    'think_tank',
    'FARI - AI for the Common Good Institute',
    JSON_OBJECT(
        'mysql_table', 'mp_fari_messages',
        'chroma_collection', 'fari',
        'collector_module', 'backend.sources.fari.collector',
        'collector_class', 'FARICollector',
        'news_url', 'https://www.fari.brussels/news-and-media/news',
        'publications_url', 'https://www.fari.brussels/research-and-innovation/publications',
        'region', 'BE',
        'language', 'en',
        'interval', 86400
    ),
    '0 0 2 * * ?',
    1,
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
    JSON_EXTRACT(config, '$.chroma_collection') as chroma_collection,
    created_at
FROM mp_message_sources
WHERE name = 'fari';
