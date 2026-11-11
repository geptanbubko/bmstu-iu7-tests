#!/bin/sh
# Имитация E2E-сценария (tests/e2e/population_monitoring_scenario_e2e.py) средствами curl.
# Запуск: ci/stand.sh replay (в контейнере alpine рядом со стендом; трафик пишет tcpdump)
# или вручную: BASE_URL=http://localhost:<порт> LOG=./curl-replay.log sh e2e/curl/replay.sh
set -eu

if ! command -v jq >/dev/null 2>&1 || ! command -v curl >/dev/null 2>&1; then
    apk add --no-cache curl jq >/dev/null
fi

API="${BASE_URL:-http://localhost:5000}/api/v1"
LOG="${LOG:-/capture/curl-replay.log}"
TAG="${RUN_TAG:-curl-$(date +%s)}"
: > "$LOG"

# call METHOD PATH [TOKEN] [JSON] → тело ответа в stdout, код ответа в $LOG
call() {
    method=$1; path=$2; token=${3:-}; body=${4:-}
    set -- -sS -X "$method" "$API$path" -H "Accept: application/json" -w '\n%{http_code}'
    [ -n "$token" ] && set -- "$@" -H "Authorization: Bearer $token"
    [ -n "$body" ] && set -- "$@" -H "Content-Type: application/json" --data "$body"
    response=$(curl "$@")
    code=$(printf '%s\n' "$response" | tail -n 1)
    json=$(printf '%s\n' "$response" | sed '$d')
    printf '>>> %s %s %s\n<<< HTTP %s %s\n\n' "$method" "$path" "$body" "$code" "$json" >> "$LOG"
    printf '%s' "$json"
}

call GET /health >/dev/null
ADMIN=$(call POST /session "" '{"role":"admin"}' | jq -r .token)
RESEARCHER=$(call POST /session "" '{"role":"researcher"}' | jq -r .token)

SPECIES=$(call POST /species "$ADMIN" "{\"scientific_name\":\"Vulpes lagopus $TAG\",\"common_name\":\"Песец\"}" | jq -r .id)
LOCATION=$(call POST /locations "$ADMIN" "{\"name\":\"Хибины $TAG\",\"region\":\"Мурманская область\"}" | jq -r .id)
PERSON=$(call POST /researchers "$ADMIN" "{\"full_name\":\"Тестов Т.Т. $TAG\",\"organization\":\"ИУ7\"}" | jq -r .id)

for pair in 2025-04-10:3 2025-05-10:5 2025-06-10:6 2025-07-10:8 2025-08-10:9; do
    day=${pair%%:*}; count=${pair##*:}
    call POST /observations "$RESEARCHER" \
        "{\"species_id\":$SPECIES,\"location_id\":$LOCATION,\"researcher_id\":$PERSON,\"observation_date\":\"$day\",\"individuals_count\":$count,\"notes\":\"$TAG\"}" >/dev/null
done

call GET /observations "$RESEARCHER" >/dev/null
TREND=$(call GET "/analytics/population?species_id=$SPECIES&date_from=2025-01-01&date_to=2025-12-31&location_id=$LOCATION" "$RESEARCHER" | jq -r .has_trend)

call DELETE /session "$ADMIN" >/dev/null
call DELETE /session "$RESEARCHER" >/dev/null

echo "[replay] species=$SPECIES location=$LOCATION researcher=$PERSON has_trend=$TREND (лог: $LOG)"
[ "$TREND" = "true" ]
