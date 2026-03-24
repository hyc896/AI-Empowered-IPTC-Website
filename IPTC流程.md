# IPTC 思政课智能案例系统操作流程

**数据流向**：
```
新闻网站 → 采集器 → MySQL消息表 → 向量撞库 → 匹配知识点 → 生成案例 → 前端展示
```

---

## 环境准备

### 必需服务

在启动系统前，确保以下服务已运行：

1. **MySQL** (端口3306)
   - 数据库名：`message_platform`
   - 用户名/密码：配置在`.env`文件中

2. **Redis** (端口6379)
   - 用于Celery消息队列

### 配置文件检查

确保以下配置文件存在且正确：

- `D:\AI-Empowered IPTC Website\.env` - 环境变量配置
- `D:\AI-Empowered IPTC Website\一期\config.yaml` - 系统配置

---

## 后端服务启动

### 前置条件：激活Conda环境

**重要**：启动服务前必须先激活正确的conda环境，否则会找不到依赖包。

```bash
# 激活conda环境（根据实际环境名称调整）
conda activate personal_agent
```
单独启动各个服务

如果需要单独启动某个服务进行调试：

**启动ChromaDB Server**：
```bash
chroma run --path ./data/chromadb --host 0.0.0.0 --port 11530
```

**启动采集器Worker**：
```bash
celery -A backend.tasks worker --loglevel=info --pool=solo -Q default,collector -n collector@%h
```

**启动FastAPI Server**：
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 11528
```

### 验证后端服务

打开浏览器访问：http://localhost:11528/docs

如果能看到Swagger API文档页面，说明后端服务启动成功。

---

## 前端服务启动

### 安装依赖（首次运行）

```bash
cd "D:\AI-Empowered IPTC Website\一期\iptc-dashboard"
npm install
```

### 启动开发服务器

```bash
cd "D:\AI-Empowered IPTC Website\一期\iptc-dashboard"
npm run dev
```

**启动成功标志**：
```
VITE v5.x.x  ready in xxx ms

➜  Local:   http://localhost:5174/
➜  Network: use --host to expose
```

### 访问前端界面

打开浏览器访问：http://localhost:5174

**主要功能页面**：
- 首页：http://localhost:5174/
- 案例库：http://localhost:5174/cases
- 案例详情：http://localhost:5174/cases/{案例ID}
- 知识图谱：http://localhost:5174/graph

### 前端配置

前端API请求地址配置在：`iptc-dashboard/src/api/request.ts`

默认后端地址：`http://localhost:11528`

---

## 消息采集流程

### 采集器概述

系统支持多个新闻源的自动采集，包括：
- **理论网站**：人民网理论频道、光明网理论频道、求是网、中国社会科学网
- **财经媒体**：同花顺7x24快讯、证券时报、36氪
- **其他来源**：根据配置动态扩展

### 方式1：通过API手动触发采集

**查看可用的采集器列表**：

```bash
curl http://localhost:11528/api/v1/collectors/list
```

**手动触发指定采集器**：

```bash
# 触发求是网采集
curl -X POST http://localhost:11528/api/v1/collectors/qstheory/trigger

# 触发人民网理论频道采集
curl -X POST http://localhost:11528/api/v1/collectors/people_theory/trigger

# 触发同花顺快讯采集
curl -X POST http://localhost:11528/api/v1/collectors/tonghuashun/trigger
```

**查看采集任务状态**：

```bash
# 返回的task_id用于查询任务状态
curl http://localhost:11528/api/v1/collectors/qstheory/task/{task_id}
```

### 方式2：通过定时任务自动采集

系统使用Celery Beat进行定时调度，配置文件位于：`backend/tasks/__init__.py`

**默认调度策略**：
- 理论网站：每2小时采集一次
- 财经快讯：每30分钟采集一次
- 其他来源：根据更新频率配置

**查看定时任务状态**：

启动脚本会自动启动Celery Beat，无需手动干预。

### 采集结果验证

**检查MySQL数据库**：

```sql
-- 查看最近采集的消息（以求是网为例）
SELECT id, title, published_at, crawled_at
FROM mp_qstheory_messages
ORDER BY crawled_at DESC
LIMIT 10;

-- 统计各来源的消息数量
SELECT source_id, COUNT(*) as count
FROM mp_qstheory_messages
GROUP BY source_id;
```

**检查采集日志**：

采集器Worker的日志会显示采集进度和结果：
```
[采集器] qstheory 开始采集
[采集器] 采集到 15 条新消息
[采集器] 去重后剩余 12 条
[采集器] 成功存储到数据库
```

---

## 知识点撞库与案例生成

### 撞库原理

系统使用向量相似度匹配技术，将采集到的新闻消息与思政课知识点进行匹配：

1. **向量化**：将消息内容转换为向量，存储在ChromaDB中
2. **相似度计算**：计算消息向量与知识点向量的余弦相似度
3. **阈值筛选**：相似度 ≥ 0.5 的消息被认为与知识点相关
4. **案例生成**：当某个知识点匹配到 ≥ 5 条消息时，自动生成教学案例

### 执行批量撞库

**运行批量匹配脚本**：

```bash
cd "D:\AI-Empowered IPTC Website\一期"
python backend/scripts/batch_match_cases.py
```

**脚本执行流程**：

1. 加载所有中国来源的消息表
2. 从ChromaDB加载知识点向量库
3. 批量处理消息（每批200条）
4. 计算每条消息与所有知识点的相似度
5. 筛选相似度 ≥ 0.5 的匹配结果
6. 统计每个知识点的匹配消息数量
7. 对匹配数 ≥ 5 的知识点生成案例

**配置参数**：

在 `batch_match_cases.py` 中可调整以下参数：

```python
BATCH_SIZE = 200                    # 每批处理的消息数量
SIMILARITY_THRESHOLD = 0.5          # 相似度阈值
CASE_GENERATION_THRESHOLD = 5       # 生成案例所需的最小消息数
```

### 查看生成的案例

**通过前端界面查看**：

访问 http://localhost:5174/cases 查看案例库

**通过数据库查询**：

```sql
-- 查看最近生成的案例
SELECT id, title, summary, published_at
FROM iptc_cases
ORDER BY created_at DESC
LIMIT 10;

-- 查看某个知识点的案例
SELECT id, title, related_knowledge_points
FROM iptc_cases
WHERE related_knowledge_points LIKE '%中国式现代化%'
ORDER BY published_at DESC;
```

### 手动导入Markdown案例

如果有已编写好的Markdown格式案例，可以使用导入脚本：

```bash
cd "D:\AI-Empowered IPTC Website\一期"
python backend/scripts/import_markdown_cases.py
```

该脚本会自动解析Markdown文件中的标题、内容、知识点等信息，并导入到数据库。

---

## 常见问题排查

### 问题1：ChromaDB初始化失败

**错误信息**：
```
pyo3_runtime.PanicException: range start index 10 out of range for slice of length 9
```

**原因**：ChromaDB数据文件损坏或版本不兼容

**解决方案**：

```bash
# 停止所有服务（Ctrl+C）

# 删除损坏的ChromaDB数据
Remove-Item -Recurse -Force "D:\AI-Empowered IPTC Website\一期\data\chromadb_mp"

# 重新启动服务
cd "D:\AI-Empowered IPTC Website\一期"
python start.py
```

### 问题2：后端服务无法启动

**检查端口占用**：

```bash
# 检查11528端口是否被占用
netstat -ano | findstr "11528"

# 如果被占用，终止进程
taskkill /PID <进程ID> /F
```

**检查MySQL连接**：

确保MySQL服务正在运行，且`.env`文件中的数据库配置正确。

### 问题3：前端无法连接后端

**检查后端服务状态**：

访问 http://localhost:11528/docs，如果能看到API文档，说明后端正常。

**检查前端配置**：

确认 `iptc-dashboard/src/api/request.ts` 中的后端地址为 `http://localhost:11528`

### 问题4：采集器无响应

**查看Worker日志**：

启动脚本的终端会显示Worker日志，查找错误信息。

**手动测试采集器**：

```bash
# 单独启动采集器Worker进行调试
celery -A backend.tasks worker --loglevel=debug --pool=solo -Q collector -n collector@%h
```

### 问题5：案例生成数量少

**检查消息数量**：

```sql
-- 统计各来源的消息数量
SELECT COUNT(*) FROM mp_qstheory_messages;
SELECT COUNT(*) FROM mp_people_theory_messages;
```

**调整相似度阈值**：

如果消息数量充足但案例少，可以适当降低 `SIMILARITY_THRESHOLD`（如从0.5降到0.4）。

**检查知识点向量库**：

```python
# 在Python中检查ChromaDB
import chromadb
client = chromadb.PersistentClient(path="./data/chromadb")
collection = client.get_collection("iptc_knowledge_points")
print(f"知识点数量: {collection.count()}")
```

### 问题6：前端显示空白

**检查浏览器控制台**：

按F12打开开发者工具，查看Console和Network标签页的错误信息。

**检查API响应**：

```bash
# 测试案例列表API
curl http://localhost:11528/api/v1/cases?page=1&page_size=20
```

### 获取帮助

如遇到其他问题，请检查：
1. 启动脚本的完整日志输出
2. MySQL数据库连接状态
3. Redis服务运行状态
4. ChromaDB数据目录权限

---

**文档版本**：v1.0
**最后更新**：2025年1月
**维护者**：IPTC项目组

后端 cd "D:\AI-Empowered IPTC Website\一期\backend" && python start_all.py
前端 cd "D:\AI-Empowered IPTC Website\一期\iptc-dashboard" && npm run dev

手动
  终端1 - Worker（保持运行）：
  conda activate personal_agent; cd "D:\AI-Empowered IPTC Website\一期"; python -m celery -A backend.tasks worker --loglevel=info --pool=solo -Q collector,default
  
  终端2 - 自动调度器（替代Beat）：
  conda activate personal_agent; cd "D:\AI-Empowered IPTC Website\一期"; python auto_collector_scheduler.py


  1. 先检查匹配情况：
  python backend/scripts/check_knowledge_point_matches.py

  2. 再批量生成案例：
  python backend/scripts/batch_match_cases.py

  3. 再次检查结果：
  python backend/scripts/check_knowledge_point_matches.py

  等待脚本运行结束后，可以运行以下命令查看生成结果：
  cd "D:\AI-Empowered IPTC Website\一期" && python backend/scripts/check_stats.py

  查看案例以及相关联的消息
  python backend/scripts/show_random_case.py

 cd "d:\AI-Empowered IPTC Website\一期\backend\Graph\GraphRAG-Visualizer\backend"
 python -m uvicorn app.main_test:app --reload --port 8000

撞库并生成案例
  cd "D:/AI-Empowered IPTC Website/一期"
  python backend/scripts/batch_match_cases.py


   uvicorn backend.main:app --host 0.0.0.0 --port 11528
    cd iptc-dashboard                   
>> npm run dev 