"""Собственный инструмент микробенчмаркинга.

Один прогон = один процесс в отдельном контейнере:

    setup     — свежая БД, открытие реализации, первичное соединение (не измеряется по операциям);
    overhead  — калибровка: тот же цикл замера, но вместо операции пустая функция;
    warmup    — прогрев кусками по WARMUP_CHUNK операций, пока медиана двух соседних кусков
                не сойдётся в пределах WARMUP_TOLERANCE (но не меньше min и не больше max);
    measure   — измеряемая фаза: только она идёт в статистику;
    teardown  — «хвост» операций после замера: записывается, но в статистику не входит;
    cleanup   — закрытие реализации и удаление БД.

Каждая операция замеряется отдельно: t0 = perf_counter_ns(); op(arg); t1 = perf_counter_ns().
Аргументы и функции выбираются из заранее построенного плана до первого вызова таймера,
поэтому в замер попадает только вызов операции и сами вызовы таймера (это и есть overhead).
"""
from __future__ import annotations

import gc
import os
import platform
import random
import shutil
import sqlite3
import statistics
import sys
import tempfile
import time
from array import array
from dataclasses import dataclass
from datetime import datetime, timezone

from bench import dataset
from bench.scenarios import SCENARIOS, TARGETS, open_target

PERCENTILES = (0.5, 0.75, 0.9, 0.95, 0.99)


@dataclass(frozen=True)
class Config:
    warmup_min: int = 2_000
    warmup_max: int = 20_000
    warmup_chunk: int = 500
    warmup_tolerance: float = 0.05
    measure: int = 20_000
    teardown: int = 1_000
    calibration: int = 50_000

    def __post_init__(self) -> None:
        if self.measure < 100:
            raise ValueError("Нужно не меньше 100 измеряемых испытаний")


def _noop(_arg) -> None:
    return None


def _timed_loop(fns, args, start: int, count: int, origin: int) -> tuple[array, array]:
    """Горячий цикл замера. Локальные имена — чтобы не платить за поиск глобалей в замере."""
    timer = time.perf_counter_ns
    stamps = array("q", bytes(8 * count))
    latencies = array("q", bytes(8 * count))
    for j in range(count):
        fn = fns[start + j]
        arg = args[start + j]
        t0 = timer()
        fn(arg)
        t1 = timer()
        stamps[j] = t0 - origin
        latencies[j] = t1 - t0
    return stamps, latencies


def percentile(sorted_values, p: float) -> float:
    """Перцентиль с линейной интерполяцией (как numpy.percentile по умолчанию)."""
    if not sorted_values:
        return float("nan")
    k = (len(sorted_values) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(sorted_values) - 1)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (k - lo)


def summarize(latencies) -> dict:
    values = sorted(latencies)
    return {
        "count": len(values),
        "min": values[0],
        "max": values[-1],
        "mean": statistics.fmean(values),
        "stdev": statistics.pstdev(values),
        "percentiles": {str(p): percentile(values, p) for p in PERCENTILES},
    }


def _calibrate(count: int, origin: int) -> dict:
    fns = [_noop] * count
    args = [None] * count
    _timed_loop(fns, args, 0, min(count, 5_000), origin)  # прогрев самого цикла
    _, latencies = _timed_loop(fns, args, 0, count, origin)
    timer = time.perf_counter_ns
    deltas = []
    for _ in range(10_000):
        a = timer()
        b = timer()
        if b > a:
            deltas.append(b - a)
    info = time.get_clock_info("perf_counter")
    stats = summarize(latencies)
    stats.update(
        {
            "clock": info.implementation,
            "clock_resolution_ns": info.resolution * 1e9,
            "timer_call_min_ns": min(deltas) if deltas else 0,
            "timer_call_median_ns": statistics.median(deltas) if deltas else 0,
        }
    )
    return stats


def _phase(name: str, stamps: array, latencies: array, kinds: list[str], wall_ns: int) -> dict:
    return {
        "name": name,
        "count": len(latencies),
        "duration_ns": wall_ns,
        "ts": stamps.tolist(),
        "lat": latencies.tolist(),
        "kinds": kinds,
    }


def _environment() -> dict:
    try:
        affinity = sorted(os.sched_getaffinity(0))  # type: ignore[attr-defined]
    except AttributeError:
        affinity = None
    import sqlalchemy

    return {
        "python": sys.version.split()[0],
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "sqlite": sqlite3.sqlite_version,
        "sqlalchemy": sqlalchemy.__version__,
        "cpu_count": os.cpu_count(),
        "cpu_affinity": affinity,
        "hostname": platform.node(),
        "in_docker": os.path.exists("/.dockerenv"),
    }


def run(target: str, scenario: str, config: Config, repeat: int = 0, seed: int = 2026) -> dict:
    if target not in TARGETS:
        raise ValueError(f"target: {sorted(TARGETS)}")
    spec = SCENARIOS[scenario]
    timer = time.perf_counter_ns
    origin = timer()
    started_at = datetime.now(timezone.utc).isoformat()

    # --- setup ---------------------------------------------------------------------------------
    workdir = tempfile.mkdtemp(prefix="wildlife-bench-", dir=os.environ.get("BENCH_DB_DIR"))
    database = os.path.join(workdir, "bench.db")
    rows = dataset.seed_database(database)
    repo = open_target(target, database)
    repo.get_species(1)  # первое соединение и прогрев схемы — вне замеров
    total = config.warmup_max + config.measure + config.teardown
    plan = spec.build(repo, random.Random(seed + repeat), total)
    gc.collect()
    setup_ns = timer() - origin

    calibration_start = timer()
    overhead = _calibrate(config.calibration, origin)
    calibration_ns = timer() - calibration_start

    # --- warmup: до стабилизации медианы ---------------------------------------------------------
    w_stamps, w_lat = array("q"), array("q")
    position, previous_median, stable = 0, None, False
    w_start = timer()
    while position < config.warmup_max:
        stamps, lat = _timed_loop(plan.fns, plan.args, position, config.warmup_chunk, origin)
        w_stamps.extend(stamps)
        w_lat.extend(lat)
        position += config.warmup_chunk
        median = statistics.median(lat)
        if previous_median and position >= config.warmup_min:
            if abs(median - previous_median) / previous_median <= config.warmup_tolerance:
                stable = True
                break
        previous_median = median
    w_wall = timer() - w_start
    warmup = _phase("warmup", w_stamps, w_lat, plan.kinds[:position], w_wall)
    warmup["stable"] = stable

    # --- measure --------------------------------------------------------------------------------
    m_start = timer()
    m_stamps, m_lat = _timed_loop(plan.fns, plan.args, position, config.measure, origin)
    m_wall = timer() - m_start
    measure = _phase("measure", m_stamps, m_lat, plan.kinds[position : position + config.measure], m_wall)
    position += config.measure

    # --- teardown-хвост ---------------------------------------------------------------------------
    t_start = timer()
    t_stamps, t_lat = _timed_loop(plan.fns, plan.args, position, config.teardown, origin)
    t_wall = timer() - t_start
    teardown = _phase("teardown", t_stamps, t_lat, plan.kinds[position : position + config.teardown], t_wall)

    # --- cleanup --------------------------------------------------------------------------------
    c_start = timer()
    repo.close()
    shutil.rmtree(workdir, ignore_errors=True)
    cleanup_ns = timer() - c_start
    total_ns = timer() - origin

    measure_kinds = {}
    for kind in sorted(set(measure["kinds"])):
        measure_kinds[kind] = summarize(
            [v for v, k in zip(measure["lat"], measure["kinds"]) if k == kind]
        )

    return {
        "target": target,
        "target_title": TARGETS[target],
        "scenario": scenario,
        "scenario_title": spec.title,
        "repeat": repeat,
        "seed": seed + repeat,
        "started_at": started_at,
        "config": config.__dict__,
        "environment": _environment(),
        "dataset": rows,
        "durations_ns": {
            "setup": setup_ns,
            "calibration": calibration_ns,
            "warmup": w_wall,
            "measure": m_wall,
            "teardown": t_wall,
            "cleanup": cleanup_ns,
            "total": total_ns,
        },
        "overhead": overhead,
        "summary": summarize(measure["lat"]),
        "summary_by_kind": measure_kinds,
        "phases": [warmup, measure, teardown],
    }
