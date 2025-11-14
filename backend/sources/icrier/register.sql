-- ==================================================================================
-- ICRIER (Indian Council for Research on International Economic Relations) 注册脚本
-- 印度国际经济关系研究委员会
-- ==================================================================================

-- 1. 创建消息表
CREATE TABLE IF NOT EXISTS mp_icrier_messages (
    id VARCHAR(36) PRIMARY KEY COMMENT '消息ID（UUID）',
    source_id VARCHAR(36) NOT NULL COMMENT '来源ID',
    external_id VARCHAR(200) COMMENT '外部唯一标识（URL slug）',
    title VARCHAR(500) NOT NULL COMMENT '标题',
    content TEXT NOT NULL COMMENT '正文内容（英文摘要）',
    summary TEXT COMMENT '摘要（中文翻译）',
    provider VARCHAR(500) COMMENT '作者（多个用逗号分隔）',
    published_at DATETIME COMMENT '发布时间',
    crawled_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
    url VARCHAR(500) UNIQUE NOT NULL COMMENT '原文链接（用于去重）',
    region VARCHAR(50) DEFAULT 'IN' COMMENT '地区（IN=India）',
    category VARCHAR(100) COMMENT '分类（Policy Briefs/Reports/Bulletins等）',
    language VARCHAR(10) DEFAULT 'en' COMMENT '语言（en）',
    pdf_url VARCHAR(500) COMMENT 'PDF下载链接',
    metadata JSON COMMENT '其他元数据（JSON对象）',
    FOREIGN KEY (source_id) REFERENCES mp_message_sources(id) ON DELETE CASCADE,
    INDEX idx_source_id (source_id),
    INDEX idx_published_at (published_at),
    INDEX idx_crawled_at (crawled_at),
    INDEX idx_source_published (source_id, published_at),
    INDEX idx_url (url),
    INDEX idx_external_id (external_id),
    INDEX idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='ICRIER印度智库出版物表';

-- 2. 注册消息源
INSERT INTO mp_message_sources (id, name, adapter_name, category, display_name, config, is_active, created_at, updated_at)
VALUES (
    UUID(),
    'icrier',
    'icrier',
    'research',
    'ICRIER - 印度国际经济关系研究委员会',
    JSON_OBJECT(
        'collector_module', 'backend.sources.icrier.collector',
        'collector_class', 'ICRIERCollector',
        'interval', 86400,
        'mysql_table', 'mp_icrier_messages',
        'chroma_collection', 'icrier_publications',
        'url', 'https://icrier.org/publication/',
        'region', 'IN',
        'language', 'en'
    ),
    1,
    NOW(),
    NOW()
)
ON DUPLICATE KEY UPDATE
    display_name = VALUES(display_name),
    config = VALUES(config),
    updated_at = NOW();

-- 3. 验证注册
SELECT
    id,
    name,
    display_name,
    category,
    is_active,
    JSON_EXTRACT(config, '$.mysql_table') AS mysql_table,
    JSON_EXTRACT(config, '$.chroma_collection') AS chroma_collection,
    JSON_EXTRACT(config, '$.url') AS url
FROM mp_message_sources
WHERE name = 'icrier';
