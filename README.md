# 消息平台 (Message Platform)

## 启动步骤

### 1. 环境准备

```
conda create -n personal_agent python=3.11 -y; conda activate personal_agent; pip install -r requirements.txt
```

### 2. 数据库初始化

**方式一：完整数据导入（推荐，包含历史数据）**
```
mysql -u root -p < full_database_dump.sql
```

**方式二：仅创建表结构（空库）**
```
mysql -u root -p < init_db.sql
```

**方式三：表结构 + 消息源配置**
```
mysql -u root -p < init_db.sql
mysql -u root -p message_platform < data_message_sources.sql
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env` 并修改数据库密码等配置。

主要配置项：
- `MYSQL_PASSWORD`: MySQL密码
- `LLM_API_KEY`: LLM服务API密钥
- `EMBEDDING_API_KEY`: Embedding服务API密钥

### 4. 启动服务

conda activate personal_agent; python start.py
cd global-news-dashboard; npm install; npm run dev
```

**启动Celery定时任务（可选）：**
```
conda activate personal_agent; celery -A backend.celery_app worker --loglevel=info --pool=solo
```

### 5. 验证服务

- API文档: http://localhost:11528/docs
- 健康检查: http://localhost:11528/health
- 前端仪表盘: http://localhost:5173 (如已启动)

## 数据库文件说明

| 文件 | 用途 |
|------|------|
| `init_db.sql` | 数据库表结构DDL（仅结构，无数据） |
| `data_message_sources.sql` | 消息源配置数据 |
| `full_database_dump.sql` | 完整数据库导出（结构+所有数据） |
