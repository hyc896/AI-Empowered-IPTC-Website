#!/bin/bash
set -e

# Unified deployment/update script for the Zhuguang IPTC platform.
# Run on the server from the repository root:
#   bash update_server.sh

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log()   { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[ERR]${NC} $1"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if command -v git &>/dev/null && [ -f ".gitmodules" ]; then
    log "Sync Git submodules..."
    git submodule sync --recursive
    git submodule update --init --recursive
fi

log "Working directory: $SCRIPT_DIR"

# ----------------------------------------------------------
# 0. Check/install Docker
# ----------------------------------------------------------
if ! command -v docker &>/dev/null; then
    warn "Docker is not installed. Installing..."
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
    log "Docker installed"
else
    log "Docker: $(docker --version)"
fi

if docker compose version &>/dev/null; then
    COMPOSE="docker compose"
elif command -v docker-compose &>/dev/null; then
    COMPOSE="docker-compose"
else
    error "docker compose is not available"
fi

# ----------------------------------------------------------
# 1. First-run data migration from bare-metal MySQL/ChromaDB
# ----------------------------------------------------------
MIGRATE_FLAG="$SCRIPT_DIR/.data_migrated"

if [ ! -f "$MIGRATE_FLAG" ] && command -v mysql &>/dev/null; then
    warn "Detected bare-metal MySQL. Trying to migrate old data into Docker volumes..."

    $COMPOSE up -d mysql
    log "Waiting for Docker MySQL, up to 60 seconds..."
    for i in $(seq 1 30); do
        docker exec $(docker ps -qf "name=iptc-platform-mysql") \
            mysqladmin ping -u root -piptc_prod_2025 --silent 2>/dev/null && break
        sleep 2
    done

    for DB in iptc_main iptc_practice; do
        if mysql -u root -piptc_prod_2025 -e "USE $DB;" 2>/dev/null; then
            log "Exporting $DB ..."
            mysqldump -u root -piptc_prod_2025 \
                --single-transaction --routines --triggers \
                "$DB" > "/tmp/${DB}_backup.sql"

            log "Importing $DB into Docker MySQL ..."
            docker exec -i $(docker ps -qf "name=iptc-platform-mysql") \
                mysql -u root -piptc_prod_2025 < "/tmp/${DB}_backup.sql"
            log "$DB migrated"
        else
            warn "$DB does not exist on bare-metal MySQL, skipped"
        fi
    done

    CHROMA_DIRS=(
        "/opt/zhuguang/backend/data/chromadb_new"
        "/opt/zhuguang/backend/data/chromadb"
        "/opt/zhuguang_src/一期/backend/data/chromadb_new"
        "/opt/zhuguang_src/一期/backend/data/chromadb"
        "$SCRIPT_DIR/一期/backend/data/chromadb_new"
    )
    for CHROMA_DIR in "${CHROMA_DIRS[@]}"; do
        if [ -d "$CHROMA_DIR" ] && [ "$(ls -A "$CHROMA_DIR")" ]; then
            log "Migrating ChromaDB data: $CHROMA_DIR"
            docker volume create iptc-platform_chromadb_data 2>/dev/null || true
            docker run --rm \
                -v "$CHROMA_DIR:/src:ro" \
                -v iptc-platform_chromadb_data:/dest \
                alpine sh -c "cp -r /src/. /dest/"
            log "ChromaDB migrated"
            break
        fi
    done

    touch "$MIGRATE_FLAG"
    log "Initial data migration completed"
fi

# Initialize an empty ChromaDB volume from repository data when available.
if [ -d "$SCRIPT_DIR/一期/backend/data/chromadb_new" ]; then
    docker volume create iptc-platform_chromadb_data >/dev/null 2>&1 || true
    CHROMA_ITEMS=$(docker run --rm -v iptc-platform_chromadb_data:/dest alpine sh -c "ls -A /dest 2>/dev/null | wc -l")
    if [ "$CHROMA_ITEMS" = "0" ]; then
        log "Initializing ChromaDB volume from 一期/backend/data/chromadb_new"
        docker run --rm \
            -v "$SCRIPT_DIR/一期/backend/data/chromadb_new:/src:ro" \
            -v iptc-platform_chromadb_data:/dest \
            alpine sh -c "cp -r /src/. /dest/"
    fi
fi

# ----------------------------------------------------------
# 2. Stop old systemd services if present
# ----------------------------------------------------------
for SVC in zhuguang-backend zhuguang-celery nginx; do
    if systemctl is-active --quiet "$SVC" 2>/dev/null; then
        warn "Stopping old service: $SVC"
        systemctl stop "$SVC" 2>/dev/null || true
        systemctl disable "$SVC" 2>/dev/null || true
    fi
done

# ----------------------------------------------------------
# 3. Build frontend
# ----------------------------------------------------------
log "Building frontend..."
docker run --rm \
    -v "$SCRIPT_DIR/二期/frontend:/app" \
    -w /app \
    node:18-alpine \
    sh -c "npm install --registry=https://registry.npmmirror.com && npm run build"
log "Frontend build completed"

# ----------------------------------------------------------
# 4. Copy frontend dist into Docker volume
# ----------------------------------------------------------
log "Deploying frontend volume..."
docker volume create iptc-platform_frontend_dist 2>/dev/null || true
docker run --rm \
    -v "$SCRIPT_DIR/二期/frontend/dist:/src:ro" \
    -v iptc-platform_frontend_dist:/dest \
    alpine sh -c "rm -rf /dest/* && cp -r /src/. /dest/"
log "Frontend volume updated"

# ----------------------------------------------------------
# 5. Start/rebuild services
# ----------------------------------------------------------
log "Starting all services..."
$COMPOSE pull mysql redis 2>/dev/null || true
$COMPOSE up -d --build --remove-orphans
log "Services started"

# ----------------------------------------------------------
# 6. Wait and run migrations/self-check
# ----------------------------------------------------------
log "Waiting for MySQL..."
for i in $(seq 1 30); do
    docker exec $(docker ps -qf "name=iptc-platform-mysql" | head -1) \
        mysqladmin ping -u root -piptc_prod_2025 --silent 2>/dev/null && break
    sleep 3
done
log "MySQL is ready"

log "Running database migrations..."
$COMPOSE exec -T collector-backend python -X utf8 backend/scripts/migrate_iptc_schema.py
$COMPOSE exec -T collector-backend python -X utf8 backend/scripts/seed_iptc_sources.py --activate-existing --disable-legacy
$COMPOSE exec -T practice-backend python -X utf8 migrations/0002_add_venue_case_link.py
log "Database migrations completed"

log "Restarting collector beat to reload schedules..."
$COMPOSE restart collector-celery-beat

log "Waiting for practice backend..."
for i in $(seq 1 20); do
    curl -sf http://localhost/health >/dev/null 2>&1 && break
    sleep 3
done

log "Running collector deployment doctor..."
if ! $COMPOSE exec -T collector-backend python -X utf8 backend/scripts/deployment_doctor.py; then
    warn "Collector deployment doctor failed; inspect the FAIL lines before triggering collection/matching"
fi

# ----------------------------------------------------------
# 7. Print status
# ----------------------------------------------------------
echo ""
echo "=========================================="
echo "  Service status"
echo "=========================================="
$COMPOSE ps

SERVER_IP=$(curl -sf http://ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
echo ""
echo "=========================================="
echo -e "  ${GREEN}Deployment completed${NC}"
echo "=========================================="
echo "  URL:             http://${SERVER_IP}"
echo "  Collector API:   http://${SERVER_IP}/api/v1/iptc/"
echo "  Graph API:       http://${SERVER_IP}/api/v1/knowledge-graph/"
echo ""
echo "  Common commands:"
echo "    Logs:      $COMPOSE logs -f [service]"
echo "    Restart:   $COMPOSE restart [service]"
echo "    Stop all:  $COMPOSE down"
