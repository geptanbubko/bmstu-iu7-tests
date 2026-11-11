#!/usr/bin/env bash
# Запуск одного этапа тестов. Точка входа тестового контейнера (docker/tests.Dockerfile).
#
#   ci/run-tests.sh unit
#   ci/run-tests.sh integration      # + два повторных прогона на одном инстансе хранилища
#   ci/run-tests.sh e2e              # нужен стенд: WILDLIFE_E2E_URL
#   ci/run-tests.sh skipped <stage> [причина]   # этап не запускался → результаты Allure со статусом skipped
#
# Сырые результаты Allure: $RESULTS_ROOT/<stage> (по умолчанию ./results/<stage>).
set -uo pipefail
cd "$(dirname "$0")/.."

stage="${1:?укажите этап: unit | integration | e2e | skipped <stage>}"
results_root="${RESULTS_ROOT:-results}"

run_pytest() {
    local target="$1"; shift
    python -m pytest "tests/$target" --alluredir="$results_root/$target" "$@"
}

case "$stage" in
    unit)
        run_pytest unit
        ;;

    integration)
        run_pytest integration --junitxml=/tmp/it-main.xml || exit $?

        # Требование 14: повторный запуск не меняет результат и не ломает хранилище.
        # Оба прогона работают с ОДНИМ постоянным инстансом: второй стартует только
        # если первый вернул хранилище в эталонное состояние (см. tests/integration/conftest.py).
        shared_db="$(mktemp -d)/wildlife-it-shared.db"
        for attempt in 1 2; do
            echo "== integration: повторный прогон $attempt на $shared_db"
            WILDLIFE_IT_DB="$shared_db" python -m pytest tests/integration -q --no-cov \
                -p no:cacheprovider --alluredir="/tmp/it-repeat-$attempt" \
                --junitxml="/tmp/it-repeat-$attempt.xml" || exit $?
        done
        python - /tmp/it-main.xml /tmp/it-repeat-1.xml /tmp/it-repeat-2.xml <<'PY' || exit $?
import sys
import xml.etree.ElementTree as ET

def outcome(path):
    cases = {}
    for case in ET.parse(path).iter("testcase"):
        status = "passed"
        for tag in ("failure", "error", "skipped"):
            if case.find(tag) is not None:
                status = tag
        cases[f"{case.get('classname')}::{case.get('name')}"] = status
    return cases

runs = [outcome(p) for p in sys.argv[1:]]
if any(run != runs[0] for run in runs[1:]):
    print("Результаты повторных прогонов integration различаются:", runs)
    sys.exit(1)
print(f"== integration: {len(runs)} прогона, результаты совпали ({len(runs[0])} тестов)")
PY
        ;;

    e2e)
        : "${WILDLIFE_E2E_URL:?не задан адрес стенда WILDLIFE_E2E_URL}"
        run_pytest e2e --no-cov
        ;;

    skipped)
        target="${2:?укажите этап, который не запускался}"
        reason="${3:-Этап не запускался: предыдущий этап конвейера завершился с ошибкой}"
        echo "== $target: помечается как skipped ($reason)"
        WILDLIFE_STAGE_SKIPPED="$reason" run_pytest "$target" --no-cov -q
        code=$?
        # 0 — всё пропущено; 5 — нечего собирать. Иное — ошибка сбора тестов.
        [ "$code" -eq 0 ] || [ "$code" -eq 5 ] || exit "$code"
        ;;

    *)
        echo "Неизвестный этап: $stage" >&2
        exit 2
        ;;
esac
