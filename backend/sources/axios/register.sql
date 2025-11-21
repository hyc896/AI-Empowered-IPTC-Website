-- Axios新闻源注册脚本
-- RSS Feed: https://api.axios.com/feed/

-- 1. 创建消息表
CREATE TABLE IF NOT EXISTS `mp_axios_messages` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '消息ID（UUID）',
  `source_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '来源ID',
  `external_id` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '外部唯一标识（RSS的guid字段）',
  `title` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '标题（RSS的title字段）',
  `content` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '正文内容（RSS的description字段）',
  `summary` text COLLATE utf8mb4_unicode_ci COMMENT '中文摘要（翻译后）',
  `provider` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '作者（RSS的author字段）',
  `published_at` datetime DEFAULT NULL COMMENT '发布时间（RSS的pubDate字段）',
  `crawled_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
  `url` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '原文链接（RSS的link字段，用于去重）',
  `region` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '地区（中文格式，从文章内容提取，如"美国"、"全球"等）',
  `industry_tags` text COLLATE utf8mb4_unicode_ci COMMENT '行业标签（逗号分隔，最多3个，涉及AI必须包含"人工智能"标签）',
  `ai_tag` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',
  `category` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '文章分类（RSS的category字段）',
  `language` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT 'en' COMMENT '语言（en=英文）',
  `media_content` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '媒体内容URL（RSS的media:content字段）',
  `tags` json DEFAULT NULL COMMENT '标签列表（JSON数组）',
  `metadata` json DEFAULT NULL COMMENT '其他元数据（JSON对象）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `url` (`url`),
  KEY `idx_source_id` (`source_id`),
  KEY `idx_published_at` (`published_at`),
  KEY `idx_crawled_at` (`crawled_at`),
  KEY `idx_source_published` (`source_id`,`published_at`),
  KEY `idx_external_id` (`external_id`),
  KEY `idx_category` (`category`),
  KEY `idx_region` (`region`),
  KEY `idx_ai_tag` (`ai_tag`),
  CONSTRAINT `mp_axios_messages_ibfk_1` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Axios新闻消息表（基于RSS Feed采集）';

-- 2. 注册消息源到mp_message_sources表
INSERT INTO `mp_message_sources` (`id`, `name`, `adapter_name`, `category`, `display_name`, `config`, `schedule`, `is_active`, `created_at`, `updated_at`)
VALUES (
  UUID(),
  'axios',
  'axios',
  'news',
  'Axios新闻',
  JSON_OBJECT(
    'mysql_table', 'mp_axios_messages',
    'chroma_collection', 'axios_news',
    'collector_module', 'backend.sources.axios.collector',
    'region', '美国',
    'language', 'en'
  ),
  '0 */1 * * *',
  1,
  NOW(),
  NOW()
);
