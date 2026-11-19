#!/usr/bin/env bash
# ЛР3: прогон микробенчмарка SQL vs ORM. Каждый прогон (реализация × сценарий × повтор) — отдельный
# контейнер из ОДНОГО образа: одинаковая конфигурация, свежий процесс, свежая БД в tmpfs, 1 ядро CPU.
#
#   bash ci/bench.sh            # build + verify + run + report
#   bash ci/bench.sh build | verify | run | report
#
# Настройки (переменные окружения):
#   BENCH_REPEATS=5                     повторов на пару «реализация × сценарий»
#   BENCH_SCENARIOS="read_by_id read_range write_insert mixed"
#   BENCH_CPU=1                         ядро, к которому привязан контейнер (--cpuset-cpus)
#   BENCH_ARGS="--measure 20000"        доп. аргументы python -m bench run
#   BENCH_OUT=results/bench             raw/ — сырые результаты, report/ — графики
set -euo pipefail
cd "$(dirname "$0")/.."

stage="${1:-all}"
image="${BENCH_IMAGE:-wildlife-bench:local}"
repeats="${BENCH_REPEATS:-5}"
scenarios="${BENCH_SCENARIOS:-read_by_id read_range write_insert mixed}"
out="${BENCH_OUT:-results/bench}"
extra_args="${BENCH_ARGS:-}"
if [ -z "${BENCH_CPU:-}" ]; then
    # ядро 0 обычно обслуживает прерывания — при возможности берём соседнее
    if [ "$(nproc 2>/dev/null || echo 1)" -gt 1 ]; then BENCH_CPU=1; else BENCH_CPU=0; fi
fi

export MSYS_NO_PATHCONV=1    # Git Bash на Windows: не переписывать пути внутри контейнера
mkdir -p "$out/raw" "$out/report"
host_out="$(cd "$out" && pwd)"
if command -v cygpath >/dev/null 2>&1; then host_out="$(cygpath -w "$host_out")"; fi

user_args=()
if [ "$(uname -s)" = "Linux" ]; then user_args=(--user "$(id -u):$(id -g)"); fi

build() {
    docker build -f docker/bench.Dockerfile -t "$image" .
}

run_one() {
    local target="$1" scenario="$2" repeat="$3"
    # shellcheck disable=SC2086
    docker run --rm \
        "${user_args[@]}" \
        --cpuset-cpus="$BENCH_CPU" --cpus=1 \
        --memory=1g --memory-swap=1g \
        --network=none \
        --tmpfs /bench-db:rw,size=512m,mode=1777 \
        -v "$host_out/raw:/results" \
        "$image" run --target "$target" --scenario "$scenario" --repeat "$repeat" $extra_args
}

run_all() {
    rm -f "$out"/raw/*.json.gz
    local started=$SECONDS
    for ((r = 0; r < repeats; r++)); do
        for scenario in $scenarios; do
            # порядок реализаций чередуется, чтобы дрейф машины не играл против одной из них
            if (( r % 2 == 0 )); then order="sql orm"; else order="orm sql"; fi
            for target in $order; do
                run_one "$target" "$scenario" "$r"
            done
        done
    done
    echo "[bench] $(ls "$out"/raw/*.json.gz | wc -l) прогонов за $((SECONDS - started)) с, CPU=$BENCH_CPU"
}

verify() {
    # честность сравнения: на одном плане SQL и ORM возвращают одно и то же
    docker run --rm "${user_args[@]}" --network=none --tmpfs /bench-db:rw,size=512m,mode=1777 \
        "$image" verify
}

report() {
    docker run --rm "${user_args[@]}" --network=none -v "$host_out:/out" \
        "$image" report --raw /out/raw --out /out/report
}

case "$stage" in
    build) build ;;
    verify) verify ;;
    run) run_all ;;
    report) report ;;
    all) build; verify; run_all; report ;;
    *) echo "usage: $0 [all|build|verify|run|report]" >&2; exit 2 ;;
esac
