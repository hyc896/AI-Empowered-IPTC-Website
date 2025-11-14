-- 36氪快讯采集器注册SQL

-- 1. 创建kr36_messages表
CREATE TABLE IF NOT EXISTS `kr36_messages` (
  `id` VARCHAR(36) NOT NULL COMMENT '消息ID（UUID）',
  `source_id` VARCHAR(36) NOT NULL COMMENT '来源ID',
  `item_id` VARCHAR(50) NOT NULL COMMENT '36氪item_id（用于去重）',
  `title` VARCHAR(500) NOT NULL COMMENT '标题',
  `content` TEXT NOT NULL COMMENT '正文内容',
  `summary` TEXT COMMENT '摘要（直接使用content）',
  `published_at` DATETIME COMMENT '发布时间',
  `kr_route` VARCHAR(500) COMMENT '36氪页面路由',
  `source_url` VARCHAR(500) COMMENT '原文链接',
  `image_url` VARCHAR(1000) COMMENT '图片链接',
  `crawled_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
  `comment_count` INT DEFAULT 0 COMMENT '评论数',
  `has_relevant` BOOLEAN DEFAULT FALSE COMMENT '是否有相关内容',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_item_id` (`item_id`),
  KEY `idx_source_id` (`source_id`),
  KEY `idx_published_at` (`published_at`),
  KEY `idx_source_published` (`source_id`, `published_at`),
  KEY `idx_crawled_at` (`crawled_at`),
  CONSTRAINT `fk_kr36_messages_source` FOREIGN KEY (`source_id`) REFERENCES `message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='36氪快讯表';

-- 2. 注册消息源到message_sources表
INSERT INTO `message_sources` (
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
  'kr36',
  'kr36_collector',
  'newsflash',
  '36氪快讯',
  JSON_OBJECT(
    'url', 'https://www.36kr.com/newsflashes',
    'interval', 180,
    'mysql_table', 'kr36_messages',
    'chroma_collection', 'mp_kr36',
    'collector_module', 'backend.services.message.sources.kr36.collector'
  ),
  '0 */3 * * * *',
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
  is_active
FROM message_sources
WHERE name = 'kr36';
