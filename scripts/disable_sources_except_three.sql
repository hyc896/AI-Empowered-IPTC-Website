-- 批量关闭消息源（仅保留同花顺、arXiv和36Kr）
-- 执行前请确认：保留的三个消息源分别是 name 包含 '同花顺'、'arXiv' 和 'kr36'

-- 关闭除了同花顺、arXiv和36Kr之外的所有消息源
UPDATE mp_message_sources
SET is_active = 0
WHERE name NOT IN (
    SELECT name FROM (
        SELECT name FROM mp_message_sources
        WHERE name LIKE '%同花顺%'
           OR name LIKE '%arXiv%'
           OR name = 'kr36'
    ) AS keep_sources
);

-- 验证结果：查看当前启用的消息源
SELECT id, name, adapter_name, is_active
FROM mp_message_sources
WHERE is_active = 1
ORDER BY name;

-- 验证结果：查看已关闭的消息源数量
SELECT
    COUNT(*) as total_sources,
    SUM(is_active) as active_sources,
    COUNT(*) - SUM(is_active) as disabled_sources
FROM mp_message_sources;
