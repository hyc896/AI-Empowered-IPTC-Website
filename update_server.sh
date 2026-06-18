#!/bin/bash
set -e

# ============================================================
# 逐光智慧思政平台 - 服务器部署/更新脚本
# 在服务器上执行：bash update_server.sh
#
# 用法：
#   首次部署：bash update_server.sh
#   后续更新：git pull && bash update_server.sh
# ============================================================

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log()   { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
log "工作目录: $SCRIPT_DIR"

# ----------------------------------------------------------
# 0. 检查/安装 Docker
# ----------------------------------------------------------
if ! command -v docker &>/dev/null; then
    warn "Docker 未安装，正在安装..."
    apt-get update -qq
    apt-get install -y ca-certificates curl gnupg lsb-release
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update -qq
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    systemctl enable docker && systemctl start docker
    log "Docker 安装完成"
else
    log "Docker: $(docker --version)"
fi

# 确认 docker compose 可用
if docker compose version &>/dev/null; then
    COMPOSE="docker compose"
elif command -v docker-compose &>/dev/null; then
    COMPOSE="docker-compose"
else
    error "docker compose 不可用"
fi

# ----------------------------------------------------------
# 1. 数据迁移（仅首次：将裸机 MySQL 数据导入 Docker volume）
# ----------------------------------------------------------
MIGRATE_FLAG="$SCRIPT_DIR/.data_migrated"

if [ ! -f "$MIGRATE_FLAG" ] && command -v mysql &>/dev/null; then
    warn "检测到裸机 MySQL，尝试迁移旧数据到 Docker volume..."

    # 先启动 MySQL 容器（仅数据库）
    $COMPOSE up -d mysql
    log "等待 Docker MySQL 就绪（最多 60 秒）..."
    for i in $(seq 1 30); do
        docker exec $(docker ps -qf "name=iptc-platform-mysql") \
            mysqladmin ping -u root -piptc_prod_2025 --silent 2>/dev/null && break
        sleep 2
    done

    for DB in iptc_main iptc_practice; do
        if mysql -u root -piptc_prod_2025 -e "USE $DB;" 2>/dev/null; then
            log "导出 $DB ..."
            mysqldump -u root -piptc_prod_2025 \
                --single-transaction --routines --triggers \
                "$DB" > "/tmp/${DB}_backup.sql"

            log "导入 $DB 到 Docker MySQL ..."
            docker exec -i $(docker ps -qf "name=iptc-platform-mysql") \
                mysql -u root -piptc_prod_2025 < "/tmp/${DB}_backup.sql"
            log "$DB 迁移完成"
        else
            warn "$DB 在裸机上不存在，跳过"
        fi
    done

    # 迁移 ChromaDB 数据（如果有）
    CHROMA_DIRS=("/opt/zhuguang/backend/data/chromadb" "/opt/zhuguang_src/一期/backend/data/chromadb")
    for CHROMA_DIR in "${CHROMA_DIRS[@]}"; do
        if [ -d "$CHROMA_DIR" ] && [ "$(ls -A $CHROMA_DIR)" ]; then
            log "迁移 ChromaDB 数据: $CHROMA_DIR"
            docker volume create iptc-platform_chromadb_data 2>/dev/null || true
            docker run --rm \
                -v "$CHROMA_DIR:/src:ro" \
                -v iptc-platform_chromadb_data:/dest \
                alpine sh -c "cp -r /src/. /dest/"
            log "ChromaDB 迁移完成"
            break
        fi
    done

    touch "$MIGRATE_FLAG"
    log "数据迁移完成，后续更新不再执行此步骤"
fi

# ----------------------------------------------------------
# 2. 停止旧的 systemctl 服务（如果在跑）
# ----------------------------------------------------------
for SVC in zhuguang-backend zhuguang-celery nginx; do
    if systemctl is-active --quiet "$SVC" 2>/dev/null; then
        warn "停止旧服务: $SVC"
        systemctl stop "$SVC" 2>/dev/null || true
        systemctl disable "$SVC" 2>/dev/null || true
    fi
done

# ----------------------------------------------------------
# 3. 构建前端
# ----------------------------------------------------------
log "构建前端..."
docker run --rm \
    -v "$SCRIPT_DIR/二期/frontend:/app" \
    -w /app \
    node:18-alpine \
    sh -c "npm install --registry=https://registry.npmmirror.com && npm run build"
log "前端构建完成"

# ----------------------------------------------------------
# 4. 将前端 dist 写入 Docker volume
# ----------------------------------------------------------
log "部署前端到 volume..."
docker volume create iptc-platform_frontend_dist 2>/dev/null || true
docker run --rm \
    -v "$SCRIPT_DIR/二期/frontend/dist:/src:ro" \
    -v iptc-platform_frontend_dist:/dest \
    alpine sh -c "rm -rf /dest/* && cp -r /src/. /dest/"
log "前端 volume 更新完成"

# ----------------------------------------------------------
# 5. 启动/重建所有服务
# ----------------------------------------------------------
log "启动全部服务..."
$COMPOSE pull mysql redis 2>/dev/null || true   # 拉取基础镜像
$COMPOSE up -d --build --remove-orphans
log "服务启动完成"

# ----------------------------------------------------------
# 6. 等待健康检查
# ----------------------------------------------------------
log "等待 MySQL 就绪..."
for i in $(seq 1 30); do
    docker exec $(docker ps -qf "name=iptc-platform-mysql" | head -1) \
        mysqladmin ping -u root -piptc_prod_2025 --silent 2>/dev/null && break
    sleep 3
done
log "MySQL 已就绪"

log "等待二期后端就绪..."
for i in $(seq 1 20); do
    curl -sf http://localhost/health >/dev/null 2>&1 && break
    sleep 3
done

# ----------------------------------------------------------
# 7. 打印状态
# ----------------------------------------------------------
echo ""
echo "=========================================="
echo "  服务状态"
echo "=========================================="
$COMPOSE ps

SERVER_IP=$(curl -sf http://ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
echo ""
echo "=========================================="
echo -e "  ${GREEN}部署完成！${NC}"
echo "=========================================="
echo "  访问地址:    http://${SERVER_IP}"
echo "  一期 API:    http://${SERVER_IP}/api/v1/iptc/"
echo "  图谱 API:    http://${SERVER_IP}/api/v1/knowledge-graph/"
echo ""
echo "  常用命令:"
echo "    查看日志:   $COMPOSE logs -f [服务名]"
echo "    重启服务:   $COMPOSE restart [服务名]"
echo "    停止全部:   $COMPOSE down"
