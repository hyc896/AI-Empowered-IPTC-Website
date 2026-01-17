# IPTC案例自动生成系统

## 系统状态

### 自动化服务（需分别启动）

**第一步：消息采集服务**（Celery Worker + Beat）
1. **Celery Worker** - 执行采集任务
   - 配置：13个中国来源（理论4个、综合6个、财经科技3个）
   - 频率：3600秒/次（1小时）
   - 启动：打开终端1，运行Worker命令

2. **Celery Beat** - 定时调度
   - 功能：每3600秒自动触发采集任务
   - 启动：打开终端2，运行Beat命令

**第二步：案例生成服务**（IPTC Scheduler）
3. **IPTC调度器** - 自动生成案例
   - 频率：每小时一次
   - 流程：读取消息 → 向量匹配（阈值0.6）→ 生成案例（需≥3条消息）
   - 启动：打开终端3，运行`python backend/scripts/iptc_auto_scheduler.py`

## 启动命令速查

### 步骤1：启动消息采集

**终端1 - Celery Worker**：
```powershell
conda activate personal_agent; cd "D:\AI-Empowered IPTC Website\message_platform"; python -m celery -A backend.tasks worker --loglevel=info --pool=solo -Q collector,default
```

**终端2 - Celery Beat**：
```powershell
conda activate personal_agent; cd "D:\AI-Empowered IPTC Website\message_platform"; python -m celery -A backend.tasks beat --loglevel=info
```

### 步骤2：等待消息入库（10-30分钟）

验证消息是否采集成功：
```bash
mysql -u root -pHyc174513 -D message_platform -e "SELECT 'people_theory' as source, COUNT(*) FROM mp_people_theory_messages UNION ALL SELECT 'cctv_news', COUNT(*) FROM mp_cctv_news_messages UNION ALL SELECT 'xinhua', COUNT(*) FROM mp_xinhua_messages;"
```

### 步骤3：启动案例生成

**终端3 - IPTC Scheduler**：
```powershell
conda activate personal_agent; cd "D:\AI-Empowered IPTC Website\message_platform"; python backend/scripts/iptc_auto_scheduler.py
```

## 常用查询命令

### 查看消息数量
```bash
mysql -u root -pHyc174513 -D message_platform -e "SELECT 'people_theory' as source, COUNT(*) FROM mp_people_theory_messages UNION ALL SELECT 'qstheory', COUNT(*) FROM mp_qstheory_messages UNION ALL SELECT 'gmw_theory', COUNT(*) FROM mp_gmw_theory_messages UNION ALL SELECT 'cssn', COUNT(*) FROM mp_cssn_messages UNION ALL SELECT 'cctv_news', COUNT(*) FROM mp_cctv_news_messages UNION ALL SELECT 'xinhua', COUNT(*) FROM mp_xinhua_messages UNION ALL SELECT 'gmw', COUNT(*) FROM mp_gmw_messages UNION ALL SELECT 'guancha', COUNT(*) FROM mp_guancha_messages UNION ALL SELECT 'huanqiu', COUNT(*) FROM mp_huanqiu_messages UNION ALL SELECT 'thepaper', COUNT(*) FROM mp_thepaper_messages;"
```

### 查看知识点匹配进度
```bash
mysql -u root -pHyc174513 -D message_platform --default-character-set=utf8mb4 -e "SELECT knowledge_point_name, COUNT(*) as count, CASE WHEN COUNT(*) >= 3 THEN '✓' ELSE '✗' END as status FROM iptc_message_knowledge_relations GROUP BY knowledge_point_name ORDER BY count DESC;"
```

### 查看生成的案例
```bash
mysql -u root -pHyc174513 -D message_platform --default-character-set=utf8mb4 -e "SELECT title, tags, created_at FROM iptc_cases ORDER BY created_at DESC LIMIT 5;"
```

## 系统管理

### 停止所有服务
```powershell
# 在Worker终端按 Ctrl+C
# 在Beat终端按 Ctrl+C
# 在Scheduler终端按 Ctrl+C
```

### 检查系统状态
```bash
# 检查Redis
redis-cli ping

# 检查数据库
mysql -u root -pHyc174513 -D message_platform -e "SELECT COUNT(*) FROM mp_message_sources WHERE is_active = 1;"

# 检查消息总数
mysql -u root -pHyc174513 -D message_platform -e "SELECT SUM(cnt) as total FROM (SELECT COUNT(*) as cnt FROM mp_people_theory_messages UNION ALL SELECT COUNT(*) FROM mp_cctv_news_messages UNION ALL SELECT COUNT(*) FROM mp_xinhua_messages) t;"
```

## 配置参数

### 采集器配置
- **消息源数量**：13个中国来源
- **采集频率**：3600秒（1小时）
- **数据表**：mp_{source_name}_messages
- **配置位置**：数据库mp_message_sources表

### 案例生成阈值
文件：`backend/scripts/batch_match_cases.py`
```python
SIMILARITY_THRESHOLD = 0.6          # 相似度阈值
CASE_GENERATION_THRESHOLD = 3       # 知识点需关联≥3条消息
```

## 完整文档

详细说明请参考：`IPTC案例生成系统使用指南.md`
