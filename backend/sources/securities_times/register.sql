-- Securities Times (证券时报) 消息源注册SQL
-- 执行方式（PowerShell推荐）：
-- Get-Content backend/sources/securities_times/register.sql -Encoding UTF8 | mysql -h localhost -P 3306 -u root -p123456 --default-character-set=utf8mb4 message_platform

-- 1. 创建消息表
CREATE TABLE IF NOT EXISTS `mp_securities_times_messages` (
  `id` VARCHAR(36) NOT NULL COMMENT '消息ID（UUID）',
  `source_id` VARCHAR(36) NOT NULL COMMENT '来源ID',
  `external_id` VARCHAR(200) DEFAULT NULL COMMENT '外部唯一标识（从URL提取的文章ID，如3500937）',
  `title` VARCHAR(500) NOT NULL COMMENT '标题',
  `content` TEXT NOT NULL COMMENT '正文内容（从详情页提取）',
  `summary` TEXT DEFAULT NULL COMMENT '摘要（优先提取excerpt，否则用content前1000字）',
  `provider` VARCHAR(500) DEFAULT NULL COMMENT '作者（多个用逗号分隔，从byline提取）',
  `published_at` DATETIME DEFAULT NULL COMMENT '发布时间（格式：YYYY-MM-DD HH:MM）',
  `crawled_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
  `url` VARCHAR(500) NOT NULL COMMENT '原文链接（用于去重）',
  `region` VARCHAR(200) DEFAULT NULL COMMENT '地区（中文格式，从文章内容提取，如"中国"、"中国/广东省/深圳市"、"全球"等）',
  `industry_tags` TEXT DEFAULT NULL COMMENT '行业标签（逗号分隔，最多3个，如"金融,科技金融,人工智能"）',
  `ai_tag` VARCHAR(50) DEFAULT NULL COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',
  `category` VARCHAR(100) DEFAULT NULL COMMENT '文章分类（要闻/快讯/股市/公司等）',
  `language` VARCHAR(10) DEFAULT 'zh' COMMENT '语言（zh=中文）',
  `tags` JSON DEFAULT NULL COMMENT '标签列表（JSON数组，从页面提取）',
  `metadata` JSON DEFAULT NULL COMMENT '其他元数据（JSON对象）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_url` (`url`),
  KEY `idx_source_id` (`source_id`),
  KEY `idx_published_at` (`published_at`),
  KEY `idx_crawled_at` (`crawled_at`),
  KEY `idx_source_published` (`source_id`, `published_at`),
  KEY `idx_external_id` (`external_id`),
  KEY `idx_category` (`category`),
  KEY `idx_region` (`region`),
  KEY `idx_ai_tag` (`ai_tag`),
  CONSTRAINT `fk_securities_times_source` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='证券时报（Securities Times）财经新闻消息表';

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
  '证券时报',
  'securities_times',
  'news',
  '证券时报 (Securities Times)',
  JSON_OBJECT(
    'interval', 86400,
    'mysql_table', 'mp_securities_times_messages',
    'chroma_collection', 'securities_times',
    'collector_module', 'backend.sources.securities_times.collector',
    'categories', JSON_ARRAY('yw'),
    'region', 'CN',
    'language', 'zh',
    'description', '证券时报是中国证监会指定的信息披露媒体，报道财经新闻、股市行情、上市公司动态等'
  ),
  '0 0 */6 * * ?',
  1,
  NOW(),
  NOW()
);

-- 3. 验证注册结果
SELECT
  id,
  name,
  category,
  is_active,
  JSON_EXTRACT(config, '$.mysql_table') as mysql_table,
  JSON_EXTRACT(config, '$.chroma_collection') as chroma_collection,
  JSON_EXTRACT(config, '$.collector_module') as collector_module
FROM mp_message_sources
WHERE name = '证券时报';

-- 4. 验证表创建结果
SHOW CREATE TABLE mp_securities_times_messages;
