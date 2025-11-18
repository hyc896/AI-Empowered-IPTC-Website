-- Bloomberg Technology 消息源注册脚本
-- 数据库：message_platform
-- 执行方式：PowerShell (推荐)
--   Get-Content backend/sources/bloomberg/register.sql -Encoding UTF8 | mysql -h localhost -P 3306 -u root -p123456 --default-character-set=utf8mb4 message_platform

-- ============================================================
-- 第一步：创建消息表
-- ============================================================
CREATE TABLE IF NOT EXISTS `mp_bloomberg_messages` (
    -- 核心必备字段（遵循2025统一标准）
    `id` VARCHAR(36) NOT NULL COMMENT '消息ID（UUID）',
    `source_id` VARCHAR(36) NOT NULL COMMENT '来源ID',
    `external_id` VARCHAR(200) NULL COMMENT '外部唯一标识（RSS的guid字段）',
    `title` VARCHAR(500) NOT NULL COMMENT '标题（RSS的title字段）',
    `content` TEXT NOT NULL COMMENT '正文内容（RSS的description字段）',
    `summary` TEXT NULL COMMENT '中文摘要（翻译后）',
    `provider` VARCHAR(500) NULL COMMENT '作者（RSS的dc:creator字段）',
    `published_at` DATETIME NULL COMMENT '发布时间（RSS的pubDate字段）',
    `crawled_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
    `url` VARCHAR(500) NOT NULL COMMENT '原文链接（RSS的link字段，用于去重）',

    -- 新增必备字段（2025年强制要求）
    `region` VARCHAR(200) NULL COMMENT '地区（中文格式，从文章内容提取，如"美国"、"全球"等）',
    `industry_tags` TEXT NULL COMMENT '行业标签（逗号分隔，最多3个，涉及AI必须包含"人工智能"标签）',
    `ai_tag` VARCHAR(50) NULL COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',

    -- 扩展字段
    `category` VARCHAR(100) NULL COMMENT '文章分类（RSS的category字段）',
    `language` VARCHAR(10) DEFAULT 'en' COMMENT '语言（en=英文）',
    `media_content` VARCHAR(500) NULL COMMENT '媒体内容URL（RSS的media:content字段）',
    `tags` JSON NULL COMMENT '标签列表（JSON数组）',
    `metadata` JSON NULL COMMENT '其他元数据（JSON对象）',

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

    CONSTRAINT `fk_bloomberg_source_id`
        FOREIGN KEY (`source_id`)
        REFERENCES `mp_message_sources`(`id`)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Bloomberg Technology科技新闻消息表（基于RSS Feed采集）';

-- ============================================================
-- 第二步：注册消息源
-- ============================================================
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
    'Bloomberg Technology',
    'bloomberg',
    'news',
    'Bloomberg Technology',
    JSON_OBJECT(
        'collector_module', 'backend.sources.bloomberg.collector',
        'mysql_table', 'mp_bloomberg_messages',
        'chroma_collection', 'bloomberg_tech',
        'region', '全球',
        'language', 'en',
        'rss_url', 'https://feeds.bloomberg.com/technology/news.rss',
        'description', 'Bloomberg Technology科技新闻RSS源'
    ),
    '0 */2 * * *',
    1,
    NOW(),
    NOW()
);

-- ============================================================
-- 验证注册成功
-- ============================================================
-- 查看表结构
SHOW CREATE TABLE `mp_bloomberg_messages`;

-- 查看消息源注册信息
SELECT
    id,
    name,
    adapter_name,
    category,
    display_name,
    is_active,
    JSON_EXTRACT(config, '$.mysql_table') AS mysql_table,
    JSON_EXTRACT(config, '$.chroma_collection') AS chroma_collection,
    JSON_EXTRACT(config, '$.collector_module') AS collector_module,
    created_at
FROM `mp_message_sources`
WHERE name = 'Bloomberg Technology';
