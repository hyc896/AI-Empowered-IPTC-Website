-- OBIA (Observatório Brasileiro de Inteligência Artificial) 巴西AI观测站注册脚本
-- 执行方式：
-- chcp 65001
-- mysql -h localhost -P 3306 -u root -p123456 --default-character-set=utf8mb4 message_platform < backend/sources/obia/register.sql

USE message_platform;

-- 1. 创建消息表
CREATE TABLE IF NOT EXISTS mp_obia_messages (
    id VARCHAR(36) PRIMARY KEY COMMENT '消息ID（UUID）',
    source_id VARCHAR(36) NOT NULL COMMENT '来源ID',
    external_id VARCHAR(200) COMMENT '外部唯一标识（从PDF URL提取data-guid）',
    title VARCHAR(500) NOT NULL COMMENT '标题',
    content TEXT NOT NULL COMMENT '正文内容（描述信息）',
    summary TEXT COMMENT '摘要（中文翻译）',
    provider VARCHAR(500) COMMENT '作者列表（多个用逗号分隔）',
    published_at DATETIME COMMENT '发布时间（从PDF URL中的时间戳提取，格式：YYYYMMDDhhmmss）',
    crawled_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
    url VARCHAR(500) NOT NULL UNIQUE COMMENT '原文链接（PDF直链，用于去重）',
    region VARCHAR(50) DEFAULT 'BR' COMMENT '地区（BR=Brazil 巴西）',
    category VARCHAR(100) COMMENT '分类（PANORAMA SETORIAL DA INTERNET/PESQUISAS TIC等）',
    language VARCHAR(10) DEFAULT 'pt' COMMENT '语言（pt=葡萄牙语）',
    pdf_url VARCHAR(500) COMMENT 'PDF下载链接（与url相同）',
    series VARCHAR(100) COMMENT '系列名称（Panorama Setorial/TIC Empresas/TIC Governo等）',
    metadata JSON COMMENT '其他元数据（JSON对象）',

    -- 外键
    CONSTRAINT fk_obia_source FOREIGN KEY (source_id) REFERENCES mp_message_sources(id) ON DELETE CASCADE,

    -- 索引
    INDEX idx_source_id (source_id),
    INDEX idx_published_at (published_at),
    INDEX idx_crawled_at (crawled_at),
    INDEX idx_source_published (source_id, published_at),
    INDEX idx_url (url),
    INDEX idx_external_id (external_id),
    INDEX idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='OBIA巴西AI观测站研究出版物表';

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
    'obia',
    'obia',
    'research',
    'OBIA - Brazilian AI Observatory',
    JSON_OBJECT(
        'url', 'https://obia.nic.br/s/publicacoes',
        'mysql_table', 'mp_obia_messages',
        'chroma_collection', 'obia_publications',
        'interval', 86400,
        'region', 'BR',
        'language', 'pt',
        'collector_module', 'backend.sources.obia.collector.OBIACollector'
    ),
    '0 0 * * *',
    1,
    NOW(),
    NOW()
) ON DUPLICATE KEY UPDATE
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
    JSON_EXTRACT(config, '$.region') AS region,
    created_at
FROM mp_message_sources
WHERE name = 'obia';

-- 4. 验证表结构
SHOW CREATE TABLE mp_obia_messages\G
