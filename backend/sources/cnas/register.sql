-- CNAS消息源注册脚本
-- Center for a New American Security (新美国安全中心)

-- 1. 创建消息表
CREATE TABLE IF NOT EXISTS `mp_cnas_messages` (
  `id` varchar(36) NOT NULL COMMENT '消息ID（UUID）',
  `source_id` varchar(36) NOT NULL COMMENT '来源ID',
  `external_id` varchar(100) DEFAULT NULL COMMENT '外部唯一标识（从URL路径提取slug）',
  `title` varchar(500) NOT NULL COMMENT '文章标题',
  `content` text NOT NULL COMMENT '文章正文内容',
  `summary` text COMMENT '中文摘要（翻译后）',
  `provider` varchar(500) DEFAULT NULL COMMENT '作者列表（逗号分隔）',
  `published_at` datetime DEFAULT NULL COMMENT '发布时间',
  `crawled_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
  `url` varchar(500) NOT NULL COMMENT '文章链接（用于去重）',
  `region` varchar(50) DEFAULT 'US' COMMENT '地区（US）',
  `category` varchar(100) DEFAULT NULL COMMENT '内容分类（Defense/Technology & National Security等）',
  `language` varchar(10) DEFAULT 'en' COMMENT '语言（en）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `url` (`url`),
  KEY `idx_source_id` (`source_id`),
  KEY `idx_published_at` (`published_at`),
  KEY `idx_crawled_at` (`crawled_at`),
  KEY `idx_source_published` (`source_id`,`published_at`),
  KEY `idx_url` (`url`),
  KEY `idx_external_id` (`external_id`),
  KEY `idx_category` (`category`),
  CONSTRAINT `fk_cnas_source` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='CNAS（新美国安全中心）文章表';

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
  'cnas',
  'cnas',
  'news',
  'CNAS 新美国安全中心',
  JSON_OBJECT(
    'interval', 86400,
    'mysql_table', 'mp_cnas_messages',
    'chroma_collection', 'cnas_reports',
    'collector_module', 'backend.sources.cnas.collector.CNASCollector',
    'url', 'https://www.cnas.org/reports',
    'region', 'US',
    'timezone', 'America/New_York',
    'language', 'en'
  ),
  '0 2 * * *',
  1,
  NOW(),
  NOW()
) ON DUPLICATE KEY UPDATE
  `display_name` = VALUES(`display_name`),
  `config` = VALUES(`config`),
  `schedule` = VALUES(`schedule`),
  `is_active` = VALUES(`is_active`),
  `updated_at` = NOW();

-- 3. 验证注册结果
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
WHERE name = 'cnas';
