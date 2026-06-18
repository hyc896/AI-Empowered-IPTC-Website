#!/bin/bash
set -e

# ============================================
# 逐光智慧思政平台 - 一键部署脚本
# 在阿里云 Ubuntu 22.04 服务器上执行
# ============================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()   { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "=========================================="
echo "  逐光智慧思政平台 - 部署开始"
echo "=========================================="
echo ""

# ------------------------------------------
# 1. 安装 Docker（如果没有）
# ------------------------------------------
if ! command -v docker &> /dev/null; then
    warn "Docker 未安装，正在安装..."
    apt-get update
    apt-get install -y ca-certificates curl gnupg
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    systemctl enable docker
    systemctl start docker
    log "Docker 安装完成"
else
    log "Docker 已安装: $(docker --version)"
fi

# 确保 docker compose 可用
if docker compose version &> /dev/null; then
    COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE="docker-compose"
else
    error "docker compose 不可用，请检查 Docker 安装"
fi
log "使用: $COMPOSE"

# ------------------------------------------
# 2. 构建前端
# ------------------------------------------
log "构建前端..."

# 在 node 容器中构建前端 dist
docker run --rm \
    -v "$SCRIPT_DIR/frontend:/app" \
    -w /app \
    node:18-alpine \
    sh -c "npm install --registry=https://registry.npmmirror.com && npm run build"

log "前端构建完成"

# ------------------------------------------
# 3. 将前端 dist 复制到 Docker volume
# ------------------------------------------
log "部署前端静态文件到 volume..."

# 先创建 volume（如果不存在）
docker volume create zhuguang_frontend_dist 2>/dev/null || true

# 用临时容器把 dist 内容复制到 volume
docker run --rm \
    -v "$SCRIPT_DIR/frontend/dist:/src:ro" \
    -v zhuguang_frontend_dist:/dest \
    alpine \
    sh -c "rm -rf /dest/* && cp -r /src/* /dest/"

log "前端静态文件已部署"

# ------------------------------------------
# 4. 启动所有服务
# ------------------------------------------
log "启动 Docker 服务..."
$COMPOSE down --remove-orphans 2>/dev/null || true
$COMPOSE up -d --build

# ------------------------------------------
# 5. 等待服务就绪
# ------------------------------------------
log "等待 MySQL 就绪..."
RETRIES=30
until docker exec $(docker ps -qf "name=mysql" | head -1) mysqladmin ping -h localhost -u root -piptc_prod_2025 --silent 2>/dev/null; do
    RETRIES=$((RETRIES - 1))
    if [ $RETRIES -le 0 ]; then
        error "MySQL 启动超时"
    fi
    sleep 2
done
log "MySQL 已就绪"

log "等待后端就绪..."
RETRIES=20
until curl -sf http://localhost/health > /dev/null 2>&1; do
    RETRIES=$((RETRIES - 1))
    if [ $RETRIES -le 0 ]; then
        warn "后端健康检查超时，查看日志..."
        $COMPOSE logs --tail=30 backend
        break
    fi
    sleep 3
done

# 后端启动时会自动通过 init_database() 创建表
log "数据库表已自动初始化"

# ------------------------------------------
# 6. 检查服务状态
# ------------------------------------------
echo ""
echo "=========================================="
echo "  服务状态"
echo "=========================================="
$COMPOSE ps

# ------------------------------------------
# 7. 输出访问信息
# ------------------------------------------
SERVER_IP=$(curl -sf http://ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')

echo ""
echo "=========================================="
echo -e "  ${GREEN}部署完成！${NC}"
echo "=========================================="
echo ""
echo "  访问地址: http://${SERVER_IP}"
echo "  API 文档: http://${SERVER_IP}/api/v1/auth"
echo ""
echo "  常用命令:"
echo "    查看日志:   $COMPOSE logs -f"
echo "    重启服务:   $COMPOSE restart"
echo "    停止服务:   $COMPOSE down"
echo "    查看状态:   $COMPOSE ps"
echo ""
