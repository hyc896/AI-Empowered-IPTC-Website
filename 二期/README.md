# 逐光智慧思政平台 - 后端API

## 项目简介

逐光智慧思政平台是一个思政课理论与实践一体化平台，包含案例学习和实践活动两大板块。

## 技术栈

- **框架**: FastAPI 0.109.0
- **数据库**: MySQL 8.0 + SQLAlchemy 2.0
- **任务队列**: Celery 5.3 + Redis
- **认证**: JWT (python-jose)
- **密码加密**: bcrypt (passlib)

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制配置文件模板：
```bash
cp config/.env.example config/.env
```

编辑 `config/.env` 文件，配置数据库连接等信息。

### 3. 创建数据库

```sql
CREATE DATABASE iptc_practice CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 4. 初始化数据库表

```bash
cd backend
python -c "from database import init_database; init_database()"
```

### 5. 启动Redis（用于Celery）

```bash
redis-server
```

### 6. 启动Celery Worker

```bash
cd backend
celery -A celery_app worker --loglevel=info --pool=solo
```

### 7. 启动后端服务

```bash
cd backend
python main.py
```

服务启动后访问：
- API文档: http://localhost:8001/docs
- 健康检查: http://localhost:8001/health

## API文档

### 认证相关
- `POST /api/v1/auth/login` - 用户登录
- `POST /api/v1/auth/logout` - 用户登出
- `GET /api/v1/auth/me` - 获取当前用户信息
- `POST /api/v1/auth/change-password` - 修改密码
- `POST /api/v1/auth/register` - 注册用户（管理员）

### 知识点管理
- `POST /api/v1/knowledge-points` - 创建知识点
- `GET /api/v1/knowledge-points` - 获取知识点列表
- `GET /api/v1/knowledge-points/{id}` - 获取知识点详情
- `PUT /api/v1/knowledge-points/{id}` - 更新知识点
- `DELETE /api/v1/knowledge-points/{id}` - 删除知识点

### 实践方案
- `POST /api/v1/practice/plans/generate` - 生成实践方案（异步）
- `GET /api/v1/practice/plans/task/{task_id}` - 查询生成任务状态
- `GET /api/v1/practice/plans/{id}` - 获取方案详情
- `GET /api/v1/practice/plans` - 获取我的方案列表
- `DELETE /api/v1/practice/plans/{id}` - 删除方案

### 实践提交
- `POST /api/v1/submissions` - 创建提交（草稿）
- `GET /api/v1/submissions` - 获取提交列表
- `GET /api/v1/submissions/{id}` - 获取提交详情
- `PUT /api/v1/submissions/{id}` - 更新提交
- `POST /api/v1/submissions/{id}/files` - 上传附件
- `POST /api/v1/submissions/{id}/submit` - 正式提交审核
- `DELETE /api/v1/submissions/{id}` - 删除提交

### 审核管理
- `GET /api/v1/reviews/pending` - 获取待审核列表
- `POST /api/v1/reviews` - 提交审核结果
- `GET /api/v1/reviews/history` - 获取审核历史
- `GET /api/v1/reviews/{id}` - 获取审核详情

## 数据库表结构

### users - 用户表
- 学生、教师、管理员三种角色
- 支持学号/工号登录
- 密码bcrypt加密

### knowledge_points - 知识点表
- 三门课程的知识点体系
- 支持按课程、章节筛选

### practice_plans - 实践方案表
- AI生成的个性化实践方案
- 包含任务清单、推荐场馆等

### venues - 场馆表
- 实践场馆信息
- 支持手动维护和AI提取

### practice_submissions - 实践提交表
- 学生提交的实践作业
- 支持多种文件类型上传

### practice_reviews - 审核记录表
- 教师审核结果
- 包含评分和评语

## 开发规范

- 遵循RESTful API设计
- 使用Pydantic进行数据验证
- 所有API需要JWT认证（除登录接口）
- 代码注释使用中文
- 遵循KISS原则

## 常见问题

### 1. 数据库连接失败
检查 `.env` 文件中的数据库配置是否正确。

### 2. Celery任务执行失败
确保Redis已启动，并检查 `CELERY_BROKER_URL` 配置。

### 3. 文件上传失败
检查 `data/uploads` 目录是否存在且有写权限。

### 4. JWT token无效
检查 `JWT_SECRET_KEY` 配置，确保前后端使用相同的密钥。

## 许可证

MIT License
