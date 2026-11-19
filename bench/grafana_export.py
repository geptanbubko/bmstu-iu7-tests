"""Экспорт результатов в SQL для дашборда Grafana (PostgreSQL — встроенный источник данных Grafana).

Из сырых прогонов строится один файл `01_bench.sql.gz`, который postgres выполняет при старте
(docker-entrypoint-initdb.d). Те же расчёты, что и в статическом отчёте (bench/report.py):
перцентили, кривая распределения, гистограмма, фазы, overhead — графики в Grafana и в отчёте
показывают одни и те же числа.
"""
from __future__ import annotations

import gzip
import io
from pathlib import Path

import numpy as np

from bench.report import (
    REQUIRED,
    SCENARIO_ORDER,
    SCENARIO_SHORT,
    TARGET_LABELS,
    TARGET_ORDER,
    _hdr_curve,
    load_runs,
    merged,
)

SCHEMA = """
DROP TABLE IF EXISTS scenarios, targets, runs, summary, curve, histogram, timeline,
    timeline_median, phases, kinds, overhead CASCADE;

CREATE TABLE scenarios (scenario text PRIMARY KEY, ord int, short text, title text);
CREATE TABLE targets   (target text PRIMARY KEY, ord int, label text);
-- один прогон = один контейнер
CREATE TABLE runs (scenario text, target text, repeat int, p50_us float8, p99_us float8,
    overhead_ns float8, total_s float8, cpu text, python text, sqlite text, sqlalchemy text,
    in_docker bool, started_at timestamptz);
-- перцентили по всем прогоном пары вместе (0.5, 0.75, 0.9, 0.95, 0.99, 0.999)
CREATE TABLE summary (scenario text, target text, p float8, label text, latency_us float8);
-- кривая «перцентиль → задержка»; nines = -log10(1 - p): 1 = 90 %, 2 = 99 %, 3 = 99.9 %
CREATE TABLE curve (scenario text, target text, nines float8, p float8, latency_us float8);
CREATE TABLE histogram (scenario text, target text, bin_us float8, share_pct float8);
-- задержка каждой операции прогона r00 во времени (все фазы)
CREATE TABLE timeline (scenario text, target text, phase text, t_s float8, latency_us float8);
CREATE TABLE timeline_median (scenario text, target text, t_s float8, latency_us float8);
-- среднее на прогон: операций и секунд в каждой фазе
CREATE TABLE phases (scenario text, target text, phase text, ord int, ops float8, duration_s float8);
CREATE TABLE kinds (scenario text, target text, kind text, p float8, label text, latency_us float8);
CREATE TABLE overhead (scenario text, target text, repeat int, noop_ns float8, timer_min_ns float8,
    share_pct float8);
"""

PHASE_ORDER = {"other": 0, "warmup": 1, "measure": 2, "teardown": 3}
MEDIAN_WINDOW = 101
TIMELINE_STEP = 1  # каждая операция; при огромных прогонах можно прореживать


def _copy(buf: io.StringIO, table: str, columns: tuple[str, ...], rows) -> None:
    buf.write(f"COPY {table} ({', '.join(columns)}) FROM stdin;\n")
    for row in rows:
        buf.write("\t".join(_cell(v) for v in row))
        buf.write("\n")
    buf.write("\\.\n\n")


def _cell(value) -> str:
    if value is None:
        return r"\N"
    if isinstance(value, bool):
        return "t" if value else "f"
    if isinstance(value, float):
        return repr(value) if np.isfinite(value) else r"\N"
    text = str(value)
    return text.replace("\\", "\\\\").replace("\t", " ").replace("\n", " ")


def _p_label(p: float) -> str:
    return f"p{p * 100:g}"


def export_sql(raw_dir: Path, out_file: Path) -> Path:
    runs = load_runs(raw_dir)
    scenarios = [s for s in SCENARIO_ORDER if any(k[0] == s for k in runs)]
    buf = io.StringIO()
    buf.write(SCHEMA)

    _copy(buf, "scenarios", ("scenario", "ord", "short", "title"), [
        (s, i, SCENARIO_SHORT[s], next(r for (sc, _t), rs in runs.items() if sc == s for r in rs)["scenario_title"])
        for i, s in enumerate(scenarios)
    ])
    _copy(buf, "targets", ("target", "ord", "label"), [
        (t, i, TARGET_LABELS[t]) for i, t in enumerate(TARGET_ORDER)
    ])

    run_rows, summary_rows, curve_rows, hist_rows = [], [], [], []
    tl_rows, med_rows, phase_rows, kind_rows, oh_rows = [], [], [], [], []
    probs = REQUIRED + (0.999,)
    for s in scenarios:
        present = [t for t in TARGET_ORDER if (s, t) in runs]
        data = {t: merged(runs[(s, t)]) for t in present}
        lo = min(np.quantile(v, 0.0005) for v in data.values())
        hi = max(np.quantile(v, 0.9995) for v in data.values())
        edges = np.logspace(np.log10(lo), np.log10(hi), 90)
        centers = np.sqrt(edges[:-1] * edges[1:])
        for t in present:
            rs, values = runs[(s, t)], data[t]
            for r in rs:
                env = r["environment"]
                run_rows.append((
                    s, t, r["repeat"], r["summary"]["percentiles"]["0.5"] / 1e3,
                    r["summary"]["percentiles"]["0.99"] / 1e3, r["overhead"]["percentiles"]["0.5"],
                    r["durations_ns"]["total"] / 1e9, str(env["cpu_affinity"]), env["python"],
                    env["sqlite"], env["sqlalchemy"], bool(env["in_docker"]), r["started_at"],
                ))
                oh_rows.append((
                    s, t, r["repeat"], r["overhead"]["percentiles"]["0.5"], r["overhead"]["timer_call_min_ns"],
                    r["overhead"]["percentiles"]["0.5"] / r["summary"]["percentiles"]["0.5"] * 100,
                ))
            for p, v in zip(probs, np.quantile(values, probs)):
                summary_rows.append((s, t, p, _p_label(p), float(v)))
            xs, ys = _hdr_curve(values)
            for x, y in zip(xs, ys):
                p = 1 - 1 / x
                curve_rows.append((s, t, float(np.log10(x)), float(p), float(y)))
            counts, _ = np.histogram(np.clip(values, lo, hi), bins=edges)
            for c, share in zip(centers, counts / values.size * 100):
                hist_rows.append((s, t, float(c), float(share)))

            first = rs[0]
            origin = first["phases"][0]["ts"][0] if first["phases"][0]["ts"] else 0
            all_ts, all_lat = [], []
            for phase in first["phases"]:
                for ts, lat in zip(phase["ts"][::TIMELINE_STEP], phase["lat"][::TIMELINE_STEP]):
                    tl_rows.append((s, t, phase["name"], (ts - origin) / 1e9, lat / 1e3))
                all_ts += phase["ts"]
                all_lat += phase["lat"]
            lat = np.asarray(all_lat, dtype=np.float64)
            if lat.size > MEDIAN_WINDOW:
                rolling = np.median(np.lib.stride_tricks.sliding_window_view(lat, MEDIAN_WINDOW), axis=1)
                ts_mid = np.asarray(all_ts[MEDIAN_WINDOW // 2: MEDIAN_WINDOW // 2 + rolling.size], dtype=np.float64)
                for x, y in zip(ts_mid[::10], rolling[::10]):
                    med_rows.append((s, t, float((x - origin) / 1e9), float(y / 1e3)))

            names = ("warmup", "measure", "teardown")
            durations = {n: float(np.mean([r["durations_ns"][n] for r in rs])) / 1e9 for n in names}
            total = float(np.mean([r["durations_ns"]["total"] for r in rs])) / 1e9
            for i, n in enumerate(names):
                ops = float(np.mean([r["phases"][i]["count"] for r in rs]))
                phase_rows.append((s, t, n, PHASE_ORDER[n], ops, durations[n]))
            phase_rows.append((s, t, "other", 0, None, total - sum(durations.values())))

            kinds = sorted({k for r in rs for k in r["phases"][1]["kinds"]})
            for kind in kinds:
                for p, v in zip(REQUIRED, np.quantile(merged(rs, kind), REQUIRED)):
                    kind_rows.append((s, t, kind, p, _p_label(p), float(v)))

    _copy(buf, "runs", ("scenario", "target", "repeat", "p50_us", "p99_us", "overhead_ns", "total_s", "cpu",
                        "python", "sqlite", "sqlalchemy", "in_docker", "started_at"), run_rows)
    _copy(buf, "summary", ("scenario", "target", "p", "label", "latency_us"), summary_rows)
    _copy(buf, "curve", ("scenario", "target", "nines", "p", "latency_us"), curve_rows)
    _copy(buf, "histogram", ("scenario", "target", "bin_us", "share_pct"), hist_rows)
    _copy(buf, "timeline", ("scenario", "target", "phase", "t_s", "latency_us"), tl_rows)
    _copy(buf, "timeline_median", ("scenario", "target", "t_s", "latency_us"), med_rows)
    _copy(buf, "phases", ("scenario", "target", "phase", "ord", "ops", "duration_s"), phase_rows)
    _copy(buf, "kinds", ("scenario", "target", "kind", "p", "label", "latency_us"), kind_rows)
    _copy(buf, "overhead", ("scenario", "target", "repeat", "noop_ns", "timer_min_ns", "share_pct"), oh_rows)
    buf.write("CREATE INDEX ON timeline (scenario, target, phase);\nANALYZE;\n")

    out_file.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out_file, "wt", encoding="utf-8") as fh:
        fh.write(buf.getvalue())
    return out_file
