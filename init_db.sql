-- ============================================================================
-- Message Platform Database Initialization Script
-- 消息平台数据库初始化脚本
--
-- 用法:
--   mysql -u root -p < init_db.sql
-- ============================================================================

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS `message_platform`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `message_platform`;

-- 禁用外键检查
SET FOREIGN_KEY_CHECKS = 0;
SET NAMES utf8mb4;

-- ============================================================================
-- 删除所有表（先删子表，后删父表）
-- ============================================================================
DROP TABLE IF EXISTS `mp_ars_technica_messages`;
DROP TABLE IF EXISTS `mp_arxiv_messages`;
DROP TABLE IF EXISTS `mp_axios_messages`;
DROP TABLE IF EXISTS `mp_betakit_messages`;
DROP TABLE IF EXISTS `mp_bloomberg_messages`;
DROP TABLE IF EXISTS `mp_cnbc_messages`;
DROP TABLE IF EXISTS `mp_der_spiegel_messages`;
DROP TABLE IF EXISTS `mp_financial_times_messages`;
DROP TABLE IF EXISTS `mp_gcg_ai_messages`;
DROP TABLE IF EXISTS `mp_govai_messages`;
DROP TABLE IF EXISTS `mp_guardian_messages`;
DROP TABLE IF EXISTS `mp_inteligencia_argentina_messages`;
DROP TABLE IF EXISTS `mp_investing_com_messages`;
DROP TABLE IF EXISTS `mp_kr36_messages`;
DROP TABLE IF EXISTS `mp_lanacion_messages`;
DROP TABLE IF EXISTS `mp_le_monde_messages`;
DROP TABLE IF EXISTS `mp_nikkei_asia_ai_messages`;
DROP TABLE IF EXISTS `mp_partnership_ai_messages`;
DROP TABLE IF EXISTS `mp_securities_times_messages`;
DROP TABLE IF EXISTS `mp_techcrunch_messages`;
DROP TABLE IF EXISTS `mp_techinasia_messages`;
DROP TABLE IF EXISTS `mp_the_hindu_messages`;
DROP TABLE IF EXISTS `mp_times_of_india_messages`;
DROP TABLE IF EXISTS `mp_tonghuashun_messages`;
DROP TABLE IF EXISTS `mp_venturebeat_messages`;
DROP TABLE IF EXISTS `mp_wired_messages`;
DROP TABLE IF EXISTS `mp_wsj_messages`;
DROP TABLE IF EXISTS `mp_ai_daily_reports`;
DROP TABLE IF EXISTS `mp_message_sources`;


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mp_message_sources` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '消息源ID（UUID）',
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '源名称',
  `adapter_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '适配器名称',
  `category` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '业务类别：news/wechat/rss等',
  `display_name` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '显示名称',
  `config` json DEFAULT NULL COMMENT '适配器配置（JSON格式）',
  `schedule` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '定时任务cron表达式',
  `is_active` tinyint(1) DEFAULT '1' COMMENT '是否启用',
  `last_crawled_at` datetime DEFAULT NULL COMMENT '最后抓取时间',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `idx_is_active` (`is_active`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_category` (`category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mp_ai_daily_reports` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'UUID主键',
  `report_date` date NOT NULL COMMENT '报告日期（YYYY-MM-DD）',
  `content` longtext COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '日报Markdown内容',
  `statistics` json NOT NULL COMMENT '统计数据（消息数量、地区分布等）',
  `governance_count` int NOT NULL DEFAULT '0' COMMENT 'AI治理信息数量',
  `research_count` int NOT NULL DEFAULT '0' COMMENT 'AI科研信息数量',
  `industry_count` int NOT NULL DEFAULT '0' COMMENT 'AI产业信息数量',
  `total_messages` int NOT NULL DEFAULT '0' COMMENT '总消息数量',
  `generation_status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending' COMMENT '生成状态（pending/success/failed）',
  `error_message` text COLLATE utf8mb4_unicode_ci COMMENT '错误信息（生成失败时记录）',
  `generated_at` datetime NOT NULL COMMENT '生成时间',
  `model_version` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'LLM模型版本',
  `report_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'comprehensive' COMMENT '报告类型（comprehensive/governance/research/industry）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_report_date_type` (`report_date`,`report_type`),
  KEY `idx_generated_at` (`generated_at`),
  KEY `idx_status` (`generation_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI日报表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mp_ars_technica_messages` (
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
  `region` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '地区（中文格式，从文章内容提取）',
  `industry_tags` text COLLATE utf8mb4_unicode_ci COMMENT '行业标签（逗号分隔，最多3个，涉及AI必须包含"人工智能"标签）',
  `ai_tag` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',
  `category` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '文章分类',
  `language` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT 'en' COMMENT '语言',
  `media_content` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '媒体内容URL（RSS的media:content字段）',
  `tags` json DEFAULT NULL COMMENT '标签列表（JSON数组）',
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
  KEY `idx_region` (`region`),
  KEY `idx_ai_tag` (`ai_tag`),
  CONSTRAINT `mp_ars_technica_messages_ibfk_1` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Ars Technica消息表（RSS Feed采集）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mp_arxiv_messages` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '消息ID（UUID）',
  `source_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '来源ID',
  `arxiv_id` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'arXiv ID（用于去重）',
  `title` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '标题',
  `content` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '摘要（Abstract）',
  `summary` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '展示摘要（<1000字=content，>=1000字LLM生成）',
  `provider` text COLLATE utf8mb4_unicode_ci COMMENT '所有作者逗号分隔（无作者时=Anonymous）',
  `published_at` datetime DEFAULT NULL COMMENT '发布时间',
  `url` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '论文详情页（用于去重）',
  `primary_category` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '主分类',
  `categories` json DEFAULT NULL COMMENT '所有分类数组',
  `doi` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'DOI',
  `journal_ref` text COLLATE utf8mb4_unicode_ci COMMENT '期刊引用',
  `comment` text COLLATE utf8mb4_unicode_ci COMMENT '评论',
  `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
  `crawled_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
  `industry_tags` text COLLATE utf8mb4_unicode_ci COMMENT '行业标签（固定为人工智能）',
  `ai_tag` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'AI分类标签（固定为AI科研信息）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `arxiv_id` (`arxiv_id`),
  UNIQUE KEY `url` (`url`),
  KEY `idx_source_id` (`source_id`),
  KEY `idx_published_at` (`published_at`),
  KEY `idx_source_published` (`source_id`,`published_at`),
  KEY `idx_crawled_at` (`crawled_at`),
  KEY `idx_arxiv_id` (`arxiv_id`),
  KEY `idx_primary_category` (`primary_category`),
  KEY `idx_doi` (`doi`),
  KEY `idx_updated_at` (`updated_at`),
  KEY `idx_ai_tag` (`ai_tag`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mp_axios_messages` (
  `id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '消息ID（UUID）',
  `source_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '来源ID',
  `external_id` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '外部唯一标识（RSS的guid字段）',
  `title` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '标题（RSS的title字段）',
  `content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '正文内容（RSS的description字段）',
  `summary` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '中文摘要（翻译后）',
  `provider` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '作者（RSS的author字段）',
  `published_at` datetime DEFAULT NULL COMMENT '发布时间（RSS的pubDate字段）',
  `crawled_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
  `url` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '原文链接（RSS的link字段，用于去重）',
  `region` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '地区（中文格式，从文章内容提取，如"美国"、"全球"等）',
  `industry_tags` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '行业标签（逗号分隔，最多3个，涉及AI必须包含"人工智能"标签）',
  `ai_tag` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',
  `category` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '文章分类',
  `language` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'en' COMMENT '语言（en=英文）',
  `media_content` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '媒体内容URL（RSS的media:content字段）',
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
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mp_betakit_messages` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '消息ID（UUID）',
  `source_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '来源ID',
  `external_id` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '外部唯一标识（从RSS guid提取的post ID或URL slug）',
  `title` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '标题',
  `content` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '正文内容（从RSS content:encoded清理HTML后提取）',
  `summary` text COLLATE utf8mb4_unicode_ci COMMENT '摘要（中文翻译，来自RSS description）',
  `provider` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '作者（RSS dc:creator字段）',
  `published_at` datetime DEFAULT NULL COMMENT '发布时间（RSS pubDate字段）',
  `crawled_at` datetime NOT NULL COMMENT '抓取时间',
  `url` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '原文链接（用于去重）',
  `region` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '地区（中文格式，主要为''加拿大''或''加拿大/省份''）',
  `industry_tags` text COLLATE utf8mb4_unicode_ci COMMENT '行业标签（逗号分隔，最多3个）',
  `ai_tag` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',
  `category` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '分类（ai/machine-learning/funding/startups等）',
  `language` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '语言（en，可能包含法语）',
  `tags` json DEFAULT NULL COMMENT 'RSS category标签列表（JSON数组）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `url` (`url`),
  KEY `idx_ai_tag` (`ai_tag`),
  KEY `idx_external_id` (`external_id`),
  KEY `idx_crawled_at` (`crawled_at`),
  KEY `idx_category` (`category`),
  KEY `idx_source_published` (`source_id`,`published_at`),
  KEY `idx_source_id` (`source_id`),
  KEY `idx_region` (`region`),
  KEY `idx_url` (`url`),
  KEY `idx_published_at` (`published_at`),
  CONSTRAINT `mp_betakit_messages_ibfk_1` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mp_bloomberg_messages` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '消息ID（UUID）',
  `source_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '来源ID',
  `external_id` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '外部唯一标识（RSS的guid字段）',
  `title` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '标题（RSS的title字段）',
  `content` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '正文内容（RSS的description字段）',
  `summary` text COLLATE utf8mb4_unicode_ci COMMENT '中文摘要（翻译后）',
  `provider` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '作者（RSS的dc:creator字段）',
  `published_at` datetime DEFAULT NULL COMMENT '发布时间（RSS的pubDate字段）',
  `crawled_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
  `url` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '原文链接（RSS的link字段，用于去重）',
  `region` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '地区（中文格式，从文章内容提取，如"美国"、"全球"等）',
  `industry_tags` text COLLATE utf8mb4_unicode_ci COMMENT '行业标签（逗号分隔，最多3个，涉及AI必须包含"人工智能"标签）',
  `ai_tag` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',
  `category` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '文章分类',
  `language` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT 'en' COMMENT '语言（en=英文）',
  `media_content` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '媒体内容URL（RSS的media:content字段）',
  `tags` json DEFAULT NULL COMMENT '标签列表（JSON数组）',
  `metadata` json DEFAULT NULL COMMENT '其他元数据（JSON对象）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_url` (`url`),
  KEY `idx_source_id` (`source_id`),
  KEY `idx_published_at` (`published_at`),
  KEY `idx_crawled_at` (`crawled_at`),
  KEY `idx_source_published` (`source_id`,`published_at`),
  KEY `idx_external_id` (`external_id`),
  KEY `idx_category` (`category`),
  KEY `idx_region` (`region`),
  KEY `idx_ai_tag` (`ai_tag`),
  CONSTRAINT `fk_bloomberg_source_id` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Bloomberg Technology科技新闻消息表（基于RSS Feed采集）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mp_cnbc_messages` (
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
  `region` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '地区（中文格式，从文章内容提取）',
  `industry_tags` text COLLATE utf8mb4_unicode_ci COMMENT '行业标签（逗号分隔，最多3个，涉及AI必须包含"人工智能"标签）',
  `ai_tag` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',
  `category` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '文章分类',
  `language` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT 'en' COMMENT '语言',
  `media_content` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '媒体内容URL（RSS的media:content字段）',
  `tags` json DEFAULT NULL COMMENT '标签列表（JSON数组）',
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
  KEY `idx_region` (`region`),
  KEY `idx_ai_tag` (`ai_tag`),
  CONSTRAINT `mp_cnbc_messages_ibfk_1` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='CNBC Technology消息表（RSS Feed采集）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mp_der_spiegel_messages` (
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
  `region` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '地区（中文格式，从文章内容提取）',
  `industry_tags` text COLLATE utf8mb4_unicode_ci COMMENT '行业标签（逗号分隔，最多3个，涉及AI必须包含"人工智能"标签）',
  `ai_tag` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',
  `category` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '文章分类',
  `language` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT 'de' COMMENT '语言',
  `media_content` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '媒体内容URL（RSS的media:content字段）',
  `tags` json DEFAULT NULL COMMENT '标签列表（JSON数组）',
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
  KEY `idx_region` (`region`),
  KEY `idx_ai_tag` (`ai_tag`),
  CONSTRAINT `mp_der_spiegel_messages_ibfk_1` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Der Spiegel Netzwelt消息表（RSS Feed采集）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mp_financial_times_messages` (
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
  `region` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '地区（中文格式，从文章内容提取）',
  `industry_tags` text COLLATE utf8mb4_unicode_ci COMMENT '行业标签（逗号分隔，最多3个，涉及AI必须包含"人工智能"标签）',
  `ai_tag` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',
  `category` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '文章分类',
  `language` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT 'en' COMMENT '语言',
  `media_content` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '媒体内容URL（RSS的media:content字段）',
  `tags` json DEFAULT NULL COMMENT '标签列表（JSON数组）',
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
  KEY `idx_region` (`region`),
  KEY `idx_ai_tag` (`ai_tag`),
  CONSTRAINT `mp_financial_times_messages_ibfk_1` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Financial Times Technology消息表（RSS Feed采集）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mp_gcg_ai_messages` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '消息ID（UUID）',
  `source_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '来源ID',
  `external_id` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '外部唯一标识（从URL路径提取slug）',
  `title` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '标题',
  `content` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '正文内容（从详情页提取的简介）',
  `summary` text COLLATE utf8mb4_unicode_ci COMMENT '中文摘要（翻译后）',
  `provider` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '作者（多个用逗号分隔）',
  `published_at` datetime DEFAULT NULL COMMENT '发布时间',
  `crawled_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
  `url` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '原文链接（用于去重）',
  `region` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT 'ZA' COMMENT '地区（ZA=South Africa/Africa 南非/非洲）',
  `category` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '出版物类型（Policy Brief/Report/Article/Analysis/Toolkit等）',
  `language` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT 'en' COMMENT '语言（en）',
  `tags` json DEFAULT NULL COMMENT '标签列表（如Technology、Public Policy等）',
  `industry_tags` text COLLATE utf8mb4_unicode_ci COMMENT '行业标签（逗号分隔，最多3个）',
  `ai_tag` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',
  `pdf_url` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'PDF下载链接（如果有）',
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
  KEY `idx_ai_tag` (`ai_tag`),
  CONSTRAINT `fk_gcg_ai_source` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='GCG AI治理研究中心文章表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mp_govai_messages` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '消息ID（UUID）',
  `source_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '来源ID',
  `external_id` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `title` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '论文标题',
  `content` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '论文摘要/正文内容',
  `summary` text COLLATE utf8mb4_unicode_ci COMMENT '中文摘要（翻译后）',
  `provider` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '作者列表（逗号分隔）',
  `published_at` datetime DEFAULT NULL COMMENT '发布时间',
  `crawled_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
  `url` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '论文链接（用于去重）',
  `region` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT 'GLOBAL' COMMENT '地区（GLOBAL）',
  `category` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '研究分类（Survey Research/Technical AI Governance等）',
  `language` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT 'en' COMMENT '语言（en）',
  `industry_tags` text COLLATE utf8mb4_unicode_ci COMMENT '行业标签（逗号分隔，最多3个）',
  `ai_tag` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',
  `metadata` json DEFAULT NULL COMMENT '其他元数据（JSON对象）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_url` (`url`),
  KEY `idx_source_id` (`source_id`),
  KEY `idx_published_at` (`published_at`),
  KEY `idx_crawled_at` (`crawled_at`),
  KEY `idx_source_published` (`source_id`,`published_at`),
  KEY `idx_external_id` (`external_id`),
  KEY `idx_category` (`category`),
  KEY `idx_ai_tag` (`ai_tag`),
  CONSTRAINT `fk_govai_source` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='GovAI研究论文表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mp_guardian_messages` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '消息ID（UUID）',
  `source_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '来源ID',
  `external_id` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '外部唯一标识（RSS guid）',
  `title` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '标题',
  `content` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '正文内容（RSS description或summary）',
  `summary` text COLLATE utf8mb4_unicode_ci COMMENT '摘要（中文翻译）',
  `provider` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '作者（多个用逗号分隔）',
  `published_at` datetime DEFAULT NULL COMMENT '发布时间',
  `crawled_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
  `url` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '原文链接（用于去重）',
  `region` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '地区（中文格式，如英国、全球等）',
  `industry_tags` text COLLATE utf8mb4_unicode_ci COMMENT '行业标签（逗号分隔，最多3个）',
  `ai_tag` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',
  `category` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '分类（AI/Technology/Security等）',
  `language` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT 'en' COMMENT '语言（en）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `url` (`url`),
  KEY `idx_source_id` (`source_id`),
  KEY `idx_published_at` (`published_at`),
  KEY `idx_crawled_at` (`crawled_at`),
  KEY `idx_source_published` (`source_id`,`published_at`),
  KEY `idx_url` (`url`),
  KEY `idx_external_id` (`external_id`),
  KEY `idx_category` (`category`),
  KEY `idx_region` (`region`),
  CONSTRAINT `mp_guardian_messages_ibfk_1` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='The Guardian AI与科技新闻消息表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mp_inteligencia_argentina_messages` (
  `id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '消息ID（UUID）',
  `source_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '来源ID',
  `external_id` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '外部唯一标识（从URL提取slug）',
  `title` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '标题',
  `content` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '正文内容（从详情页提取的完整文章）',
  `summary` text COLLATE utf8mb4_unicode_ci COMMENT '中文摘要（翻译后）',
  `provider` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '作者',
  `published_at` datetime DEFAULT NULL COMMENT '发布时间',
  `crawled_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
  `url` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '原文链接（用于去重）',
  `region` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '地区（中文格式，如阿根廷、阿根廷/布宜诺斯艾利斯、全球等）',
  `industry_tags` text COLLATE utf8mb4_unicode_ci COMMENT '行业标签（逗号分隔，最多3个，涉及AI必须包含人工智能标签）',
  `ai_tag` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',
  `category` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT 'inteligencia-artificial' COMMENT '文章分类（固定为AI类）',
  `language` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT 'es' COMMENT '语言（西班牙语）',
  `excerpt` text COLLATE utf8mb4_unicode_ci COMMENT '摘要（从列表页提取的excerpt）',
  `tags` json DEFAULT NULL COMMENT '标签列表（JSON数组）',
  `metadata` json DEFAULT NULL COMMENT '其他元数据（JSON对象）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `url` (`url`),
  KEY `idx_source_id` (`source_id`),
  KEY `idx_published_at` (`published_at`),
  KEY `idx_crawled_at` (`crawled_at`),
  KEY `idx_source_published` (`source_id`,`published_at`),
  KEY `idx_url` (`url`),
  KEY `idx_external_id` (`external_id`),
  KEY `idx_region` (`region`),
  KEY `idx_ai_tag` (`ai_tag`),
  CONSTRAINT `fk_inteligencia_argentina_source` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Inteligencia Argentina AI分类消息表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mp_investing_com_messages` (
  `id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '消息ID（UUID）',
  `source_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '来源ID',
  `external_id` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '外部唯一标识（RSS guid）',
  `title` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '标题',
  `content` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '正文内容（description）',
  `summary` text COLLATE utf8mb4_unicode_ci COMMENT '摘要（同content）',
  `provider` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '信息提供方（固定为Investing.com）',
  `published_at` datetime DEFAULT NULL COMMENT '发布时间（pubDate）',
  `crawled_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
  `url` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '原文链接（用于去重）',
  `region` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '地区（中文格式，如"美国"、"全球"等）',
  `industry_tags` text COLLATE utf8mb4_unicode_ci COMMENT '行业标签（逗号分隔，最多3个）',
  `ai_tag` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',
  `category` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '分类（General News）',
  `language` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT 'en' COMMENT '语言（en）',
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
  KEY `idx_region` (`region`),
  KEY `idx_ai_tag` (`ai_tag`),
  KEY `idx_ai_tag_published` (`ai_tag`,`published_at`),
  CONSTRAINT `mp_investing_com_messages_ibfk_1` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Investing.com General News（全球金融市场综合新闻）消息表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mp_kr36_messages` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '消息ID（UUID）',
  `source_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '来源ID',
  `item_id` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '36氪item_id（用于去重）',
  `title` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '标题',
  `content` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '正文内容',
  `summary` text COLLATE utf8mb4_unicode_ci COMMENT '摘要（直接使用content）',
  `published_at` datetime DEFAULT NULL COMMENT '发布时间',
  `kr_route` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '36氪页面路由',
  `source_url` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '原文链接',
  `image_url` text COLLATE utf8mb4_unicode_ci COMMENT '图片链接',
  `crawled_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
  `comment_count` int DEFAULT '0' COMMENT '评论数',
  `has_relevant` tinyint(1) DEFAULT '0' COMMENT '是否相关',
  `region` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '地区（国家/省份/城市，斜杠分隔）',
  `industry_tags` text COLLATE utf8mb4_unicode_ci COMMENT '行业标签（逗号分隔，最多3个）',
  `ai_tag` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `item_id` (`item_id`),
  KEY `idx_source_id` (`source_id`),
  KEY `idx_published_at` (`published_at`),
  KEY `idx_source_published` (`source_id`,`published_at`),
  KEY `idx_crawled_at` (`crawled_at`),
  KEY `idx_item_id` (`item_id`),
  KEY `idx_source_url` (`source_url`),
  KEY `idx_region` (`region`),
  KEY `idx_industry_tags` (`industry_tags`(100)),
  KEY `idx_ai_tag` (`ai_tag`),
  KEY `idx_ai_tag_published` (`ai_tag`,`published_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mp_lanacion_messages` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '消息ID（UUID）',
  `source_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '来源ID',
  `external_id` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '外部唯一标识（从URL提取，如nid12345）',
  `title` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '标题（中文翻译）',
  `content` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '正文内容（中文翻译）',
  `summary` text COLLATE utf8mb4_unicode_ci COMMENT '摘要（中文翻译）',
  `provider` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '作者',
  `published_at` datetime DEFAULT NULL COMMENT '发布时间',
  `crawled_at` datetime NOT NULL COMMENT '抓取时间',
  `url` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '原文链接（用于去重）',
  `region` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '地区（中文格式，默认''阿根廷''，通过FieldEnricher动态提取）',
  `industry_tags` text COLLATE utf8mb4_unicode_ci COMMENT '行业标签（逗号分隔，最多3个，涉及AI必须包含''人工智能''标签）',
  `ai_tag` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',
  `language` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '原始语言（西班牙语）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `url` (`url`),
  KEY `idx_region` (`region`),
  KEY `idx_source_published` (`source_id`,`published_at`),
  KEY `idx_source_id` (`source_id`),
  KEY `idx_ai_tag` (`ai_tag`),
  KEY `idx_url` (`url`),
  KEY `idx_published_at` (`published_at`),
  KEY `idx_external_id` (`external_id`),
  KEY `idx_crawled_at` (`crawled_at`),
  CONSTRAINT `mp_lanacion_messages_ibfk_1` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mp_le_monde_messages` (
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
  `region` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '地区（中文格式，从文章内容提取）',
  `industry_tags` text COLLATE utf8mb4_unicode_ci COMMENT '行业标签（逗号分隔，最多3个，涉及AI必须包含"人工智能"标签）',
  `ai_tag` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',
  `category` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '文章分类',
  `language` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT 'fr' COMMENT '语言',
  `media_content` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '媒体内容URL（RSS的media:content字段）',
  `tags` json DEFAULT NULL COMMENT '标签列表（JSON数组）',
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
  KEY `idx_region` (`region`),
  KEY `idx_ai_tag` (`ai_tag`),
  CONSTRAINT `mp_le_monde_messages_ibfk_1` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Le Monde Pixels消息表（RSS Feed采集）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mp_nikkei_asia_ai_messages` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '消息ID（UUID）',
  `source_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '来源ID',
  `external_id` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '外部唯一标识（文章ID或slug）',
  `title` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '标题',
  `content` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '正文内容（subhead描述）',
  `summary` text COLLATE utf8mb4_unicode_ci COMMENT '中文摘要（翻译后）',
  `provider` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '作者',
  `published_at` datetime DEFAULT NULL COMMENT '发布时间',
  `crawled_at` datetime NOT NULL COMMENT '抓取时间',
  `url` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '原文链接（用于去重）',
  `region` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '地区',
  `category` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '分类',
  `language` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '语言',
  `industry_tags` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '行业标签',
  `ai_tag` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'AI分类标签',
  `metadata` json DEFAULT NULL COMMENT '其他元数据',
  PRIMARY KEY (`id`),
  UNIQUE KEY `url` (`url`),
  KEY `idx_external_id` (`external_id`),
  KEY `idx_crawled_at` (`crawled_at`),
  KEY `idx_category` (`category`),
  KEY `idx_source_published` (`source_id`,`published_at`),
  KEY `idx_source_id` (`source_id`),
  KEY `idx_url` (`url`),
  KEY `idx_published_at` (`published_at`),
  KEY `idx_ai_tag` (`ai_tag`),
  KEY `idx_ai_tag_published` (`ai_tag`,`published_at`),
  CONSTRAINT `mp_nikkei_asia_ai_messages_ibfk_1` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mp_partnership_ai_messages` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '娑堟伅ID锛圲UID锛',
  `source_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '鏉ユ簮ID',
  `external_id` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '澶栭儴鍞?竴鏍囪瘑锛堟枃绔爏lug锛',
  `title` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '鏍囬?',
  `content` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '姝ｆ枃鍐呭?',
  `summary` text COLLATE utf8mb4_unicode_ci COMMENT '鎽樿?锛堜紭鍏堜粠缃戦〉鎻愬彇锛屾棤鍒欑敤content锛宑ontent>1000瀛楁椂鍙栧墠1000瀛楋級',
  `provider` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '浣滆?鎴栦俊鎭?彁渚涙柟锛堝?涓?敤閫楀彿鍒嗛殧锛',
  `published_at` datetime DEFAULT NULL COMMENT '鍙戝竷鏃堕棿',
  `crawled_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '鎶撳彇鏃堕棿',
  `url` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '鍘熸枃閾炬帴锛堢敤浜庡幓閲嶏級',
  `region` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '鍦板尯锛圲S/EU/UK/GLOBAL绛夛級',
  `industry_tags` text COLLATE utf8mb4_unicode_ci COMMENT '行业标签（逗号分隔，最多3个）',
  `ai_tag` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',
  `category` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '鍒嗙被锛圓I Governance/Policy/Research绛夛級',
  `language` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '璇?█锛坋n/zh/fr绛夛級',
  `tags` json DEFAULT NULL COMMENT '鏍囩?鍒楄〃锛圝SON鏁扮粍锛',
  `metadata` json DEFAULT NULL COMMENT '鍏朵粬鍏冩暟鎹?紙JSON瀵硅薄锛',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_url` (`url`),
  KEY `idx_source_id` (`source_id`),
  KEY `idx_published_at` (`published_at`),
  KEY `idx_crawled_at` (`crawled_at`),
  KEY `idx_source_published` (`source_id`,`published_at`),
  KEY `idx_external_id` (`external_id`),
  KEY `idx_region` (`region`),
  KEY `idx_category` (`category`),
  KEY `idx_ai_tag` (`ai_tag`),
  CONSTRAINT `fk_partnership_ai_source` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Partnership on AI鍗氬?娑堟伅琛?紙2025缁熶竴瀛楁?鏍囧噯锛';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mp_securities_times_messages` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '??ID?UUID?',
  `source_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '??ID',
  `external_id` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '????????URL?????ID??3500937?',
  `title` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '??',
  `content` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '????????????',
  `summary` text COLLATE utf8mb4_unicode_ci COMMENT '???????excerpt????content?1000??',
  `provider` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '????????????byline???',
  `published_at` datetime DEFAULT NULL COMMENT '????????YYYY-MM-DD HH:MM?',
  `crawled_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '????',
  `url` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '??????????',
  `region` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '?????????????????"??"?"??/???/???"?"??"??',
  `industry_tags` text COLLATE utf8mb4_unicode_ci COMMENT '????????????3???"??,????,????"?',
  `ai_tag` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'AI?????AI????/AI????/AI?????',
  `category` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '文章分类',
  `language` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT 'zh' COMMENT '???zh=???',
  `tags` json DEFAULT NULL COMMENT '?????JSON?????????',
  `metadata` json DEFAULT NULL COMMENT '??????JSON???',
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_url` (`url`),
  KEY `idx_source_id` (`source_id`),
  KEY `idx_published_at` (`published_at`),
  KEY `idx_crawled_at` (`crawled_at`),
  KEY `idx_source_published` (`source_id`,`published_at`),
  KEY `idx_external_id` (`external_id`),
  KEY `idx_category` (`category`),
  KEY `idx_region` (`region`),
  KEY `idx_ai_tag` (`ai_tag`),
  CONSTRAINT `fk_securities_times_source` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='?????Securities Times????????';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mp_techcrunch_messages` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '消息ID（UUID）',
  `source_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '来源ID',
  `external_id` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '外部唯一标识（从URL提取的post ID或slug）',
  `title` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '标题',
  `content` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '正文内容（完整文章内容）',
  `summary` text COLLATE utf8mb4_unicode_ci COMMENT '摘要（中文翻译）',
  `provider` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '作者（多个用逗号分隔）',
  `published_at` datetime DEFAULT NULL COMMENT '发布时间',
  `crawled_at` datetime NOT NULL COMMENT '抓取时间',
  `url` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '原文链接（用于去重）',
  `region` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '地区（中文格式，多为''全球''、''美国''等）',
  `industry_tags` text COLLATE utf8mb4_unicode_ci COMMENT '行业标签（逗号分隔，最多3个）',
  `ai_tag` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',
  `category` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '分类（AI/Security/Robotics/Cloud Computing/Hardware等）',
  `language` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '语言（en）',
  `metadata` json DEFAULT NULL COMMENT '其他元数据（JSON对象）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `url` (`url`),
  KEY `idx_url` (`url`),
  KEY `idx_published_at` (`published_at`),
  KEY `idx_external_id` (`external_id`),
  KEY `idx_crawled_at` (`crawled_at`),
  KEY `idx_category` (`category`),
  KEY `idx_source_published` (`source_id`,`published_at`),
  KEY `idx_source_id` (`source_id`),
  KEY `idx_region` (`region`),
  KEY `idx_ai_tag` (`ai_tag`),
  KEY `idx_ai_tag_published` (`ai_tag`,`published_at`),
  CONSTRAINT `mp_techcrunch_messages_ibfk_1` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mp_techinasia_messages` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '消息ID（UUID）',
  `source_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '来源ID',
  `external_id` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '外部唯一标识（从URL slug提取）',
  `title` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '标题',
  `content` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '正文内容（从详情页提取完整文章）',
  `summary` text COLLATE utf8mb4_unicode_ci COMMENT '摘要（RSS description翻译为中文）',
  `provider` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '作者（多个用逗号分隔）',
  `published_at` datetime DEFAULT NULL COMMENT '发布时间',
  `crawled_at` datetime NOT NULL COMMENT '抓取时间',
  `url` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '原文链接（用于去重）',
  `region` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '地区（中文格式，如''新加坡''、''印度尼西亚''、''全球''等）',
  `industry_tags` text COLLATE utf8mb4_unicode_ci COMMENT '行业标签（逗号分隔，最多3个）',
  `ai_tag` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',
  `category` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '分类（AI/Investments/Startups/Fintech等）',
  `language` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '语言（en）',
  `metadata` json DEFAULT NULL COMMENT '其他元数据（JSON对象）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `url` (`url`),
  KEY `idx_region` (`region`),
  KEY `idx_url` (`url`),
  KEY `idx_published_at` (`published_at`),
  KEY `idx_external_id` (`external_id`),
  KEY `idx_crawled_at` (`crawled_at`),
  KEY `idx_category` (`category`),
  KEY `idx_source_published` (`source_id`,`published_at`),
  KEY `idx_source_id` (`source_id`),
  CONSTRAINT `mp_techinasia_messages_ibfk_1` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mp_the_hindu_messages` (
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
  `region` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '地区（中文格式，从文章内容提取）',
  `industry_tags` text COLLATE utf8mb4_unicode_ci COMMENT '行业标签（逗号分隔，最多3个，涉及AI必须包含"人工智能"标签）',
  `ai_tag` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',
  `category` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '文章分类',
  `language` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT 'en' COMMENT '语言',
  `media_content` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '媒体内容URL（RSS的media:content字段）',
  `tags` json DEFAULT NULL COMMENT '标签列表（JSON数组）',
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
  KEY `idx_region` (`region`),
  KEY `idx_ai_tag` (`ai_tag`),
  CONSTRAINT `mp_the_hindu_messages_ibfk_1` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='The Hindu Business消息表（RSS Feed采集）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mp_times_of_india_messages` (
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
  `region` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '地区（中文格式，从文章内容提取）',
  `industry_tags` text COLLATE utf8mb4_unicode_ci COMMENT '行业标签（逗号分隔，最多3个，涉及AI必须包含"人工智能"标签）',
  `ai_tag` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',
  `category` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '文章分类',
  `language` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT 'en' COMMENT '语言',
  `media_content` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '媒体内容URL（RSS的media:content字段）',
  `tags` json DEFAULT NULL COMMENT '标签列表（JSON数组）',
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
  KEY `idx_region` (`region`),
  KEY `idx_ai_tag` (`ai_tag`),
  CONSTRAINT `mp_times_of_india_messages_ibfk_1` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Times of India Tech消息表（RSS Feed采集）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mp_tonghuashun_messages` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '消息ID（UUID）',
  `source_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '来源ID',
  `title` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '标题',
  `content` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '正文内容',
  `summary` text COLLATE utf8mb4_unicode_ci COMMENT '摘要（<1000字用content，≥1000字LLM生成）',
  `provider` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '信息提供方（来源）',
  `published_at` datetime DEFAULT NULL COMMENT '发布时间',
  `url` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '原文链接（用于去重）',
  `image_url` text COLLATE utf8mb4_unicode_ci COMMENT '图片链接',
  `crawled_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
  `seq` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '同花顺序列号',
  `tags` json DEFAULT NULL COMMENT '标签列表（JSON数组）',
  `region` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '地区（国家/省份/城市，斜杠分隔）',
  `industry_tags` text COLLATE utf8mb4_unicode_ci COMMENT '行业标签（逗号分隔，最多3个）',
  `ai_tag` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `url` (`url`),
  KEY `idx_source_id` (`source_id`),
  KEY `idx_published_at` (`published_at`),
  KEY `idx_source_published` (`source_id`,`published_at`),
  KEY `idx_crawled_at` (`crawled_at`),
  KEY `idx_seq` (`seq`),
  KEY `idx_provider` (`provider`),
  KEY `idx_url` (`url`),
  KEY `idx_region` (`region`),
  KEY `idx_industry_tags` (`industry_tags`(100)),
  KEY `idx_ai_tag` (`ai_tag`),
  KEY `idx_ai_tag_published` (`ai_tag`,`published_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mp_venturebeat_messages` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '消息ID（UUID）',
  `source_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '来源ID',
  `external_id` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '外部唯一标识（从URL路径提取slug）',
  `title` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '标题',
  `content` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '正文内容（从详情页提取的完整文章）',
  `summary` text COLLATE utf8mb4_unicode_ci COMMENT '中文摘要（翻译后）',
  `provider` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '作者（多个用逗号分隔）',
  `published_at` datetime DEFAULT NULL COMMENT '发布时间',
  `crawled_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
  `url` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '原文链接（用于去重）',
  `region` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '地区（中文格式，如"美国"、"美国/加利福尼亚州"、"全球"等）',
  `industry_tags` text COLLATE utf8mb4_unicode_ci COMMENT '行业标签（逗号分隔，最多3个，涉及AI必须包含"人工智能"标签）',
  `category` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '文章分类（AI/Data Infrastructure/Security）',
  `language` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT 'en' COMMENT '语言（en）',
  `excerpt` text COLLATE utf8mb4_unicode_ci COMMENT '摘要（从列表页提取的excerpt）',
  `featured_image` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '特色图片URL',
  `tags` json DEFAULT NULL COMMENT '标签列表（JSON数组）',
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
  KEY `idx_region` (`region`),
  CONSTRAINT `fk_venturebeat_source` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='VentureBeat科技媒体（美国AI、数据基础设施、安全领域新闻）消息表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mp_wired_messages` (
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
  `region` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '地区（中文格式，从文章内容提取，默认"美国"）',
  `industry_tags` text COLLATE utf8mb4_unicode_ci COMMENT '行业标签（逗号分隔，最多3个，涉及AI必须包含"人工智能"标签）',
  `ai_tag` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',
  `category` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '文章分类',
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
  KEY `idx_url` (`url`),
  KEY `idx_external_id` (`external_id`),
  KEY `idx_category` (`category`),
  KEY `idx_region` (`region`),
  KEY `idx_ai_tag` (`ai_tag`),
  CONSTRAINT `mp_wired_messages_ibfk_1` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Wired科技新闻消息表（RSS Feed采集）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mp_wsj_messages` (
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
  `category` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '文章分类',
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
  KEY `idx_url` (`url`),
  KEY `idx_external_id` (`external_id`),
  KEY `idx_category` (`category`),
  KEY `idx_region` (`region`),
  KEY `idx_ai_tag` (`ai_tag`),
  CONSTRAINT `fk_wsj_source` FOREIGN KEY (`source_id`) REFERENCES `mp_message_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='华尔街日报科技新闻消息表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;


-- 恢复外键检查
SET FOREIGN_KEY_CHECKS = 1;
