-- 创建AI日报表
-- 执行方式：
-- chcp 65001
-- mysql -h localhost -P 3306 -u root -p123456 --default-character-set=utf8mb4 message_platform < backend/scripts/create_ai_daily_reports_table.sql

CREATE TABLE IF NOT EXISTS mp_ai_daily_reports (
    id VARCHAR(36) PRIMARY KEY COMMENT 'UUID主键',
    report_date DATE NOT NULL UNIQUE COMMENT '报告日期（YYYY-MM-DD）',
    content LONGTEXT NOT NULL COMMENT '日报Markdown内容',
    statistics JSON NOT NULL COMMENT '统计数据（消息数量、地区分布等）',
    governance_count INT NOT NULL DEFAULT 0 COMMENT 'AI治理信息数量',
    research_count INT NOT NULL DEFAULT 0 COMMENT 'AI科研信息数量',
    industry_count INT NOT NULL DEFAULT 0 COMMENT 'AI产业信息数量',
    total_messages INT NOT NULL DEFAULT 0 COMMENT '总消息数量',
    generation_status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '生成状态（pending/success/failed）',
    error_message TEXT DEFAULT NULL COMMENT '错误信息（生成失败时记录）',
    generated_at DATETIME NOT NULL COMMENT '生成时间',
    model_version VARCHAR(50) NOT NULL COMMENT 'LLM模型版本',
    INDEX idx_report_date (report_date),
    INDEX idx_generated_at (generated_at),
    INDEX idx_status (generation_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI日报表';

-- 验证表创建成功
SELECT '表创建验证:' AS info;
SHOW CREATE TABLE mp_ai_daily_reports;

SELECT '完成！' AS status;
