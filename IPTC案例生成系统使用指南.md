# IPTC案例生成系统使用指南

## 系统架构说明

本系统由**三个独立的进程**组成，必须按顺序启动：

### 1. Celery Worker（消息采集执行器）
- **功能**：执行消息采集任务
- **运行方式**：需手动启动，持续运行
- **数据存储**：自动存储到MySQL数据库的各消息表

### 2. Celery Beat（定时调度器）
- **功能**：定时触发消息采集任务
- **频率**：每个消息源按config.interval配置执行（中国来源为3600秒=1小时）
- **运行方式**：需手动启动，持续运行
- **数据来源**：从数据库mp_message_sources表动态读取配置

### 3. IPTC Auto Scheduler（案例生成脚本）
- **功能**：读取数据库消息 → 向量匹配知识点 → 生成案例
- **频率**：每1小时执行一次
- **运行方式**：需手动启动，持续运行
- **数据流**：MySQL消息表 → ChromaDB向量匹配 → LLM生成案例 → 存储到iptc_cases表

**关键理解**：
- Celery Worker/Beat负责**消息采集**
- iptc_auto_scheduler.py负责**案例生成**
- 两者完全独立，必须都启动才能完成完整流程

---

## 一、消息采集服务的启动方式

### 1.1 启动环境要求

**Conda环境**：`personal_agent`

**必需的依赖**：
- celery==5.5.3
- redis==6.4.0
- schedule==1.2.2
- 其他依赖见 requirements.txt

**验证环境**：
```powershell
# 激活环境并检查Python版本
conda activate personal_agent
python --version

# 检查Redis是否运行
redis-cli ping
# 应显示：PONG
```

### 1.2 启动Celery Worker（采集执行器）

**终端1** - 打开第一个PowerShell窗口：

```powershell
conda activate personal_agent
cd "D:\AI-Empowered IPTC Website\message_platform"
python -m celery -A backend.tasks worker --loglevel=info --pool=solo -Q collector,default
```

**参数说明**：
- `-A backend.tasks` - 指定Celery应用位置
- `--pool=solo` - Windows必须使用solo模式（单线程串行执行）
- `-Q collector,default` - 监听collector和default两个队列
- `--loglevel=info` - 日志级别

**启动成功标志**：
```
[tasks]
  . backend.tasks.collector_tasks.run_collector
  . backend.tasks.ai_report_tasks.generate_daily_report

[2025-12-10 00:20:30] celery@hostname ready.
```

### 1.3 启动Celery Beat（定时调度器）

**终端2** - 打开第二个PowerShell窗口：

```powershell
conda activate personal_agent
cd "D:\AI-Empowered IPTC Website\message_platform"
python -m celery -A backend.tasks beat --loglevel=info
```

**启动成功标志**：
```
[Beat调度] 加载到 13 个激活消息源
[Beat调度] 注册采集任务: 人民网理论频道 (间隔: 3600秒)
[Beat调度] 注册采集任务: 央视新闻 (间隔: 3600秒)
...
[Beat调度] 采集器任务加载完成: 13 个
celery beat v5.5.3 is starting.
```

### 1.4 验证采集是否工作

启动后等待5-10分钟，查看Worker终端是否有任务执行日志：

```
[2025-12-10 00:25:00] Task backend.tasks.collector_tasks.run_collector[xxx] received
[2025-12-10 00:25:05] Task backend.tasks.collector_tasks.run_collector[xxx] succeeded in 5.2s
```

查询数据库验证消息是否入库：

```bash
mysql -u root -pHyc174513 -D message_platform -e "
SELECT 'people_theory' as source, COUNT(*) FROM mp_people_theory_messages
UNION ALL SELECT 'cctv_news', COUNT(*) FROM mp_cctv_news_messages
UNION ALL SELECT 'xinhua', COUNT(*) FROM mp_xinhua_messages
UNION ALL SELECT 'gmw', COUNT(*) FROM mp_gmw_messages
UNION ALL SELECT 'guancha', COUNT(*) FROM mp_guancha_messages
UNION ALL SELECT 'huanqiu', COUNT(*) FROM mp_huanqiu_messages
UNION ALL SELECT 'thepaper', COUNT(*) FROM mp_thepaper_messages
ORDER BY source;"
```

### 1.5 停止采集服务

```powershell
# 在Worker终端按 Ctrl+C
# 在Beat终端按 Ctrl+C
```

---

## 二、案例生成脚本的启动方式

### 2.1 前置条件

**确保数据库已有消息**！运行以下命令检查：

```bash
mysql -u root -pHyc174513 -D message_platform -e "
SELECT SUM(cnt) as total FROM (
    SELECT COUNT(*) as cnt FROM mp_people_theory_messages
    UNION ALL SELECT COUNT(*) FROM mp_qstheory_messages
    UNION ALL SELECT COUNT(*) FROM mp_gmw_theory_messages
    UNION ALL SELECT COUNT(*) FROM mp_cssn_messages
    UNION ALL SELECT COUNT(*) FROM mp_cctv_news_messages
    UNION ALL SELECT COUNT(*) FROM mp_xinhua_messages
    UNION ALL SELECT COUNT(*) FROM mp_gmw_messages
    UNION ALL SELECT COUNT(*) FROM mp_guancha_messages
    UNION ALL SELECT COUNT(*) FROM mp_huanqiu_messages
    UNION ALL SELECT COUNT(*) FROM mp_thepaper_messages
    UNION ALL SELECT COUNT(*) FROM mp_kr36_messages
    UNION ALL SELECT COUNT(*) FROM mp_securities_times_messages
    UNION ALL SELECT COUNT(*) FROM mp_tonghuashun_messages
) t;"
```

**如果total为0**，说明采集器还没采集到消息，请继续等待或检查Celery Worker/Beat是否正常运行。

### 2.2 启动命令

**终端3** - 打开第三个PowerShell窗口：

#### 生产模式（推荐）：每小时自动执行，持续运行

```powershell
conda activate personal_agent
cd "D:\AI-Empowered IPTC Website\message_platform"
python backend/scripts/iptc_auto_scheduler.py
```

#### 测试模式：只执行一次，限制5条消息，用于验证

```powershell
conda activate personal_agent
cd "D:\AI-Empowered IPTC Website\message_platform"
python backend/scripts/iptc_auto_scheduler.py --test
```

#### 仅测试初始化：验证数据库、LLM、ChromaDB是否正常

```powershell
conda activate personal_agent
cd "D:\AI-Empowered IPTC Website\message_platform"
python backend/scripts/iptc_auto_scheduler.py --init-only
```

### 2.3 启动成功标志

看到以下日志表示启动成功：

```
================================================================================
🎯 IPTC案例自动生成调度器启动
================================================================================
模式: 正常模式（每小时执行一次）
首次执行: 立即开始
================================================================================

🚀 开始执行定时任务 - 2025-12-10 00:30:00
================================================================================
[定时任务] 开始案例生成 - 2025-12-10 00:30:00
[初始化] 数据库连接池初始化成功
[初始化] 加载了 13 个中国来源的消息表
[初始化] LLM管理器初始化成功
[初始化] ChromaDB初始化成功，知识点数: 61
================================================================================
开始批量撞库任务
================================================================================
获取到 X 条待处理消息，开始撞库...
✅ [案例生成] 任务完成
================================================================================
✅ 定时任务完成 - 耗时 6.04秒
================================================================================

📅 进入定时循环，等待下次执行（每小时）...
```

### 2.4 停止案例生成脚本

```powershell
# 在运行窗口按 Ctrl+C
```

---

## 三、完整启动流程（从零开始）

### 步骤1：启动Redis（如果未运行）

```powershell
# Windows下通常Redis已作为服务自动运行
# 验证：
redis-cli ping
```

### 步骤2：启动消息采集服务

**终端1 - Celery Worker**：
```powershell
conda activate personal_agent
cd "D:\AI-Empowered IPTC Website\message_platform"
python -m celery -A backend.tasks worker --loglevel=info --pool=solo -Q collector,default
```

**终端2 - Celery Beat**：
```powershell
conda activate personal_agent
cd "D:\AI-Empowered IPTC Website\message_platform"
python -m celery -A backend.tasks beat --loglevel=info
```

### 步骤3：等待消息采集

等待10-30分钟，让采集器采集到一些消息。期间可以观察Worker终端的日志输出。

### 步骤4：验证数据库有消息

```bash
mysql -u root -pHyc174513 -D message_platform -e "
SELECT 'people_theory' as source, COUNT(*) FROM mp_people_theory_messages
UNION ALL SELECT 'cctv_news', COUNT(*) FROM mp_cctv_news_messages
UNION ALL SELECT 'xinhua', COUNT(*) FROM mp_xinhua_messages
ORDER BY source;"
```

### 步骤5：启动案例生成脚本

**终端3 - IPTC Scheduler**：
```powershell
conda activate personal_agent
cd "D:\AI-Empowered IPTC Website\message_platform"
python backend/scripts/iptc_auto_scheduler.py
```

---

## 四、如何查看每个激活的消息源采集信息的数量

### 4.1 查看所有已激活的中国来源及其配置

```bash
mysql -u root -pHyc174513 -D message_platform --default-character-set=utf8mb4 -e "
SELECT
    name as 消息源名称,
    display_name as 显示名称,
    is_active as 是否激活,
    JSON_EXTRACT(config, '$.interval') as 采集频率_秒,
    JSON_EXTRACT(config, '$.mysql_table') as 数据表名
FROM mp_message_sources
WHERE is_active = 1 AND (
    JSON_EXTRACT(config, '$.config.region') = '中国'
    OR name IN ('kr36', 'securities_times', 'tonghuashun')
)
ORDER BY name;
"
```

**预期输出**（13个已激活的中国来源，每3600秒=1小时采集）：

```
消息源名称          显示名称              是否激活  采集频率_秒  数据表名
cctv_news           央视新闻              1         3600         "mp_cctv_news_messages"
cssn                中国社会科学网        1         3600         "mp_cssn_messages"
gmw                 光明网                1         3600         "mp_gmw_messages"
gmw_theory          光明网理论            1         3600         "mp_gmw_theory_messages"
guancha             观察者网              1         3600         "mp_guancha_messages"
huanqiu             环球网                1         3600         "mp_huanqiu_messages"
kr36                36氪                  1         3600         "mp_kr36_messages"
people_theory       人民网理论            1         3600         "mp_people_theory_messages"
qstheory            求是理论              1         3600         "mp_qstheory_messages"
securities_times    证券时报              1         3600         "mp_securities_times_messages"
thepaper            澎湃新闻              1         3600         "mp_thepaper_messages"
tonghuashun         同花顺                1         3600         "mp_tonghuashun_messages"
xinhua              新华网                1         3600         "mp_xinhua_messages"
```

### 4.2 查看各消息源采集的消息数量

```bash
mysql -u root -pHyc174513 -D message_platform -e "
SELECT 'people_theory' as 消息源, COUNT(*) as 消息数量 FROM mp_people_theory_messages
UNION ALL SELECT 'qstheory', COUNT(*) FROM mp_qstheory_messages
UNION ALL SELECT 'gmw_theory', COUNT(*) FROM mp_gmw_theory_messages
UNION ALL SELECT 'cssn', COUNT(*) FROM mp_cssn_messages
UNION ALL SELECT 'cctv_news', COUNT(*) FROM mp_cctv_news_messages
UNION ALL SELECT 'xinhua', COUNT(*) FROM mp_xinhua_messages
UNION ALL SELECT 'gmw', COUNT(*) FROM mp_gmw_messages
UNION ALL SELECT 'guancha', COUNT(*) FROM mp_guancha_messages
UNION ALL SELECT 'huanqiu', COUNT(*) FROM mp_huanqiu_messages
UNION ALL SELECT 'thepaper', COUNT(*) FROM mp_thepaper_messages
UNION ALL SELECT 'kr36', COUNT(*) FROM mp_kr36_messages
UNION ALL SELECT 'securities_times', COUNT(*) FROM mp_securities_times_messages
UNION ALL SELECT 'tonghuashun', COUNT(*) FROM mp_tonghuashun_messages
ORDER BY 消息数量 DESC;
"
```

**预期输出示例**：

```
消息源                   消息数量
people_theory            15
qstheory                 8
cctv_news                5
gmw_theory               6
cssn                     3
tonghuashun              2
xinhua                   0
guancha                  0
... (其他消息源)
```

### 4.3 查看总消息数

```bash
mysql -u root -pHyc174513 -D message_platform -e "
SELECT
    'Total' as 统计项,
    (SELECT COUNT(*) FROM mp_people_theory_messages) +
    (SELECT COUNT(*) FROM mp_qstheory_messages) +
    (SELECT COUNT(*) FROM mp_gmw_theory_messages) +
    (SELECT COUNT(*) FROM mp_cssn_messages) +
    (SELECT COUNT(*) FROM mp_cctv_news_messages) +
    (SELECT COUNT(*) FROM mp_xinhua_messages) +
    (SELECT COUNT(*) FROM mp_gmw_messages) +
    (SELECT COUNT(*) FROM mp_guancha_messages) +
    (SELECT COUNT(*) FROM mp_huanqiu_messages) +
    (SELECT COUNT(*) FROM mp_thepaper_messages) +
    (SELECT COUNT(*) FROM mp_kr36_messages) +
    (SELECT COUNT(*) FROM mp_securities_times_messages) +
    (SELECT COUNT(*) FROM mp_tonghuashun_messages) as 总消息数;
"
```

---

## 五、如何查看储存在数据库中的消息的详细内容

### 5.1 查看特定消息源的最新消息（以people_theory为例）

```bash
mysql -u root -pHyc174513 -D message_platform --default-character-set=utf8mb4 -e "
SELECT
    id,
    title as 标题,
    LEFT(summary, 100) as 摘要预览,
    provider as 作者,
    published_at as 发布时间,
    crawled_at as 采集时间,
    url as 链接
FROM mp_people_theory_messages
ORDER BY crawled_at DESC
LIMIT 5;
"
```

### 5.2 查看特定消息的完整内容

```bash
# 将 YOUR_MESSAGE_ID_HERE 替换为实际的消息ID
mysql -u root -pHyc174513 -D message_platform --default-character-set=utf8mb4 -e "
SELECT
    title as 标题,
    content as 正文内容,
    summary as 摘要,
    provider as 作者,
    published_at as 发布时间,
    url as 原文链接
FROM mp_people_theory_messages
WHERE id = 'YOUR_MESSAGE_ID_HERE';
"
```

### 5.3 导出特定消息到文本文件（便于查看长文本）

```bash
mysql -u root -pHyc174513 -D message_platform --default-character-set=utf8mb4 -e "
SELECT title, content, summary, url, published_at
FROM mp_people_theory_messages
WHERE id = 'YOUR_MESSAGE_ID_HERE';
" > message_detail.txt

# 查看导出的内容
cat message_detail.txt
```

### 5.4 按关键词搜索消息

```bash
# 搜索标题包含"改革"的消息
mysql -u root -pHyc174513 -D message_platform --default-character-set=utf8mb4 -e "
SELECT
    id,
    title,
    LEFT(summary, 80) as 摘要,
    published_at
FROM mp_people_theory_messages
WHERE title LIKE '%改革%'
ORDER BY published_at DESC
LIMIT 10;
"
```

---

## 六、如何查看撞库情况

### 6.1 查看消息-知识点关联总数

```bash
mysql -u root -pHyc174513 -D message_platform -e "
SELECT COUNT(*) as 关联总数 FROM iptc_message_knowledge_relations;
"
```

### 6.2 查看各知识点的消息匹配数量（按数量降序）

```bash
mysql -u root -pHyc174513 -D message_platform --default-character-set=utf8mb4 -e "
SELECT
    knowledge_point_name as 知识点名称,
    COUNT(*) as 匹配消息数,
    CASE
        WHEN COUNT(*) >= 3 THEN '✓ 达标（可生成案例）'
        ELSE '✗ 未达标（需更多消息）'
    END as 状态
FROM iptc_message_knowledge_relations
GROUP BY knowledge_point_name
ORDER BY 匹配消息数 DESC;
"
```

**输出示例**：

```
知识点名称                      匹配消息数  状态
社会主义政治文明建设            5           ✓ 达标（可生成案例）
科学发展观的第一要义            3           ✓ 达标（可生成案例）
发展是党执政兴国第一要务        2           ✗ 未达标（需更多消息）
```

**说明**：
- **阈值**：知识点需关联 ≥3 条消息才会触发案例生成
- **相似度**：消息与知识点的向量相似度 ≥0.6 才会建立关联

### 6.3 查看特定消息匹配到的所有知识点

```bash
# 将 YOUR_MESSAGE_ID_HERE 替换为实际的消息ID
mysql -u root -pHyc174513 -D message_platform --default-character-set=utf8mb4 -e "
SELECT
    r.knowledge_point_name as 知识点名称,
    r.similarity_score as 相似度分数,
    m.title as 消息标题
FROM iptc_message_knowledge_relations r
JOIN mp_people_theory_messages m ON r.message_id = m.id
WHERE r.message_id = 'YOUR_MESSAGE_ID_HERE'
ORDER BY r.similarity_score DESC;
"
```

### 6.4 查看特定知识点关联的所有消息

```bash
# 将 '社会主义政治文明建设' 替换为实际的知识点名称
mysql -u root -pHyc174513 -D message_platform --default-character-set=utf8mb4 -e "
SELECT
    r.message_id as 消息ID,
    r.source_table as 来源表,
    r.similarity_score as 相似度,
    CASE r.source_table
        WHEN 'mp_people_theory_messages' THEN (SELECT title FROM mp_people_theory_messages WHERE id = r.message_id)
        WHEN 'mp_qstheory_messages' THEN (SELECT title FROM mp_qstheory_messages WHERE id = r.message_id)
        WHEN 'mp_gmw_theory_messages' THEN (SELECT title FROM mp_gmw_theory_messages WHERE id = r.message_id)
        WHEN 'mp_cssn_messages' THEN (SELECT title FROM mp_cssn_messages WHERE id = r.message_id)
        ELSE '未知来源'
    END as 消息标题
FROM iptc_message_knowledge_relations r
WHERE r.knowledge_point_name = '社会主义政治文明建设'
ORDER BY r.similarity_score DESC;
"
```

### 6.5 查看所有达标的知识点（可生成案例）

```bash
mysql -u root -pHyc174513 -D message_platform --default-character-set=utf8mb4 -e "
SELECT
    knowledge_point_name as 知识点名称,
    COUNT(*) as 匹配消息数,
    GROUP_CONCAT(DISTINCT source_table) as 来源表
FROM iptc_message_knowledge_relations
GROUP BY knowledge_point_name
HAVING COUNT(*) >= 3
ORDER BY 匹配消息数 DESC;
"
```

---

## 七、如何查看生成的案例数量

### 7.1 查看案例总数

```bash
mysql -u root -pHyc174513 -D message_platform -e "
SELECT COUNT(*) as 案例总数 FROM iptc_cases;
"
```

### 7.2 按日期统计案例生成数量

```bash
mysql -u root -pHyc174513 -D message_platform --default-character-set=utf8mb4 -e "
SELECT
    DATE(created_at) as 日期,
    COUNT(*) as 当日生成案例数
FROM iptc_cases
GROUP BY DATE(created_at)
ORDER BY 日期 DESC;
"
```

### 7.3 查看各知识点的案例生成情况

```bash
mysql -u root -pHyc174513 -D message_platform --default-character-set=utf8mb4 -e "
SELECT
    tags as 知识点标签,
    COUNT(*) as 案例数量
FROM iptc_cases
GROUP BY tags
ORDER BY 案例数量 DESC;
"
```

---

## 八、如何查看生成的案例

### 8.1 查看最新案例列表（简略信息）

```bash
mysql -u root -pHyc174513 -D message_platform --default-character-set=utf8mb4 -e "
SELECT
    id,
    title as 标题,
    tags as 知识点标签,
    LEFT(summary, 80) as 摘要预览,
    created_at as 生成时间
FROM iptc_cases
ORDER BY created_at DESC
LIMIT 10;
"
```

### 8.2 查看特定案例的完整内容

```bash
# 将 YOUR_CASE_ID_HERE 替换为实际的案例ID
mysql -u root -pHyc174513 -D message_platform --default-character-set=utf8mb4 -e "
SELECT
    title as 标题,
    content as 案例正文,
    summary as 摘要,
    tags as 知识点标签,
    source_url as 来源链接,
    created_at as 生成时间
FROM iptc_cases
WHERE id = 'YOUR_CASE_ID_HERE';
"
```

### 8.3 导出案例到文本文件（便于阅读长内容）

```bash
# 导出单个案例
mysql -u root -pHyc174513 -D message_platform --default-character-set=utf8mb4 -e "
SELECT * FROM iptc_cases WHERE id = 'YOUR_CASE_ID_HERE';
" > case_detail.txt

# 导出所有案例
mysql -u root -pHyc174513 -D message_platform --default-character-set=utf8mb4 -e "
SELECT id, title, content, summary, tags, created_at
FROM iptc_cases
ORDER BY created_at DESC;
" > all_cases_export.txt

# 查看导出的文件
cat case_detail.txt
```

### 8.4 按知识点搜索案例

```bash
# 搜索包含"科学发展观"的案例
mysql -u root -pHyc174513 -D message_platform --default-character-set=utf8mb4 -e "
SELECT
    id,
    title,
    tags,
    LEFT(content, 200) as 内容预览,
    created_at
FROM iptc_cases
WHERE tags LIKE '%科学发展观%'
ORDER BY created_at DESC;
"
```

### 8.5 查看案例关联的源消息

```bash
# 将 YOUR_CASE_ID_HERE 替换为实际的案例ID
mysql -u root -pHyc174513 -D message_platform --default-character-set=utf8mb4 -e "
SELECT
    source_message_ids as 关联消息ID列表,
    JSON_LENGTH(source_message_ids) as 消息数量
FROM iptc_cases
WHERE id = 'YOUR_CASE_ID_HERE';
"
```

---

## 九、系统配置参数说明

### 9.1 采集器配置

**已激活的13个中国消息源**（每3600秒=1小时采集一次）：

| 消息源 | 显示名称 | 类型 | 说明 |
|--------|----------|------|------|
| people_theory | 人民网理论 | 理论 | 人民网理论频道 |
| qstheory | 求是理论 | 理论 | 求是理论网 |
| gmw_theory | 光明网理论 | 理论 | 光明网理论频道 |
| cssn | 中国社会科学网 | 理论 | 学术理论 |
| cctv_news | 央视新闻 | 综合 | 央视网新闻 |
| xinhua | 新华网 | 综合 | 新华社官网 |
| gmw | 光明网 | 综合 | 光明日报官网 |
| guancha | 观察者网 | 综合 | 时政观察 |
| huanqiu | 环球网 | 综合 | 环球时报官网 |
| thepaper | 澎湃新闻 | 综合 | 上海主流新媒体 |
| kr36 | 36氪 | 科技 | 科技创投 |
| securities_times | 证券时报 | 财经 | 证券财经 |
| tonghuashun | 同花顺 | 财经 | 金融资讯 |

### 9.2 案例生成配置

**文件位置**：`backend/scripts/batch_match_cases.py`

| 参数 | 值 | 说明 |
|------|-----|------|
| BATCH_SIZE | 200 | 每批处理的消息数量 |
| SIMILARITY_THRESHOLD | 0.6 | 向量匹配相似度阈值（0-1） |
| CASE_GENERATION_THRESHOLD | 3 | 知识点需关联≥3条消息才生成案例 |

### 9.3 调度器配置

**文件位置**：`backend/scripts/iptc_auto_scheduler.py`

- **执行频率**：每1小时自动执行一次
- **启动模式**：需手动启动，持续运行
- **日志位置**：`logs/iptc_scheduler.log`

### 9.4 提示词模板

**文件位置**：`D:\AI-Empowered IPTC Website\新闻转案例提示词.md`

**核心原则**：
- 绝对真实性：严禁编造不在源材料中的信息
- 知识点动态绑定：根据向量匹配结果使用对应知识点
- 多源综合：综合使用≥3条关联消息
- 灵活字数：600-1200字，视源材料丰富度调整

---

## 十、常见问题与排查

### 10.1 Celery Worker无法启动

**错误1**：`redis.exceptions.ConnectionError: Error connecting to Redis`

**解决方案**：
```bash
# 检查Redis是否运行
redis-cli ping

# 如果没有响应，启动Redis服务（Windows）
net start Redis
```

**错误2**：`ModuleNotFoundError: No module named 'celery'`

**解决方案**：
```powershell
conda activate personal_agent
pip install celery redis
```

### 10.2 Celery Beat无法加载消息源

**检查步骤**：

1. 验证数据库连接：
```bash
mysql -u root -pHyc174513 -D message_platform -e "SELECT COUNT(*) FROM mp_message_sources WHERE is_active = 1;"
```

2. 查看Beat日志，确认是否有以下输出：
```
[Beat调度] 加载到 13 个激活消息源
```

3. 如果加载失败，检查配置：
```bash
mysql -u root -pHyc174513 -D message_platform -e "
SELECT name, is_active, config
FROM mp_message_sources
WHERE name = 'people_theory';
"
```

### 10.3 采集器执行但没有消息入库

**检查步骤**：

1. 查看Worker日志，寻找错误信息
2. 检查数据库表是否存在：
```bash
mysql -u root -pHyc174513 -D message_platform -e "SHOW TABLES LIKE 'mp_%_messages';"
```

3. 手动测试采集器（可选，需要编写测试脚本）

### 10.4 消息没有匹配到知识点

**检查步骤**：

1. 验证ChromaDB知识点数量：
```powershell
conda activate personal_agent
cd "D:\AI-Empowered IPTC Website\message_platform"
python -c "import chromadb; client = chromadb.PersistentClient(path='./data/chromadb_mp'); collection = client.get_collection('iptc_knowledge_points'); print(f'知识点总数: {collection.count()}')"
```
应显示：61个知识点

2. 检查相似度阈值（当前0.6，可能需要调低）

3. 查看消息内容是否与思政课知识点相关

### 10.5 知识点关联数达标但未生成案例

**检查步骤**：

1. 查看知识点生成状态：
```bash
mysql -u root -pHyc174513 -D message_platform --default-character-set=utf8mb4 -e "
SELECT
    knowledge_point_name,
    case_generated,
    last_matched_at
FROM iptc_knowledge_point_stats;
"
```

2. 如果 `case_generated=1`，说明已生成过案例。若需重新生成：
```bash
mysql -u root -pHyc174513 -D message_platform -e "
TRUNCATE TABLE iptc_knowledge_point_stats;
"
```

3. 手动触发生成：
```powershell
conda activate personal_agent
cd "D:\AI-Empowered IPTC Website\message_platform"
python backend/scripts/batch_match_cases.py --limit 10
```

### 10.6 案例生成脚本无法启动

**错误1**：`ModuleNotFoundError: No module named 'schedule'`

**解决方案**：
```powershell
conda activate personal_agent
pip install schedule
```

**错误2**：数据库连接失败

**检查步骤**：
```bash
mysql -u root -pHyc174513 -D message_platform -e "SELECT 1;"
```

**错误3**：LLM客户端未初始化

**检查步骤**：
```bash
cd "D:\AI-Empowered IPTC Website\message_platform"
cat config.yaml | grep -A 10 "llm:"
cat .env | grep API_KEY
```

---

## 十一、快速检查脚本

创建一个快速验证脚本 `quick_check.sh`：

```bash
#!/bin/bash
cd "D:\AI-Empowered IPTC Website\message_platform"

echo "=== 步骤1: 检查消息数量 ==="
mysql -u root -pHyc174513 -D message_platform -e "
SELECT 'people_theory' as source, COUNT(*) FROM mp_people_theory_messages
UNION ALL SELECT 'qstheory', COUNT(*) FROM mp_qstheory_messages
UNION ALL SELECT 'cctv_news', COUNT(*) FROM mp_cctv_news_messages
UNION ALL SELECT 'xinhua', COUNT(*) FROM mp_xinhua_messages
UNION ALL SELECT 'gmw', COUNT(*) FROM mp_gmw_messages;"

echo ""
echo "=== 步骤2: 查询知识点关联结果 ==="
mysql -u root -pHyc174513 -D message_platform --default-character-set=utf8mb4 -e "
SELECT knowledge_point_name, COUNT(*) as count,
CASE WHEN COUNT(*) >= 3 THEN '✓' ELSE '✗' END as status
FROM iptc_message_knowledge_relations
GROUP BY knowledge_point_name
ORDER BY count DESC
LIMIT 10;"

echo ""
echo "=== 步骤3: 查询生成的案例 ==="
mysql -u root -pHyc174513 -D message_platform --default-character-set=utf8mb4 -e "
SELECT id, title, tags, created_at
FROM iptc_cases
ORDER BY created_at DESC
LIMIT 5;"

echo ""
echo "=== 流程完成 ==="
```

使用方法：
```bash
bash quick_check.sh
```

---

## 附录：数据库表结构说明

### 消息表（13个中国来源）

**理论类（4个）**：
- `mp_people_theory_messages` - 人民网理论
- `mp_qstheory_messages` - 求是理论
- `mp_gmw_theory_messages` - 光明网理论
- `mp_cssn_messages` - 中国社会科学网

**综合新闻（6个）**：
- `mp_cctv_news_messages` - 央视新闻
- `mp_xinhua_messages` - 新华网
- `mp_gmw_messages` - 光明网
- `mp_guancha_messages` - 观察者网
- `mp_huanqiu_messages` - 环球网
- `mp_thepaper_messages` - 澎湃新闻

**财经科技（3个）**：
- `mp_kr36_messages` - 36氪
- `mp_securities_times_messages` - 证券时报
- `mp_tonghuashun_messages` - 同花顺

### 关联表
- `iptc_message_knowledge_relations` - 消息与知识点的关联关系
- `iptc_knowledge_point_stats` - 知识点统计信息

### 案例表
- `iptc_cases` - 生成的思政课案例

---

## 联系与支持

如遇到问题，请检查以下日志文件：
- 案例生成日志：`logs/iptc_scheduler.log`
- Celery Worker日志：终端输出
- Celery Beat日志：终端输出
- 数据库日志：MySQL错误日志

**系统版本信息**：
- Python：3.x (personal_agent环境)
- MySQL：message_platform数据库
- ChromaDB：./data/chromadb_mp（61个知识点）
- 案例生成阈值：≥3条消息/知识点
- 向量匹配阈值：相似度≥0.6
- 采集频率：3600秒（1小时）
