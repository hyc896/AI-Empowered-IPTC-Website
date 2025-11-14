-- 为同花顺和36kr消息表添加region和industry_tags字段
-- 执行方式：
-- chcp 65001
-- mysql -h localhost -P 3306 -u root -p123456 --default-character-set=utf8mb4 message_platform < backend/scripts/add_enrichment_fields.sql

-- 为同花顺表添加字段
ALTER TABLE mp_tonghuashun_messages
ADD COLUMN region VARCHAR(200) DEFAULT NULL COMMENT '地区（国家/省份/城市，斜杠分隔）',
ADD COLUMN industry_tags TEXT DEFAULT NULL COMMENT '行业标签（逗号分隔，最多3个）';

-- 为同花顺表添加索引
ALTER TABLE mp_tonghuashun_messages
ADD INDEX idx_region (region),
ADD INDEX idx_industry_tags (industry_tags(100));

-- 为36kr表添加字段
ALTER TABLE mp_kr36_messages
ADD COLUMN region VARCHAR(200) DEFAULT NULL COMMENT '地区（国家/省份/城市，斜杠分隔）',
ADD COLUMN industry_tags TEXT DEFAULT NULL COMMENT '行业标签（逗号分隔，最多3个）';

-- 为36kr表添加索引
ALTER TABLE mp_kr36_messages
ADD INDEX idx_region (region),
ADD INDEX idx_industry_tags (industry_tags(100));

-- 验证字段添加成功
SELECT 'TongHuaShun字段验证:' AS info;
SHOW COLUMNS FROM mp_tonghuashun_messages LIKE 'region';
SHOW COLUMNS FROM mp_tonghuashun_messages LIKE 'industry_tags';

SELECT '36Kr字段验证:' AS info;
SHOW COLUMNS FROM mp_kr36_messages LIKE 'region';
SHOW COLUMNS FROM mp_kr36_messages LIKE 'industry_tags';

SELECT '完成！' AS status;
