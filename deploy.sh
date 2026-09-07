#!/bin/bash
# Redeploy de BottleCRM (founderslab) en la VPS: git pull + build + up.
# Uso: ./deploy.sh [servicio ...]
#   default: backend celery-worker celery-beat frontend  (los que se construyen
#   desde el repo). `db` y `redis` son imágenes: se levantan solos vía
#   depends_on si no están corriendo, no se reconstruyen.
#
# migrate / collectstatic / compilemessages corren dentro del entrypoint del
# contenedor `backend` en cada arranque, así que pull + up ES el upgrade
# completo -- no hay paso de migración aparte.
#
# Requiere una copia ya clonada en la VPS con .env.prod configurado
# (ver docs/self-hosting/hostinger-traefik.md). No reemplaza el setup inicial,
# solo los deploys siguientes.

set -euo pipefail

cd "$(dirname "$0")"

COMPOSE=(docker compose -f docker-compose.prod.yml)

if [ "$#" -gt 0 ]; then
    SERVICES=("$@")
else
    SERVICES=(backend celery-worker celery-beat frontend)
fi

if [ ! -f .env.prod ]; then
    echo "Error: falta .env.prod en $(pwd) -- cp .env.prod.example .env.prod y completalo." >&2
    exit 1
fi

# Los bind mounts (BD, media) viven bajo $DATA_DIR. Tiene que ser una ruta
# ABSOLUTA y FUERA del checkout, o un `git clean -fdx` borraría la base.
DATA_DIR="${DATA_DIR:-/opt/crm-founderslab-data}"
case "$DATA_DIR" in
    /*) ;;
    *) echo "Error: DATA_DIR debe ser ruta absoluta, no '$DATA_DIR'." >&2; exit 1 ;;
esac
case "$DATA_DIR/" in
    "$(pwd -P)"/*)
        echo "Error: DATA_DIR ('$DATA_DIR') está dentro del repo ('$(pwd -P)')." >&2
        echo "Movelo fuera del checkout -- si no, git clean se lleva la BD." >&2
        exit 1 ;;
esac
mkdir -p "$DATA_DIR"/postgres "$DATA_DIR"/media "$DATA_DIR"/staticfiles
export DATA_DIR

if ! docker network inspect n8n_default >/dev/null 2>&1; then
    echo "Error: no existe la red externa 'n8n_default' -- ¿está corriendo Traefik?" >&2
    exit 1
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "Error: hay cambios locales sin commitear en $(pwd) -- resolvé eso antes del pull" >&2
    echo "(git status, y git stash o git checkout según corresponda)." >&2
    git status --short
    exit 1
fi

before=$(git rev-parse --short HEAD)
echo "==> git pull (desde $before)"
git pull --ff-only
after=$(git rev-parse --short HEAD)

if [ "$before" = "$after" ]; then
    echo "==> Sin commits nuevos ($after) -- reconstruyo igual por si cambió la imagen base."
fi

echo "==> docker compose build ${SERVICES[*]}"
"${COMPOSE[@]}" build "${SERVICES[@]}"

echo "==> docker compose up -d ${SERVICES[*]}"
"${COMPOSE[@]}" up -d "${SERVICES[@]}"

echo "==> Logs recientes (Ctrl+C corta esto, el contenedor sigue corriendo):"
"${COMPOSE[@]}" logs --tail=40 backend

echo
echo "==> Deploy listo: $before -> $after"
echo "==> Verificar:  https://api-crm.founderslab.dev/healthz/   y   https://crm.founderslab.dev/"
