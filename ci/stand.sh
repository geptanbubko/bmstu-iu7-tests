#!/usr/bin/env bash
# Управление тестовым стендом в Docker (docker-compose.test.yml).
#
#   ci/stand.sh up       — собрать и поднять стенд, дождаться healthcheck
#   ci/stand.sh e2e      — прогнать E2E в контейнере тестов против стенда
#   ci/stand.sh cleanup  — завершить все сессии + откатить хранилище + проверить целостность
#   ci/stand.sh replay   — curl-имитация E2E с захватом трафика tcpdump → $CAPTURE_DIR
#   ci/stand.sh down     — удалить контейнеры, сеть и том стенда
#   ci/stand.sh all      — up → e2e → (всегда) cleanup → down
#
# STAND — имя compose-проекта. Если не задано, генерируется уникальное:
# два разработчика (или два терминала) получают независимые стенды.
set -euo pipefail
cd "$(dirname "$0")/.."
# Git Bash (Windows) иначе переписывает /data/... в C:/Program Files/Git/data/...
export MSYS_NO_PATHCONV=1

export STAND="${STAND:-wildlife-$(id -un 2>/dev/null | tr -cd 'a-z0-9' | cut -c1-12)-$(date +%s)-$RANDOM}"
export RESULTS_DIR="${RESULTS_DIR:-./results}"
export CAPTURE_DIR="${CAPTURE_DIR:-./traffic}"
DB=/data/wildlife.db

compose() { docker compose -f docker-compose.test.yml -p "$STAND" "$@"; }

cmd_up() {
    compose up -d --build --wait app
    echo "[stand] $STAND поднят: http://localhost:$(compose port app 5000 | awk -F: '{print $NF}')"
}

cmd_e2e() {
    mkdir -p "$RESULTS_DIR"
    compose run --rm tests e2e
}

cmd_cleanup() {
    compose exec -T app python ci/stand_cleanup.py
    compose exec -T app python db/dbctl.py rollback --db "$DB"
    compose exec -T app python db/dbctl.py verify --db "$DB"
}

cmd_replay() {
    mkdir -p "$CAPTURE_DIR"
    compose up -d capture
    sleep 2
    local code=0
    compose run --rm replay || code=$?
    sleep 1
    compose stop capture
    ls -l "$CAPTURE_DIR"
    return "$code"
}

cmd_down() {
    compose --profile tests --profile capture down -v --remove-orphans
}

cmd_all() {
    # Прерывание (Ctrl+C) тоже приводит к откату хранилища и удалению стенда.
    trap 'cmd_cleanup || true; cmd_down; exit 130' INT TERM
    local code=0
    cmd_up || code=$?
    [ "$code" -ne 0 ] || cmd_e2e || code=$?
    if ! cmd_cleanup; then
        echo "[stand] откат хранилища / завершение сессий не удались"
        [ "$code" -ne 0 ] || code=1
    fi
    cmd_down
    return "$code"
}

case "${1:-}" in
    up|e2e|cleanup|replay|down|all) "cmd_$1" ;;
    *) sed -n '2,13p' "$0"; exit 2 ;;
esac
