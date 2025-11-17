-- 为所有包含ai_tag字段的消息表添加索引
-- 执行方式：
-- chcp 65001
-- mysql -h localhost -P 3306 -u root -p123456 --default-character-set=utf8mb4 message_platform < backend/scripts/add_ai_tag_indexes.sql

-- 为同花顺表添加ai_tag索引
ALTER TABLE mp_tonghuashun_messages
ADD INDEX idx_ai_tag (ai_tag),
ADD INDEX idx_ai_tag_published (ai_tag, published_at);

-- 为36kr表添加ai_tag索引
ALTER TABLE mp_kr36_messages
ADD INDEX idx_ai_tag (ai_tag),
ADD INDEX idx_ai_tag_published (ai_tag, published_at);

-- 为Nikkei Asia表添加ai_tag索引
ALTER TABLE mp_nikkei_asia_ai_messages
ADD INDEX idx_ai_tag (ai_tag),
ADD INDEX idx_ai_tag_published (ai_tag, published_at);

-- 为Investing.com表添加ai_tag索引
ALTER TABLE mp_investing_com_messages
ADD INDEX idx_ai_tag (ai_tag),
ADD INDEX idx_ai_tag_published (ai_tag, published_at);

-- 为TechCrunch表添加ai_tag索引
ALTER TABLE mp_techcrunch_messages
ADD INDEX idx_ai_tag (ai_tag),
ADD INDEX idx_ai_tag_published (ai_tag, published_at);

-- 验证索引添加成功
SELECT '同花顺索引验证:' AS info;
SHOW INDEX FROM mp_tonghuashun_messages WHERE Key_name LIKE '%ai_tag%';

SELECT '36Kr索引验证:' AS info;
SHOW INDEX FROM mp_kr36_messages WHERE Key_name LIKE '%ai_tag%';

SELECT 'Nikkei Asia索引验证:' AS info;
SHOW INDEX FROM mp_nikkei_asia_ai_messages WHERE Key_name LIKE '%ai_tag%';

SELECT 'Investing.com索引验证:' AS info;
SHOW INDEX FROM mp_investing_com_messages WHERE Key_name LIKE '%ai_tag%';

SELECT 'TechCrunch索引验证:' AS info;
SHOW INDEX FROM mp_techcrunch_messages WHERE Key_name LIKE '%ai_tag%';

SELECT '完成！' AS status;
