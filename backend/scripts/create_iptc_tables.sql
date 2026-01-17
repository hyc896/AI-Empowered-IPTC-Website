-- ============================================================
-- 思政课智能案例系统 - 数据库表创建脚本
-- 创建时间: 2025-12-08
-- 用途: 创建案例生成所需的3张核心表
-- ============================================================

USE message_platform;

-- 表1: 案例表
-- 存储生成的教学案例
CREATE TABLE IF NOT EXISTS iptc_cases (
    id VARCHAR(36) PRIMARY KEY COMMENT '案例唯一标识UUID',
    title VARCHAR(500) NOT NULL COMMENT '案例标题',
    content TEXT NOT NULL COMMENT '完整Markdown格式的案例内容',
    summary TEXT COMMENT '案例摘要（核心阅读部分）',
    source_url VARCHAR(500) COMMENT '主要参考新闻来源URL',
    tags TEXT COMMENT '案例标签（逗号分隔）',
    related_knowledge_points JSON COMMENT '关联的知识点列表 [{id, name, similarity}]',
    source_message_ids JSON COMMENT '来源消息ID列表 [msg_id1, msg_id2, ...]',
    published_at DATETIME COMMENT '原始新闻发布时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '案例创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '案例更新时间',

    INDEX idx_published_at (published_at),
    INDEX idx_created_at (created_at),
    FULLTEXT idx_content (title, content, summary)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='思政课教学案例表';

-- 表2: 知识点统计表
-- 统计每个知识点匹配的消息数量，用于触发案例生成
CREATE TABLE IF NOT EXISTS iptc_knowledge_point_stats (
    id VARCHAR(36) PRIMARY KEY COMMENT '统计记录唯一标识UUID',
    knowledge_point_id VARCHAR(36) NOT NULL UNIQUE COMMENT '知识点ID（对应ChromaDB中的ID）',
    knowledge_point_name VARCHAR(200) NOT NULL COMMENT '知识点名称',
    matched_message_count INT DEFAULT 0 COMMENT '匹配的消息数量',
    case_generated TINYINT DEFAULT 0 COMMENT '是否已生成案例 0=否 1=是',
    last_matched_at DATETIME COMMENT '最后一次匹配消息的时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',

    INDEX idx_message_count (matched_message_count),
    INDEX idx_case_generated (case_generated),
    INDEX idx_kp_name (knowledge_point_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识点统计表';

-- 表3: 消息-知识点关联表
-- 记录每条消息与知识点的匹配关系（向量相似度>=0.6）
CREATE TABLE IF NOT EXISTS iptc_message_knowledge_relations (
    id VARCHAR(36) PRIMARY KEY COMMENT '关联记录唯一标识UUID',
    message_id VARCHAR(36) NOT NULL COMMENT '消息ID',
    source_table VARCHAR(100) NOT NULL COMMENT '消息来源表名（如mp_qstheory_messages）',
    knowledge_point_id VARCHAR(36) NOT NULL COMMENT '知识点ID',
    knowledge_point_name VARCHAR(200) NOT NULL COMMENT '知识点名称',
    similarity_score DECIMAL(5,4) NOT NULL COMMENT '相似度分数 0.0000-1.0000',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '关联记录创建时间',

    INDEX idx_message_id (message_id),
    INDEX idx_kp_id (knowledge_point_id),
    INDEX idx_similarity (similarity_score),
    INDEX idx_source_table (source_table),
    UNIQUE KEY uk_msg_kp (message_id, knowledge_point_id) COMMENT '同一消息不重复关联同一知识点'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='消息-知识点关联表';

-- ============================================================
-- 验证表创建
-- ============================================================
SELECT
    TABLE_NAME AS '表名',
    TABLE_COMMENT AS '说明',
    CREATE_TIME AS '创建时间'
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'message_platform'
  AND TABLE_NAME LIKE 'iptc%'
ORDER BY TABLE_NAME;

-- ============================================================
-- 表结构说明
-- ============================================================
--
-- 数据流向:
-- 1. 消息采集 -> mp_*_messages 表
-- 2. 向量撞库 -> iptc_message_knowledge_relations 表
-- 3. 统计聚合 -> iptc_knowledge_point_stats 表
-- 4. 达到阈值(>=7条) -> 触发案例生成 -> iptc_cases 表
--
-- 核心配置参数:
-- - 相似度阈值: 0.6 (similarity_score >= 0.6 才记录关联)
-- - 案例生成阈值: 7 (matched_message_count >= 7 才生成案例)
-- - 批量触发数: 200 (积攒200条新消息后触发批量撞库)
--
-- ============================================================
