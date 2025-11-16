-- 消息平台数据库初始化脚本
-- 创建核心表结构

-- 1. 创建消息源配置表
CREATE TABLE IF NOT EXISTS `mp_message_sources` (
  `id` VARCHAR(36) NOT NULL COMMENT '消息源ID（UUID）',
  `name` VARCHAR(100) NOT NULL COMMENT '源名称',
  `adapter_name` VARCHAR(100) NOT NULL COMMENT '适配器名称',
  `category` VARCHAR(50) COMMENT '业务类别：news/wechat/rss等',
  `display_name` VARCHAR(100) COMMENT '显示名称',
  `config` JSON COMMENT '适配器配置（JSON格式）',
  `schedule` VARCHAR(50) COMMENT '定时任务cron表达式',
  `is_active` TINYINT(1) DEFAULT 1 COMMENT '是否启用',
  `last_crawled_at` DATETIME COMMENT '最后抓取时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='消息源配置表';

-- 2. 创建同花顺消息表
CREATE TABLE IF NOT EXISTS `mp_tonghuashun_messages` (
  `id` VARCHAR(36) NOT NULL COMMENT '消息ID（UUID）',
  `source_id` VARCHAR(36) NOT NULL COMMENT '来源ID',
  `seq` VARCHAR(50) NOT NULL COMMENT '同花顺seq（唯一标识）',
  `title` VARCHAR(500) NOT NULL COMMENT '标题',
  `content` TEXT NOT NULL COMMENT '正文内容',
  `summary` TEXT COMMENT '摘要',
  `digest` VARCHAR(500) COMMENT '摘要简短版',
  `url` VARCHAR(500) NOT NULL COMMENT '原文链接',
  `provider` VARCHAR(500) COMMENT '信息提供方',
  `image_url` VARCHAR(1000) COMMENT '图片链接',
  `published_at` DATETIME COMMENT '发布时间',
  `crawled_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
  `industry_tags` VARCHAR(500) COMMENT '行业标签（逗号分隔）',
  `region` VARCHAR(100) COMMENT '地区',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_url` (`url`),
  KEY `idx_seq` (`seq`),
  KEY `idx_source_id` (`source_id`),
  KEY `idx_published_at` (`published_at`),
  KEY `idx_source_published` (`source_id`, `published_at`),
  KEY `idx_crawled_at` (`crawled_at`),
  CONSTRAINT `fk_tonghuashun_source` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='同花顺消息表';

-- 3. 创建36氪消息表
CREATE TABLE IF NOT EXISTS `mp_kr36_messages` (
  `id` VARCHAR(36) NOT NULL COMMENT '消息ID（UUID）',
  `source_id` VARCHAR(36) NOT NULL COMMENT '来源ID',
  `item_id` VARCHAR(50) NOT NULL COMMENT '36氪item_id（用于去重）',
  `title` VARCHAR(500) NOT NULL COMMENT '标题',
  `content` TEXT NOT NULL COMMENT '正文内容',
  `summary` TEXT COMMENT '摘要',
  `published_at` DATETIME COMMENT '发布时间',
  `kr_route` VARCHAR(500) COMMENT '36氪页面路由',
  `source_url` VARCHAR(500) COMMENT '原文链接',
  `image_url` VARCHAR(1000) COMMENT '图片链接',
  `crawled_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
  `comment_count` INT DEFAULT 0 COMMENT '评论数',
  `has_relevant` TINYINT(1) DEFAULT 0 COMMENT '是否有相关内容',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_item_id` (`item_id`),
  KEY `idx_source_id` (`source_id`),
  KEY `idx_published_at` (`published_at`),
  KEY `idx_source_published` (`source_id`, `published_at`),
  KEY `idx_crawled_at` (`crawled_at`),
  CONSTRAINT `fk_kr36_source` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='36氪快讯表';

-- 4. 注册同花顺消息源
INSERT INTO `mp_message_sources` (
  `id`,
  `name`,
  `adapter_name`,
  `category`,
  `display_name`,
  `config`,
  `schedule`,
  `is_active`
) VALUES (
  UUID(),
  'tonghuashun',
  'tonghuashun_collector',
  'newsflash',
  '同花顺7x24快讯',
  JSON_OBJECT(
    'url', 'https://news.10jqka.com.cn/realtimenews.html',
    'interval', 15,
    'mysql_table', 'mp_tonghuashun_messages',
    'chroma_collection', 'mp_tonghuashun',
    'collector_module', 'backend.sources.tonghuashun.collector'
  ),
  '0 */1 * * * *',
  1
) ON DUPLICATE KEY UPDATE
  `adapter_name` = VALUES(`adapter_name`),
  `category` = VALUES(`category`),
  `display_name` = VALUES(`display_name`),
  `config` = VALUES(`config`),
  `schedule` = VALUES(`schedule`),
  `updated_at` = CURRENT_TIMESTAMP;

-- 5. 注册36氪消息源
INSERT INTO `mp_message_sources` (
  `id`,
  `name`,
  `adapter_name`,
  `category`,
  `display_name`,
  `config`,
  `schedule`,
  `is_active`
) VALUES (
  UUID(),
  'kr36',
  'kr36_collector',
  'newsflash',
  '36氪快讯',
  JSON_OBJECT(
    'url', 'https://www.36kr.com/newsflashes',
    'interval', 180,
    'mysql_table', 'mp_kr36_messages',
    'chroma_collection', 'mp_kr36',
    'collector_module', 'backend.sources.kr36.collector'
  ),
  '0 */3 * * * *',
  1
) ON DUPLICATE KEY UPDATE
  `adapter_name` = VALUES(`adapter_name`),
  `category` = VALUES(`category`),
  `display_name` = VALUES(`display_name`),
  `config` = VALUES(`config`),
  `schedule` = VALUES(`schedule`),
  `updated_at` = CURRENT_TIMESTAMP;

-- 验证结果
SELECT
  name,
  display_name,
  category,
  is_active,
  JSON_EXTRACT(config, '$.mysql_table') AS mysql_table,
  JSON_EXTRACT(config, '$.chroma_collection') AS chroma_collection
FROM mp_message_sources
ORDER BY name;
