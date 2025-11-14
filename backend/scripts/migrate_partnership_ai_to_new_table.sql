-- 迁移Partnership on AI数据到新表
-- 执行前请备份数据库！

USE message_platform;

-- 1. 创建新表mp_partnership_ai_messages
CREATE TABLE IF NOT EXISTS `mp_partnership_ai_messages` (
  `id` VARCHAR(36) NOT NULL COMMENT '消息ID（UUID）',
  `source_id` VARCHAR(36) NOT NULL COMMENT '来源ID',
  `external_id` VARCHAR(200) COMMENT '外部唯一标识（文章slug）',
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
  KEY `idx_category` (`category`),
  CONSTRAINT `fk_partnership_ai_source` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Partnership on AI博客消息表（2025统一字段标准）';

-- 2. 迁移现有数据from mp_international_messages
INSERT INTO `mp_partnership_ai_messages` (
  `id`, `source_id`, `external_id`, `title`, `content`, `summary`,
  `provider`, `published_at`, `crawled_at`, `url`,
  `region`, `category`, `language`, `tags`, `metadata`
)
SELECT
  `id`, `source_id`, `external_id`, `title`, `content`, `summary`,
  `provider`, `published_at`, `crawled_at`, `url`,
  `region`, `category`, `language`, `tags`, `metadata`
FROM `mp_international_messages`
WHERE `source_id` = (
  SELECT `id` FROM `mp_message_sources` WHERE `name` = 'partnership_ai' LIMIT 1
);

-- 3. 更新消息源配置
UPDATE `mp_message_sources`
SET `config` = JSON_SET(
  `config`,
  '$.mysql_table', 'mp_partnership_ai_messages'
)
WHERE `name` = 'partnership_ai';

-- 4. 验证迁移结果
SELECT
  '迁移完成' AS status,
  COUNT(*) AS migrated_records,
  MIN(published_at) AS earliest_date,
  MAX(published_at) AS latest_date
FROM `mp_partnership_ai_messages`;

-- 5. 验证配置更新
SELECT
  name,
  adapter_name,
  JSON_UNQUOTE(JSON_EXTRACT(config, '$.mysql_table')) AS mysql_table,
  JSON_UNQUOTE(JSON_EXTRACT(config, '$.chroma_collection')) AS chroma_collection
FROM `mp_message_sources`
WHERE name = 'partnership_ai';

-- 6. 【可选】删除旧表中的Partnership on AI数据
-- DELETE FROM `mp_international_messages`
-- WHERE `source_id` = (
--   SELECT `id` FROM `mp_message_sources` WHERE `name` = 'partnership_ai' LIMIT 1
-- );
