-- Partnership on AI博客采集器注册SQL

-- 1. 创建mp_partnership_ai_messages表（如果不存在）
CREATE TABLE IF NOT EXISTS `mp_partnership_ai_messages` (
  `id` VARCHAR(36) NOT NULL COMMENT '消息ID（UUID）',
  `source_id` VARCHAR(36) NOT NULL COMMENT '来源ID',
  `external_id` VARCHAR(100) COMMENT '外部唯一标识（post_id/article_id/event_id等）',
  `title` VARCHAR(500) NOT NULL COMMENT '标题',
  `content` TEXT NOT NULL COMMENT '正文内容',
  `summary` TEXT COMMENT '摘要（优先从网页提取，无则用content，content>1000字时取前1000字）',
  `provider` VARCHAR(500) COMMENT '作者或信息提供方（多个用逗号分隔）',
  `published_at` DATETIME COMMENT '发布时间',
  `crawled_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
  `url` VARCHAR(500) NOT NULL COMMENT '原文链接（用于去重）',
  `region` VARCHAR(50) COMMENT '地区（US/EU/UK/GLOBAL等）',
  `category` VARCHAR(100) COMMENT '分类（AI Governance/Policy/Research等）',
  `language` VARCHAR(10) COMMENT '语言（en/zh/fr等）',
  `tags` JSON COMMENT '标签列表（JSON数组）',
  `metadata` JSON COMMENT '其他元数据（JSON对象）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_url` (`url`),
  KEY `idx_source_id` (`source_id`),
  KEY `idx_published_at` (`published_at`),
  KEY `idx_crawled_at` (`crawled_at`),
  KEY `idx_source_published` (`source_id`, `published_at`),
  KEY `idx_external_id` (`external_id`),
  KEY `idx_region` (`region`),
  KEY `idx_category` (`category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Partnership on AI博客消息表（2025统一字段标准）';

-- 2. 注册消息源到mp_message_sources表
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
  'partnership_ai',
  'partnership_ai_collector',
  'ai_governance',
  'Partnership on AI',
  JSON_OBJECT(
    'url', 'https://partnershiponai.org/blog/',
    'interval', 86400,
    'mysql_table', 'mp_partnership_ai_messages',
    'chroma_collection', 'mp_partnership_ai',
    'collector_module', 'backend.sources.partnership_ai.collector',
    'region', 'US',
    'timezone', 'America/New_York',
    'language', 'en',
    'importance', 'low',
    'update_frequency', 'weekly',
    'relevance', 'high'
  ),
  '0 0 0 * * *',
  TRUE,
  NOW(),
  NOW()
) ON DUPLICATE KEY UPDATE
  `adapter_name` = VALUES(`adapter_name`),
  `category` = VALUES(`category`),
  `display_name` = VALUES(`display_name`),
  `config` = VALUES(`config`),
  `schedule` = VALUES(`schedule`),
  `is_active` = VALUES(`is_active`),
  `updated_at` = NOW();

-- 3. 验证注册结果
SELECT
  id,
  name,
  adapter_name,
  display_name,
  category,
  is_active,
  config
FROM mp_message_sources
WHERE name = 'partnership_ai';
