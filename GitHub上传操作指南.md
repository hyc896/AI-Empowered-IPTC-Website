# GitHub 上传操作指南

## 项目信息
- **项目路径**: `D:\AI-Empowered IPTC Website\一期`
- **目标仓库**: https://github.com/hyc896/AI-Empowered-IPTC-Website.git
- **排除内容**: global-news-dashboard 前端（已在.gitignore中配置）

---

## 方法一：使用批处理脚本（推荐）

### 步骤1：打开命令提示符（cmd）
1. 按 `Win + R`
2. 输入 `cmd` 并回车
3. 或者直接在开始菜单搜索"命令提示符"

### 步骤2：执行批处理脚本
在cmd窗口中依次执行以下命令：

```cmd
cd /d "D:\AI-Empowered IPTC Website\一期"
upload_to_github.bat
```

### 步骤3：按照提示完成上传
脚本会自动执行以下操作：
- 添加所有更改到暂存区
- 提交更改
- 配置远程仓库
- 推送到GitHub

---

## 方法二：使用Python脚本

### 步骤1：打开命令提示符（cmd）
同上

### 步骤2：执行Python脚本
```cmd
cd /d "D:\AI-Empowered IPTC Website\一期"
python upload_to_github.py
```

如果系统有多个Python版本，可能需要使用：
```cmd
python3 upload_to_github.py
```
或
```cmd
py upload_to_github.py
```

---

## 方法三：手动执行Git命令（最可靠）

### 步骤1：打开命令提示符
同上

### 步骤2：切换到项目目录
```cmd
cd /d "D:\AI-Empowered IPTC Website\一期"
```

### 步骤3：检查Git状态
```cmd
git status
```

### 步骤4：添加所有更改
```cmd
git add .
```

### 步骤5：提交更改
```cmd
git commit -m "Initial commit: Upload Phase 1 project (exclude global-news-dashboard)"
```

### 步骤6：移除旧的远程仓库（如果有）
```cmd
git remote remove origin
```
*注意：如果提示没有origin，忽略即可*

### 步骤7：添加新的远程仓库
```cmd
git remote add origin https://github.com/hyc896/AI-Empowered-IPTC-Website.git
```

### 步骤8：确保使用main分支
```cmd
git branch -M main
```

### 步骤9：推送到GitHub（首次推送）
```cmd
git push -u origin main -f
```

*注意：`-f` 参数表示强制推送，用于首次推送到空仓库*

### 步骤10：验证远程仓库配置
```cmd
git remote -v
```

应该看到：
```
origin  https://github.com/hyc896/AI-Empowered-IPTC-Website.git (fetch)
origin  https://github.com/hyc896/AI-Empowered-IPTC-Website.git (push)
```

---

## 已排除的内容（.gitignore配置）

以下内容**不会**被上传到GitHub：

### 前端项目
- ✅ `global-news-dashboard/` - 完整排除

### 依赖和缓存
- `node_modules/`
- `__pycache__/`
- `*.pyc`

### 数据文件
- `data/chromadb/`
- `data/chromadb_mp/`
- `*.db`
- `*.sqlite3`

### 日志和临时文件
- `logs/`
- `*.log`
- `celerybeat-schedule.*`

### 环境配置
- `.env`
- `.env.local`

### 大型文件
- `full_database_dump.sql` (32MB+)
- `*.dump`

---

## 验证上传结果

### 步骤1：访问GitHub仓库
在浏览器中打开：
https://github.com/hyc896/AI-Empowered-IPTC-Website

### 步骤2：检查文件列表
确认以下文件/文件夹存在：
- ✅ `backend/`
- ✅ `iptc-dashboard/`
- ✅ `README.md`
- ✅ `config.yaml`
- ✅ `requirements.txt`
- ✅ `init_db.sql`
- ✅ `.gitignore`

### 步骤3：确认排除成功
确认以下文件/文件夹**不存在**：
- ❌ `global-news-dashboard/`
- ❌ `data/chromadb/`
- ❌ `data/chromadb_mp/`
- ❌ `logs/`
- ❌ `node_modules/`
- ❌ `full_database_dump.sql`

---

## 常见问题

### Q1：推送时提示权限错误
**错误信息**：
```
remote: Permission to hyc896/AI-Empowered-IPTC-Website.git denied
```

**解决方案**：
1. 检查GitHub账户是否已登录
2. 配置Git凭据：
   ```cmd
   git config --global user.name "your_username"
   git config --global user.email "your_email@example.com"
   ```
3. 使用GitHub Personal Access Token（PAT）：
   - 访问 https://github.com/settings/tokens
   - 生成新的Token
   - 推送时使用Token作为密码

### Q2：推送时提示仓库不为空
**错误信息**：
```
! [rejected]        main -> main (fetch first)
```

**解决方案**：
使用强制推送（已在命令中包含）：
```cmd
git push -u origin main -f
```

### Q3：提示已存在origin远程仓库
**错误信息**：
```
fatal: remote origin already exists
```

**解决方案**：
先移除再添加：
```cmd
git remote remove origin
git remote add origin https://github.com/hyc896/AI-Empowered-IPTC-Website.git
```

### Q4：.gitignore没有生效，不该上传的文件被添加了
**解决方案**：
清除Git缓存并重新添加：
```cmd
git rm -r --cached .
git add .
git commit -m "Fix .gitignore"
git push -u origin main -f
```

---

## 后续操作

### 克隆仓库到其他电脑
```cmd
git clone https://github.com/hyc896/AI-Empowered-IPTC-Website.git
cd AI-Empowered-IPTC-Website
```

### 拉取最新更改
```cmd
git pull origin main
```

### 推送新的更改
```cmd
git add .
git commit -m "描述你的更改"
git push origin main
```

---

## 联系与支持

如果上传过程中遇到问题，请检查：
1. ✅ Git是否已安装：`git --version`
2. ✅ 网络连接是否正常
3. ✅ GitHub仓库是否已创建且为空
4. ✅ GitHub账户是否有推送权限

---

**创建时间**: 2026-01-17  
**仓库地址**: https://github.com/hyc896/AI-Empowered-IPTC-Website.git
