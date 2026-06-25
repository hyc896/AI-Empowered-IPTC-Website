#!/bin/bash
set -u

# Read-only server audit for the IPTC deployment.
# Run on the Aliyun server from the project root:
#   bash server_readonly_audit.sh

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if docker compose version >/dev/null 2>&1; then
    COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE="docker-compose"
else
    warn "docker compose is not available"
    exit 1
fi

echo "IPTC read-only server audit"
echo "============================================================"
echo "time: $(date -Is)"
echo "cwd:  $SCRIPT_DIR"
echo

log "Docker"
docker --version || true
$COMPOSE version || true
echo

log "Compose services"
$COMPOSE ps || true
echo

log "Container resource snapshot"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" || true
echo

log "Docker volumes"
docker volume ls | grep 'iptc-platform' || true
echo

log "ChromaDB volume item count"
docker run --rm -v iptc-platform_chromadb_data:/dest alpine sh -c \
    'echo "items=$(ls -A /dest 2>/dev/null | wc -l)"; find /dest -maxdepth 2 -type f | head -20' || true
echo

log "MySQL table counts"
MYSQL_CONTAINER="$(docker ps -qf "name=iptc-platform-mysql" | head -1)"
if [ -n "$MYSQL_CONTAINER" ]; then
    docker exec "$MYSQL_CONTAINER" sh -c '
        mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -N -e "
        SELECT \"iptc_main.mp_message_sources\", COUNT(*) FROM iptc_main.mp_message_sources;
        SELECT \"iptc_main.iptc_cases\", COUNT(*) FROM iptc_main.iptc_cases;
        SELECT \"iptc_main.iptc_knowledge_point_stats\", COUNT(*) FROM iptc_main.iptc_knowledge_point_stats;
        SELECT \"iptc_practice.users\", COUNT(*) FROM iptc_practice.users;
        SELECT \"iptc_practice.venues\", COUNT(*) FROM iptc_practice.venues;
        "
    ' || true

    echo
    log "Active message sources"
    docker exec "$MYSQL_CONTAINER" sh -c '
        mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -N -e "
        SELECT name, is_active,
               JSON_UNQUOTE(JSON_EXTRACT(config, \"$.region\")) AS region,
               JSON_UNQUOTE(JSON_EXTRACT(config, \"$.source_type\")) AS source_type
        FROM iptc_main.mp_message_sources
        WHERE is_active = 1
        ORDER BY name;
        "
    ' || true
else
    warn "mysql container not found"
fi
echo

log "Collector deployment doctor"
$COMPOSE exec -T collector-backend python -X utf8 backend/scripts/deployment_doctor.py || true
echo

log "Recent collector logs"
$COMPOSE logs --tail=120 collector-backend collector-celery-worker collector-celery-beat || true
