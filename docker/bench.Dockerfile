# syntax=docker/dockerfile:1.7
# Образ микробенчмарка ЛР3. Один образ — одна конфигурация; каждый прогон запускается в НОВОМ
# контейнере из него (см. ci/bench.sh), поэтому у всех попыток одинаковые стартовые условия.
#   docker build -f docker/bench.Dockerfile -t wildlife-bench .
#   docker run --rm --cpuset-cpus=0 --cpus=1 --tmpfs /bench-db -v "$PWD/results/bench/raw:/results" \
#       wildlife-bench run --target sql --scenario read_by_id
FROM python:3.12.8-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=0 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/bench/src:/bench \
    BENCH_DB_DIR=/bench-db \
    BENCH_RAW=/results \
    MPLCONFIGDIR=/tmp/matplotlib

COPY bench/requirements.txt /tmp/bench-requirements.txt
RUN pip install -r /tmp/bench-requirements.txt

WORKDIR /bench
COPY src/wildlife_business ./src/wildlife_business
COPY src/wildlife_data ./src/wildlife_data
COPY bench ./bench

# Непривилегированный пользователь; БД — в tmpfs /bench-db (монтируется при запуске).
RUN useradd --uid 1000 --create-home bench && mkdir -p /bench-db /results && chown bench /bench-db /results
USER bench

ENTRYPOINT ["python", "-m", "bench"]
CMD ["list"]
