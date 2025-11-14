-- ==========================================
-- IEAI (Institute for Ethics in AI) 消息源注册脚本
-- 德国慕尼黑技术大学AI伦理研究所
-- ==========================================

-- 1. 创建消息表
CREATE TABLE IF NOT EXISTS `mp_ieai_messages` (
  `id` varchar(36) NOT NULL COMMENT '消息ID（UUID）',
  `source_id` varchar(36) NOT NULL COMMENT '来源ID',
  `external_id` varchar(200) DEFAULT NULL COMMENT '外部唯一标识（从URL路径提取slug）',
  `title` varchar(500) NOT NULL COMMENT '标题',
  `content` text NOT NULL COMMENT '正文内容（完整文章内容）',
  `summary` text COMMENT '中文摘要（翻译后）',
  `provider` varchar(500) DEFAULT NULL COMMENT '作者（多个用逗号分隔）',
  `published_at` datetime DEFAULT NULL COMMENT '发布时间',
  `crawled_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
  `url` varchar(500) NOT NULL COMMENT '原文链接（用于去重）',
  `region` varchar(50) DEFAULT 'DE' COMMENT '地区（DE=Germany）',
  `category` varchar(100) DEFAULT NULL COMMENT '文章类型（News/Blog/Research等）',
  `language` varchar(10) DEFAULT 'en' COMMENT '语言（en）',
  `tags` json DEFAULT NULL COMMENT '标签列表（如AI Ethics、Cognitive Science等）',
  `metadata` json DEFAULT NULL COMMENT '其他元数据（JSON对象）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `url` (`url`),
  KEY `idx_source_id` (`source_id`),
  KEY `idx_published_at` (`published_at`),
  KEY `idx_crawled_at` (`crawled_at`),
  KEY `idx_source_published` (`source_id`,`published_at`),
  KEY `idx_external_id` (`external_id`),
  KEY `idx_category` (`category`),
  CONSTRAINT `fk_ieai_source_id` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='IEAI（德国慕尼黑技术大学AI伦理研究所）文章表';

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
    'ieai',
    'IEAICollector',
    'news',
    'IEAI - AI伦理研究',
    JSON_OBJECT(
        'url', 'https://www.ieai.sot.tum.de/news/',
        'region', 'DE',
        'language', 'en',
        'timezone', 'Europe/Berlin',
        'mysql_table', 'mp_ieai_messages',
        'chroma_collection', 'ieai',
        'collector_module', 'backend.sources.ieai.collector',
        'interval', 86400
    ),
    '0 3 * * *',
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
WHERE name = 'ieai';

-- 4. 检查表结构
SHOW CREATE TABLE mp_ieai_messages;

-- ==========================================
-- 注册完成提示
-- ==========================================
-- 执行完成后，请检查：
-- 1. mp_ieai_messages 表已创建
-- 2. mp_message_sources 表中已有 ieai 记录
-- 3. is_active = 1 表示已启用
-- 4. 表的 COMMENT 字段未出现乱码（中文正常显示）
-- ==========================================
