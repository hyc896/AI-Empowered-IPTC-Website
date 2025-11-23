-- La Nación AI专题采集器注册脚本
-- 阿根廷主流媒体人工智能新闻

-- 1. 创建消息表
CREATE TABLE IF NOT EXISTS mp_lanacion_messages (
    id VARCHAR(36) COLLATE utf8mb4_unicode_ci PRIMARY KEY COMMENT '消息ID（UUID）',
    source_id VARCHAR(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '来源ID',
    external_id VARCHAR(200) COMMENT '外部唯一标识（从URL提取，如nid12345）',
    title VARCHAR(500) NOT NULL COMMENT '标题（中文翻译）',
    content TEXT NOT NULL COMMENT '正文内容（中文翻译）',
    summary TEXT COMMENT '摘要（中文翻译）',
    provider VARCHAR(500) COMMENT '作者',
    published_at DATETIME COMMENT '发布时间',
    crawled_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
    url VARCHAR(500) NOT NULL UNIQUE COMMENT '原文链接（用于去重）',

    -- 新增必备字段（2025年强制要求）
    region VARCHAR(200) COMMENT '地区（中文格式，默认"阿根廷"，通过FieldEnricher动态提取）',
    industry_tags TEXT COMMENT '行业标签（逗号分隔，最多3个，涉及AI必须包含"人工智能"标签）',
    ai_tag VARCHAR(50) COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',

    -- 扩展字段
    language VARCHAR(10) DEFAULT 'es' COMMENT '原始语言（西班牙语）',

    -- 外键约束
    FOREIGN KEY (source_id) REFERENCES mp_message_sources(id) ON DELETE CASCADE,

    -- 索引（强制要求）
    INDEX idx_source_id (source_id),
    INDEX idx_published_at (published_at),
    INDEX idx_crawled_at (crawled_at),
    INDEX idx_source_published (source_id, published_at),
    INDEX idx_url (url),
    INDEX idx_external_id (external_id),
    INDEX idx_region (region),
    INDEX idx_ai_tag (ai_tag)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='La Nación AI专题消息表';

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
    'La Nación AI专题',
    'lanacion',
    'news',
    'La Nación (阿根廷)',
    JSON_OBJECT(
        'mysql_table', 'mp_lanacion_messages',
        'chroma_collection', 'lanacion',
        'collector_module', 'backend.sources.lanacion.collector',
        'region', '阿根廷',
        'language', 'es',
        'url', 'https://www.lanacion.com.ar/tema/inteligencia-artificial-tid58563/',
        'interval', 3600,
        'description', '阿根廷主流媒体La Nación的人工智能专题新闻'
    ),
    '0 */2 * * *',
    1,
    NOW(),
    NOW()
);

-- 验证注册结果
SELECT
    id,
    name,
    adapter_name,
    category,
    is_active,
    JSON_EXTRACT(config, '$.mysql_table') AS mysql_table,
    JSON_EXTRACT(config, '$.chroma_collection') AS chroma_collection,
    JSON_EXTRACT(config, '$.collector_module') AS collector_module
FROM mp_message_sources
WHERE name = 'La Nación AI专题';
