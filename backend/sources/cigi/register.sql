-- ==========================================
-- CIGI (Centre for International Governance Innovation) 消息源注册脚本
-- 国际治理创新中心（加拿大智库）
-- ==========================================

-- 1. 创建消息表
CREATE TABLE IF NOT EXISTS `mp_cigi_messages` (
  `id` varchar(36) NOT NULL COMMENT '消息ID（UUID）',
  `source_id` varchar(36) NOT NULL COMMENT '来源ID',
  `external_id` varchar(200) DEFAULT NULL COMMENT '外部唯一标识（从URL路径提取slug）',
  `title` varchar(500) NOT NULL COMMENT '标题',
  `content` text NOT NULL COMMENT '正文内容',
  `summary` text COMMENT '中文摘要（优先从网页提取，无则翻译content前1000字）',
  `provider` varchar(500) DEFAULT NULL COMMENT '作者列表（多个用逗号分隔）',
  `published_at` datetime DEFAULT NULL COMMENT '发布时间',
  `crawled_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
  `url` varchar(500) NOT NULL COMMENT '原文链接（用于去重）',
  `region` varchar(50) DEFAULT 'CA' COMMENT '地区（CA=Canada）',
  `content_type` varchar(50) DEFAULT NULL COMMENT '内容类型（Publication/Opinion/News Releases/Multimedia/Event/Op-Eds）',
  `language` varchar(10) DEFAULT 'en' COMMENT '语言（en）',
  `pdf_url` varchar(500) DEFAULT NULL COMMENT 'PDF下载链接（如果有）',
  `metadata` json DEFAULT NULL COMMENT '其他元数据（JSON对象）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `url` (`url`),
  KEY `idx_source_id` (`source_id`),
  KEY `idx_published_at` (`published_at`),
  KEY `idx_crawled_at` (`crawled_at`),
  KEY `idx_source_published` (`source_id`,`published_at`),
  KEY `idx_external_id` (`external_id`),
  KEY `idx_content_type` (`content_type`),
  CONSTRAINT `fk_cigi_source_id` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='CIGI（国际治理创新中心）研究出版物表';

-- 2. 注册消息源
INSERT INTO `mp_message_sources` (
    `id`,
    `name`,
    `adapter_name`,
    `category`,
    `display_name`,
    `config`,
    `schedule`,
    `is_active`,
    `created_at`,
    `updated_at`
) VALUES (
    UUID(),
    'cigi_ai',
    'CIGICollector',
    'news',
    'CIGI - AI主题',
    JSON_OBJECT(
        'url', 'https://www.cigionline.org/topics/artificial-intelligence/',
        'region', 'CA',
        'language', 'en',
        'timezone', 'America/Toronto',
        'mysql_table', 'mp_cigi_messages',
        'chroma_collection', 'cigi_ai',
        'collector_module', 'backend.sources.cigi.collector',
        'interval', 86400
    ),
    '0 2 * * *',
    1,
    NOW(),
    NOW()
) ON DUPLICATE KEY UPDATE
    `adapter_name` = VALUES(`adapter_name`),
    `display_name` = VALUES(`display_name`),
    `config` = VALUES(`config`),
    `schedule` = VALUES(`schedule`),
    `updated_at` = NOW();

-- 3. 验证注册结果
SELECT
    id,
    name,
    adapter_name,
    display_name,
    category,
    is_active,
    JSON_EXTRACT(config, '$.mysql_table') as mysql_table,
    JSON_EXTRACT(config, '$.chroma_collection') as chroma_collection,
    JSON_EXTRACT(config, '$.url') as url,
    created_at
FROM mp_message_sources
WHERE name = 'cigi_ai';

-- 4. 检查表结构
SHOW CREATE TABLE mp_cigi_messages;

-- ==========================================
-- 注册完成提示
-- ==========================================
-- 执行完成后，请检查：
-- 1. mp_cigi_messages 表已创建
-- 2. mp_message_sources 表中已有 cigi_ai 记录
-- 3. is_active = 1 表示已启用
-- 4. 表的 COMMENT 字段未出现乱码（中文正常显示）
-- ==========================================
