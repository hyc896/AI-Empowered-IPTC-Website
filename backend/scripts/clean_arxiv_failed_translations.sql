-- ========================================
-- arXiv翻译失败数据清理SQL脚本
-- ========================================
-- 说明：将summary字段从"[翻译失败，原文] {完整abstract}"
--      改为截断的前500字+省略号
--
-- 使用方法：
--   mysql -uroot -p123456 message_platform < backend/scripts/clean_arxiv_failed_translations.sql
--
-- 或者登录MySQL后执行：
--   source backend/scripts/clean_arxiv_failed_translations.sql
-- ========================================

USE message_platform;

-- 1. 查看当前翻译失败的记录统计
SELECT
    '翻译失败记录统计' AS 'Step 1',
    COUNT(*) AS total_count,
    AVG(LENGTH(summary)) AS avg_summary_length,
    MAX(LENGTH(summary)) AS max_summary_length,
    MIN(LENGTH(summary)) AS min_summary_length
FROM mp_arxiv_messages
WHERE summary LIKE '[翻译失败%';

-- 2. 预览前5条待修改的记录
SELECT
    '待修改记录预览' AS 'Step 2',
    arxiv_id,
    LEFT(title, 50) AS title_preview,
    LENGTH(summary) AS current_length,
    LEFT(summary, 80) AS summary_preview
FROM mp_arxiv_messages
WHERE summary LIKE '[翻译失败%'
ORDER BY published_at DESC
LIMIT 5;

-- 3. 预览修改后的效果（不实际修改）
SELECT
    '修改后预览' AS 'Step 3',
    arxiv_id,
    LENGTH(summary) AS old_length,
    LENGTH(CONCAT(SUBSTRING(content, 1, 500), '...[AI翻译暂不可用]')) AS new_length,
    LEFT(CONCAT(SUBSTRING(content, 1, 500), '...[AI翻译暂不可用]'), 80) AS new_summary_preview
FROM mp_arxiv_messages
WHERE summary LIKE '[翻译失败%'
ORDER BY published_at DESC
LIMIT 5;

-- 4. 实际执行修改（取消下面的注释以执行）
-- ⚠️  警告：此操作不可逆！请先确认上述预览无误
-- UPDATE mp_arxiv_messages
-- SET summary = CONCAT(SUBSTRING(content, 1, 500), '...[AI翻译暂不可用]')
-- WHERE summary LIKE '[翻译失败%';

-- 5. 查看修改后的统计（执行UPDATE后取消下面的注释查看结果）
-- SELECT
--     '修改后统计' AS 'Step 5',
--     COUNT(*) AS remaining_failed_count
-- FROM mp_arxiv_messages
-- WHERE summary LIKE '[翻译失败%';

-- ========================================
-- 手动执行UPDATE的步骤：
-- 1. 先运行上述脚本查看预览
-- 2. 确认无误后，取消第4步UPDATE语句的注释
-- 3. 重新运行脚本
-- 4. 取消第5步SELECT的注释查看结果
-- ========================================
