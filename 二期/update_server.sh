#!/bin/bash
set -e

echo "=== 逐光平台服务器更新脚本 ==="

# 1. 克隆最新代码
echo "[1/5] 拉取最新代码..."
cd /opt
if [ -d "zhuguang_src" ]; then
    cd zhuguang_src && git pull origin master
else
    git clone https://github.com/hyc896/AI-Empowered-IPTC-Website.git zhuguang_src
    cd zhuguang_src
fi

# 2. 安装 Node.js（如果没有）
echo "[2/5] 检查 Node.js..."
if ! command -v node &> /dev/null; then
    echo "安装 Node.js 18..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
    apt-get install -y nodejs
fi
echo "Node.js 版本: $(node -v)"

# 3. 构建前端
echo "[3/5] 构建前端..."
cd /opt/zhuguang_src/二期/frontend
npm install
npm run build

# 4. 部署前端到 nginx
echo "[4/5] 部署前端..."
rm -rf /var/www/html/*
cp -r dist/* /var/www/html/
nginx -s reload
echo "前端部署完成"

# 5. 更新后端代码
echo "[5/5] 更新后端代码..."
cp -r /opt/zhuguang_src/二期/backend/* /opt/zhuguang/backend/

# 6. 导入知识点数据
echo "[6] 导入知识点..."
mkdir -p /opt/zhuguang/backend/data
cp /opt/zhuguang_src/一期/backend/data/knowledge_points.json /opt/zhuguang/backend/data/

/opt/zhuguang/venv/bin/python -c "
import json, sys
sys.path.insert(0, '/opt/zhuguang/backend')
import os
os.environ.setdefault('ENV_FILE', '/opt/zhuguang/config/.env')

from database import engine
from database.models import KnowledgePoint, Base
from sqlalchemy.orm import Session
from sqlalchemy import text

with Session(engine) as session:
    count = session.execute(text('SELECT COUNT(*) FROM knowledge_points')).scalar()
    if count > 0:
        print(f'知识点表已有 {count} 条数据，跳过导入')
        sys.exit(0)

with open('/opt/zhuguang/backend/data/knowledge_points.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

book_map = {
    '马克思主义基本原理': 'marxism',
    '思想道德与法治': 'morality',
    '习近平新时代中国特色社会主义思想概论': 'xi_thought'
}

with Session(engine) as session:
    for kp in data:
        point = KnowledgePoint(
            name=kp['name'],
            chapter=kp.get('chapter', ''),
            category=book_map.get(kp.get('book_name', ''), 'other'),
            book_name=kp.get('book_name', ''),
            theory_description=kp.get('theory_description', ''),
            application_scenarios=json.dumps(kp.get('application_scenarios', []), ensure_ascii=False),
            typical_keywords=json.dumps(kp.get('typical_keywords', []), ensure_ascii=False)
        )
        session.add(point)
    session.commit()
    print(f'导入完成: {len(data)} 个知识点')
"

# 7. 重启后端服务
systemctl restart zhuguang-backend
systemctl restart zhuguang-celery
echo ""
echo "=== 更新完成！==="
echo "访问 http://139.196.203.83 查看效果"
