-- World Economic Forum (WEF) AI Publications 消息源注册脚本
-- 世界经济论坛AI出版物消息源

-- 1. 创建消息表
CREATE TABLE IF NOT EXISTS `mp_wef_publication_messages` (
  `id` varchar(36) NOT NULL COMMENT '消息ID（UUID）',
  `source_id` varchar(36) NOT NULL COMMENT '来源ID',
  `external_id` varchar(100) DEFAULT NULL COMMENT '外部唯一标识（从URL路径提取slug）',
  `title` varchar(500) NOT NULL COMMENT '出版物标题',
  `content` text NOT NULL COMMENT '出版物正文内容',
  `summary` text COMMENT '中文摘要（翻译后）',
  `provider` varchar(500) DEFAULT NULL COMMENT '合作方（如Ministry of Economy of UAE等）',
  `published_at` datetime DEFAULT NULL COMMENT '发布时间',
  `crawled_at` datetime NOT NULL COMMENT '抓取时间',
  `url` varchar(500) NOT NULL COMMENT '出版物链接（用于去重）',
  `region` varchar(50) DEFAULT 'GLOBAL' COMMENT '地区（GLOBAL）',
  `category` varchar(100) DEFAULT NULL COMMENT '出版物分类（如EMERGING TECHNOLOGIES等）',
  `language` varchar(10) DEFAULT 'en' COMMENT '语言（en）',
  `metadata` json DEFAULT NULL COMMENT '其他元数据（JSON对象）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `url` (`url`),
  KEY `idx_source_id` (`source_id`),
  KEY `idx_published_at` (`published_at`),
  KEY `idx_crawled_at` (`crawled_at`),
  KEY `idx_source_published` (`source_id`,`published_at`),
  KEY `idx_url` (`url`),
  KEY `idx_external_id` (`external_id`),
  KEY `idx_category` (`category`),
  CONSTRAINT `fk_wef_publication_source` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='World Economic Forum AI出版物表';

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
  'wef_publications',
  'wef_publications',
  'news',
  'World Economic Forum AI Publications',
  JSON_OBJECT(
    'url', 'https://www.weforum.org/publications/',
    'mysql_table', 'mp_wef_publication_messages',
    'chroma_collection', 'wef_publications',
    'collector_module', 'backend.sources.wef_publications.collector',
    'region', 'GLOBAL',
    'timezone', 'Europe/Zurich',
    'language', 'en',
    'interval', 86400
  ),
  '0 2 * * *',
  1,
  NOW(),
  NOW()
);

-- 3. 验证注册结果
SELECT
  id,
  name,
  display_name,
  category,
  is_active,
  JSON_EXTRACT(config, '$.mysql_table') as mysql_table,
  JSON_EXTRACT(config, '$.chroma_collection') as chroma_collection,
  JSON_EXTRACT(config, '$.collector_module') as collector_module
FROM mp_message_sources
WHERE name = 'wef_publications';
