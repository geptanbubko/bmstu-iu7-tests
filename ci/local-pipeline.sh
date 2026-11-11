#!/usr/bin/env bash
# Локальный аналог CI: unit → integration → e2e в Docker + Allure-отчёт.
# Каждый запуск получает свой стенд и свой каталог результатов, поэтому
# несколько разработчиков (или терминалов) могут запускать его одновременно.
#
#   bash ci/local-pipeline.sh            # из локальной копии
#   REPO_URL=https://github.com/<owner>/<repo>.git GIT_REF=lab2 bash ci/local-pipeline.sh
set -uo pipefail
cd "$(dirname "$0")/.."

run_id="$(id -un 2>/dev/null | tr -cd 'a-z0-9' | cut -c1-12)-$(date +%s)-$RANDOM"
export STAND="wildlife-$run_id"
export RESULTS_DIR="./results/$run_id"
export CAPTURE_DIR="./traffic/$run_id"
export TESTS_IMAGE="wildlife-tests:$run_id"
mkdir -p "$RESULTS_DIR"
# Абсолютный путь для docker -v: в Git Bash нужен вид C:/..., иначе MSYS портит аргумент.
results_host="$(cd "$RESULTS_DIR" && { pwd -W 2>/dev/null || pwd; })"

docker build -f docker/tests.Dockerfile \
    --build-arg REPO_URL="${REPO_URL:-}" --build-arg GIT_REF="${GIT_REF:-}" \
    -t "$TESTS_IMAGE" . || exit 1

failed=""
run_stage() {
    local stage="$1"
    if [ -n "$failed" ]; then
        RESULTS_ROOT="$RESULTS_DIR" bash ci/run-tests.sh skipped "$stage" \
            "Этап не запускался: упал этап $failed"
        return
    fi
    echo "===== $stage ====="
    if [ "$stage" = e2e ]; then
        bash ci/stand.sh all || failed="$stage"
    else
        MSYS_NO_PATHCONV=1 docker run --rm -v "$results_host:/results" "$TESTS_IMAGE" "$stage" || failed="$stage"
    fi
}

run_stage unit
run_stage integration
run_stage e2e
docker image rm "$TESTS_IMAGE" >/dev/null 2>&1 || true

if command -v allure >/dev/null 2>&1; then
    allure generate "$RESULTS_DIR"/unit "$RESULTS_DIR"/integration "$RESULTS_DIR"/e2e \
        --clean --single-file -o "$RESULTS_DIR/report" \
        && echo "Отчёт: $RESULTS_DIR/report/index.html"
fi

if [ -n "$failed" ]; then
    echo "Конвейер упал на этапе: $failed"
    exit 1
fi
echo "Конвейер пройден: unit → integration → e2e"
