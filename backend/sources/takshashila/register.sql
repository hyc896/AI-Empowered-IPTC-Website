-- ================================================
-- Takshashila Institution 消息源注册SQL脚本
-- ================================================

USE message_platform;

-- 1. 创建消息表
CREATE TABLE IF NOT EXISTS mp_takshashila_messages (
    id VARCHAR(36) PRIMARY KEY COMMENT '消息ID（UUID）',
    source_id VARCHAR(36) NOT NULL COMMENT '来源ID',
    external_id VARCHAR(200) COMMENT '外部唯一标识（从URL文件名提取，如20251103-LEPF-Policy-Brief）',
    title VARCHAR(500) NOT NULL COMMENT '标题',
    content TEXT NOT NULL COMMENT '正文内容（从详情页提取）',
    summary TEXT COMMENT '中文摘要（翻译后）',
    provider VARCHAR(500) COMMENT '作者列表（多个用逗号分隔）',
    published_at DATETIME COMMENT '发布时间',
    crawled_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
    url VARCHAR(500) NOT NULL UNIQUE COMMENT '原文链接（用于去重）',

    region VARCHAR(50) DEFAULT 'IN' COMMENT '地区（IN=India）',
    language VARCHAR(10) DEFAULT 'en' COMMENT '语言（en）',
    publication_type VARCHAR(100) COMMENT '出版物类型（Policy Brief/Discussion Document/Working Paper等）',
    categories JSON COMMENT '分类标签列表（如Geopolitics, Public Policy, Governance）',
    metadata JSON COMMENT '其他元数据（JSON对象）',

    FOREIGN KEY (source_id) REFERENCES mp_message_sources(id) ON DELETE CASCADE,

    INDEX idx_source_id (source_id),
    INDEX idx_published_at (published_at),
    INDEX idx_crawled_at (crawled_at),
    INDEX idx_source_published (source_id, published_at),
    INDEX idx_url (url),
    INDEX idx_external_id (external_id),
    INDEX idx_publication_type (publication_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Takshashila Institution出版物表';

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
    'takshashila',
    'takshashila',
    'think_tank',
    'Takshashila Institution',
    JSON_OBJECT(
        'url', 'https://takshashila.org.in/pages/publications/',
        'mysql_table', 'mp_takshashila_messages',
        'chroma_collection', 'takshashila',
        'collector_module', 'backend.sources.takshashila',
        'interval', 86400,
        'region', 'IN',
        'language', 'en',
        'description', '印度塔克沙希拉研究所（Takshashila Institution）是印度领先的公共政策智库，专注于技术政策、地缘政治、国防与安全、治理等领域的研究。'
    ),
    '0 2 * * *',
    1,
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
    category,
    is_active,
    JSON_EXTRACT(config, '$.mysql_table') AS mysql_table,
    JSON_EXTRACT(config, '$.chroma_collection') AS chroma_collection,
    JSON_EXTRACT(config, '$.region') AS region
FROM mp_message_sources
WHERE name = 'takshashila';

-- 4. 验证表结构
SHOW CREATE TABLE mp_takshashila_messages;
