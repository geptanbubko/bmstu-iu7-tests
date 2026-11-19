"""Графический отчёт по сырым результатам прогонов (только графики, без таблиц).

Для каждого сценария:
    * timeline    — задержка каждой операции во времени (все фазы, прогрев/хвост подсвечены);
    * percentiles — распределение по перцентилям в логарифмическом масштабе, одна линия на реализацию;
    * histogram   — гистограмма распределения (логарифмические корзины);
    * pbars       — требуемые перцентили 0.5 / 0.75 / 0.9 / 0.95 / 0.99 столбцами;
    * phases      — время выполнения теста и количество операций по фазам warmup / measure / teardown;
    * kinds       — (mixed) перцентили отдельно для чтений и записей.
Сводные: p50/p99 по сценариям, во сколько раз ORM медленнее, overhead инструмента,
стабильность между прогонами в отдельных контейнерах.
"""
from __future__ import annotations

import gzip
import html
import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.ticker import FixedLocator, FuncFormatter, NullFormatter, NullLocator  # noqa: E402

# --- палитра (проверена валидатором: CVD/контраст) ------------------------------------------------
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

TARGET_COLORS = {"sql": "#2a78d6", "orm": "#eb6834"}
TARGET_LABELS = {"sql": "SQL · sqlite3", "orm": "ORM · SQLAlchemy"}
PHASE_COLORS = {"warmup": "#eda100", "measure": "#1baf7a", "teardown": "#6250d6"}
PHASE_LABELS = {"warmup": "warmup (прогрев)", "measure": "measure (замер)", "teardown": "teardown (хвост)"}
OTHER_COLOR = AXIS
RATIO_COLORS = {"p50": "#1baf7a", "p99": "#6250d6"}

REQUIRED = (0.5, 0.75, 0.9, 0.95, 0.99)
TARGET_ORDER = ("sql", "orm")
SCENARIO_ORDER = ("read_by_id", "read_range", "write_insert", "mixed")
SCENARIO_SHORT = {
    "read_by_id": "чтение по PK",
    "read_range": "чтение диапазона",
    "write_insert": "запись",
    "mixed": "чтение + запись",
}

plt.rcParams.update(
    {
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "text.color": INK,
        "axes.labelcolor": INK_2,
        "axes.titlecolor": INK,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.titlepad": 12,
        "axes.edgecolor": AXIS,
        "axes.linewidth": 1,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 1,
        "grid.linestyle": "-",
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelcolor": INK_2,
        "ytick.labelcolor": INK_2,
        "legend.frameon": False,
        "legend.fontsize": 9,
        "lines.linewidth": 2,
        "lines.solid_capstyle": "round",
        "lines.solid_joinstyle": "round",
    }
)


# --- загрузка ------------------------------------------------------------------------------------
def load_runs(raw_dir: Path) -> dict[tuple[str, str], list[dict]]:
    runs: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for path in sorted(raw_dir.glob("*.json.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            run = json.load(fh)
        runs[(run["scenario"], run["target"])].append(run)
    for key in runs:
        runs[key].sort(key=lambda r: r["repeat"])
    if not runs:
        raise SystemExit(f"Нет результатов в {raw_dir}")
    return runs


def _measure(run: dict, kind: str | None = None) -> np.ndarray:
    phase = run["phases"][1]
    lat = np.asarray(phase["lat"], dtype=np.float64)
    if kind is not None:
        lat = lat[np.asarray(phase["kinds"]) == kind]
    return lat / 1e3  # мкс


def merged(runs: list[dict], kind: str | None = None) -> np.ndarray:
    return np.concatenate([_measure(r, kind) for r in runs])


# --- форматирование ---------------------------------------------------------------------------
def fmt_us(value: float) -> str:
    if value >= 1000:
        return f"{value / 1000:.1f} мс" if value < 10_000 else f"{value / 1000:.0f} мс"
    if value >= 100:
        return f"{value:.0f} мкс"
    if value >= 10:
        return f"{value:.1f} мкс"
    return f"{value:.2f} мкс"


def _log_y_us(ax) -> None:
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: fmt_us(v)))
    ax.yaxis.set_minor_formatter(NullFormatter())


def _legend_targets(ax, targets, kind: str = "line", **kwargs) -> None:
    """Ключ легенды повторяет марку графика: line — линия, dot — точка."""
    style = {"line": {"lw": 2}, "dot": {"lw": 0, "marker": "o", "ms": 8, "mec": SURFACE, "mew": 2}}[kind]
    handles = [plt.Line2D([], [], color=TARGET_COLORS[t], **style) for t in targets]
    ax.legend(handles, [TARGET_LABELS[t] for t in targets], **kwargs)


def _save(fig, out: Path, name: str) -> str:
    path = out / f"{name}.png"
    fig.savefig(path, dpi=144, bbox_inches="tight")
    plt.close(fig)
    return path.name


def _targets_of(runs, scenario) -> list[str]:
    return [t for t in TARGET_ORDER if (scenario, t) in runs]


# --- графики сценария ----------------------------------------------------------------------------
def chart_timeline(runs, scenario, out) -> str:
    targets = _targets_of(runs, scenario)
    fig, axes = plt.subplots(len(targets), 1, figsize=(11, 2.9 * len(targets)), sharey=True)
    axes = np.atleast_1d(axes)
    for ax, target in zip(axes, targets):
        run = runs[(scenario, target)][0]
        origin = run["phases"][0]["ts"][0] if run["phases"][0]["ts"] else 0
        color = TARGET_COLORS[target]
        for phase in run["phases"]:
            ts = (np.asarray(phase["ts"], dtype=np.float64) - origin) / 1e9
            lat = np.asarray(phase["lat"], dtype=np.float64) / 1e3
            if ts.size == 0:
                continue
            if phase["name"] != "measure":
                ax.axvspan(ts[0], ts[-1], color=PHASE_COLORS[phase["name"]], alpha=0.12, lw=0)
            ax.text(
                (ts[0] + ts[-1]) / 2, 1.0, f"{phase['name']} · {phase['count']} оп.",
                transform=ax.get_xaxis_transform(), ha="center", va="bottom", fontsize=8, color=INK_2,
            )
            ax.scatter(ts, lat, s=1.5, color=color, alpha=0.18, lw=0, rasterized=True)
        all_ts = np.concatenate([np.asarray(p["ts"], dtype=np.float64) for p in run["phases"]])
        all_lat = np.concatenate([np.asarray(p["lat"], dtype=np.float64) for p in run["phases"]])
        window = 101
        if all_lat.size > window:
            rolling = np.median(np.lib.stride_tricks.sliding_window_view(all_lat, window), axis=1)
            x = (all_ts[window // 2 : window // 2 + rolling.size] - origin) / 1e9
            ax.plot(x, rolling / 1e3, color=color, lw=2)
        _log_y_us(ax)
        ax.set_xlim(left=0)
        ax.set_ylabel("задержка")
        ax.text(
            0.995, 0.96, f"{TARGET_LABELS[target]} · скользящая медиана по {window} оп.",
            transform=ax.transAxes, ha="right", va="top", fontsize=9, color=INK_2,
        )
    axes[-1].set_xlabel("время от начала прогрева, с (прогон r00)")
    axes[0].set_title(f"Задержка во времени — {run['scenario_title']}", pad=18)
    fig.tight_layout()
    return _save(fig, out, f"{scenario}_timeline")


def _hdr_curve(values: np.ndarray):
    n = values.size
    max_x = max(10.0, min(1e5, n / 2))
    xs = np.logspace(0, np.log10(max_x), 400)  # x = 1 / (1 - p)
    ps = 1 - 1 / xs
    return xs, np.quantile(values, ps)


def chart_percentiles(runs, scenario, out) -> str:
    targets = _targets_of(runs, scenario)
    fig, ax = plt.subplots(figsize=(11, 4.6))
    curves: dict[str, np.ndarray] = {}
    for target in targets:
        values = merged(runs[(scenario, target)])
        xs, ys = _hdr_curve(values)
        color = TARGET_COLORS[target]
        ax.plot(xs, ys, color=color, lw=2, zorder=3)
        px = np.array([1 / (1 - p) for p in REQUIRED])
        py = np.quantile(values, REQUIRED)
        ax.scatter(px, py, s=46, color=color, edgecolor=SURFACE, linewidth=2, zorder=4)
        curves[target] = py
    # подписи p50 и p99: у верхней линии — над точкой, у нижней — под ней
    for i, p in enumerate(REQUIRED):
        if p not in (0.5, 0.99) or not curves:
            continue
        top = max(curves, key=lambda t: curves[t][i])
        for target, py in curves.items():
            above = target == top
            ax.annotate(
                fmt_us(py[i]), (1 / (1 - p), py[i]), xytext=(0, 9 if above else -10),
                textcoords="offset points", ha="center", va="bottom" if above else "top",
                fontsize=8.5, color=INK,
            )
    ax.set_xscale("log")
    ticks = [1, 2, 4, 10, 20, 100, 1_000, 10_000, 100_000]
    labels = ["0%", "50%", "75%", "90%", "95%", "99%", "99.9%", "99.99%", "99.999%"]
    xmax = ax.get_xlim()[1]
    keep = [(t, lbl) for t, lbl in zip(ticks, labels) if t <= xmax]
    ax.xaxis.set_major_locator(FixedLocator([t for t, _ in keep]))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _p: dict(keep).get(v, "")))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.set_xlim(1, xmax)
    _log_y_us(ax)
    ax.set_xlabel("перцентиль (логарифмическая шкала: 1 / (1 − p))")
    ax.set_ylabel("задержка")
    ax.set_title(f"Распределение по перцентилям — {SCENARIO_SHORT[scenario]}")
    _legend_targets(ax, targets, loc="upper left")
    ax.text(
        0.995, 0.02, "точки — требуемые 0.5 / 0.75 / 0.9 / 0.95 / 0.99; все прогоны вместе",
        transform=ax.transAxes, ha="right", va="bottom", fontsize=8, color=MUTED,
    )
    fig.tight_layout()
    return _save(fig, out, f"{scenario}_percentiles")


def chart_histogram(runs, scenario, out) -> str:
    targets = _targets_of(runs, scenario)
    data = {t: merged(runs[(scenario, t)]) for t in targets}
    lo = min(np.quantile(v, 0.0005) for v in data.values())
    hi = max(np.quantile(v, 0.9995) for v in data.values())
    bins = np.logspace(np.log10(lo), np.log10(hi), 90)
    fig, ax = plt.subplots(figsize=(11, 4.2))
    for target, values in data.items():
        counts, edges = np.histogram(np.clip(values, lo, hi), bins=bins)
        share = counts / values.size * 100
        color = TARGET_COLORS[target]
        ax.stairs(share, edges, fill=True, color=color, alpha=0.12, lw=0)
        ax.stairs(share, edges, color=color, lw=2, label=TARGET_LABELS[target])
        median = np.median(values)
        ax.axvline(median, color=color, lw=1, alpha=0.8)
        ax.annotate(
            f"p50 {fmt_us(median)}", (median, 1), xycoords=("data", "axes fraction"),
            xytext=(4, -12), textcoords="offset points", fontsize=8.5, color=INK_2,
        )
    ax.set_xscale("log")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _p: fmt_us(v)))
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"{v:.0f}%"))
    ax.set_ylim(bottom=0)
    ax.set_xlabel("задержка (логарифмические корзины)")
    ax.set_ylabel("доля операций")
    ax.set_title(f"Гистограмма распределения — {SCENARIO_SHORT[scenario]}")
    _legend_targets(ax, targets, loc="upper right")
    fig.tight_layout()
    return _save(fig, out, f"{scenario}_histogram")


def fmt_bar(value: float) -> str:
    """Компактная подпись над столбцом: без лишних знаков, чтобы не налезать на соседа."""
    if value >= 1000:
        return f"{value / 1000:.1f} мс"
    if value >= 10:
        return f"{value:.0f} мкс"
    return f"{value:.1f} мкс"


def _grouped_bars(ax, groups, series, values, colors, labels, value_fmt=fmt_bar, log=True) -> None:
    n = len(series)
    width = min(0.32, 0.76 / n)
    x = np.arange(len(groups))
    for i, key in enumerate(series):
        offs = (i - (n - 1) / 2) * (width + 0.05)
        vals = values[key]
        bars = ax.bar(x + offs, vals, width=width, color=colors[key], label=labels[key], zorder=3)
        for bar, v in zip(bars, vals):
            ax.annotate(
                value_fmt(v), (bar.get_x() + bar.get_width() / 2, v), xytext=(0, 3),
                textcoords="offset points", ha="center", va="bottom", fontsize=7.5, color=INK,
            )
    ax.set_xticks(x, groups)
    ax.tick_params(axis="x", length=0)
    ax.grid(axis="x", visible=False)
    if log:
        _log_y_us(ax)
        top = max(max(v) for v in values.values())
        bottom = min(min(v) for v in values.values())
        ax.set_ylim(bottom / 2.5, top * 3)


def chart_pbars(runs, scenario, out) -> str:
    targets = _targets_of(runs, scenario)
    values = {t: list(np.quantile(merged(runs[(scenario, t)]), REQUIRED)) for t in targets}
    fig, ax = plt.subplots(figsize=(11, 4.2))
    _grouped_bars(
        ax, [f"p{int(p * 100)}" for p in REQUIRED], targets, values,
        TARGET_COLORS, TARGET_LABELS,
    )
    ax.set_ylabel("задержка (лог. шкала)")
    ax.set_title(f"Требуемые перцентили — {SCENARIO_SHORT[scenario]}")
    ax.legend(loc="upper left", ncols=2)
    fig.tight_layout()
    return _save(fig, out, f"{scenario}_pbars")


def _stacked_h(ax, rows, parts, colors, labels, value_fmt, totals=None) -> None:
    y = np.arange(len(rows))
    left = np.zeros(len(rows))
    narrow = np.zeros(len(rows), dtype=int)  # счётчик узких сегментов в строке: подписи чередуются
    for part in parts:
        widths = np.array([row[part] for row in rows.values()], dtype=float)
        bars = ax.barh(
            y, widths, left=left, height=0.5, color=colors[part], label=labels[part],
            edgecolor=SURFACE, linewidth=2, zorder=3,
        )
        for row, (bar, w) in enumerate(zip(bars, widths)):
            if w <= 0:
                continue
            cx = bar.get_x() + bar.get_width() / 2
            if bar.get_width() / max(ax.get_xlim()[1], 1e-9) > 0.09:  # помещается внутри сегмента
                ax.text(
                    cx, bar.get_y() + bar.get_height() / 2,
                    value_fmt(w), ha="center", va="center", fontsize=8.5,
                    color=INK if colors[part] in ("#eda100", "#1baf7a", AXIS) else "#ffffff",
                )
            else:  # узкий сегмент — подпись над / под ним по очереди, значение не теряется
                # после invert_yaxis get_y() — верхний край столбца, get_y()+height — нижний
                above = narrow[row] % 2 == 0
                narrow[row] += 1
                ax.annotate(
                    value_fmt(w), (cx, bar.get_y() if above else bar.get_y() + bar.get_height()),
                    xytext=(0, 2 if above else -2), textcoords="offset points",
                    ha="center", va="bottom" if above else "top", fontsize=8, color=INK_2,
                )
        left += widths
    if totals:
        for yi, (lft, label) in enumerate(zip(left, totals)):
            ax.text(lft, yi, f"  {label}", va="center", ha="left", fontsize=9, color=INK)
    ax.set_yticks(y, list(rows))
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="y", visible=False)
    ax.set_ylim(len(rows) - 0.3, -0.7)  # перевёрнутая ось с запасом под подписи узких сегментов


def chart_phases(runs, scenario, out) -> str:
    targets = _targets_of(runs, scenario)
    phases = ("warmup", "measure", "teardown")
    counts, durations, totals_s, totals_ops = {}, {}, [], []
    for t in targets:
        rs = runs[(scenario, t)]
        label = f"{TARGET_LABELS[t]}\n({len(rs)} прогон.)"
        counts[label] = {p: float(np.mean([r["phases"][i]["count"] for r in rs])) for i, p in enumerate(phases)}
        d = {p: float(np.mean([r["durations_ns"][p] for r in rs])) / 1e9 for p in phases}
        d["other"] = float(
            np.mean([r["durations_ns"]["total"] for r in rs])
        ) / 1e9 - sum(d.values())
        durations[label] = d
        totals_s.append(f"всего {np.mean([r['durations_ns']['total'] for r in rs]) / 1e9:.2f} с")
        totals_ops.append(f"всего {sum(counts[label].values()):,.0f} оп.".replace(",", " "))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 5.2))
    # сначала оси, потом подписи: ширина нужна для решения «влезает ли подпись»
    ax1.set_xlim(0, max(sum(v.values()) for v in counts.values()) * 1.22)
    _stacked_h(
        ax1, counts, phases, PHASE_COLORS, PHASE_LABELS,
        lambda v: f"{v:,.0f}".replace(",", " "), totals_ops,
    )
    ax1.xaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"{v:,.0f}".replace(",", " ")))
    ax1.set_title(f"Операции по фазам (среднее на прогон) — {SCENARIO_SHORT[scenario]}")

    colors = dict(PHASE_COLORS, other=OTHER_COLOR)
    labels = dict(PHASE_LABELS, other="setup + калибровка + cleanup")
    ax2.set_xlim(0, max(sum(v.values()) for v in durations.values()) * 1.22)
    _stacked_h(
        ax2, durations, ("other",) + phases, colors, labels,
        lambda v: f"{v:.2f} с", totals_s,
    )
    ax2.xaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"{v:g} с"))
    ax2.set_title("Время выполнения теста по фазам (среднее на прогон)")
    handles = [plt.Rectangle((0, 0), 1, 1, color=colors[k]) for k in ("warmup", "measure", "teardown", "other")]
    fig.legend(handles, [labels[k] for k in ("warmup", "measure", "teardown", "other")],
               loc="lower center", ncols=4, bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    return _save(fig, out, f"{scenario}_phases")


def chart_kinds(runs, scenario, out) -> str | None:
    targets = _targets_of(runs, scenario)
    kinds = sorted({k for t in targets for r in runs[(scenario, t)] for k in r["phases"][1]["kinds"]})
    if len(kinds) < 2:
        return None
    fig, axes = plt.subplots(len(kinds), 1, figsize=(11, 3.6 * len(kinds)), sharey=True)
    titles = {"read": "чтения диапазона", "write": "upsert-записи"}
    for ax, kind in zip(axes, kinds):
        values = {t: list(np.quantile(merged(runs[(scenario, t)], kind), REQUIRED)) for t in targets}
        _grouped_bars(
            ax, [f"p{int(p * 100)}" for p in REQUIRED], targets, values,
            TARGET_COLORS, TARGET_LABELS,
        )
        ax.set_title(titles.get(kind, kind), fontsize=11)
    all_vals = [
        v for kind in kinds for t in targets
        for v in np.quantile(merged(runs[(scenario, t)], kind), REQUIRED)
    ]
    axes[0].set_ylim(min(all_vals) / 2.5, max(all_vals) * 3)
    axes[0].set_ylabel("задержка (лог. шкала)")
    axes[0].legend(loc="upper left")
    fig.suptitle("Смешанный сценарий: перцентили по видам операций", x=0.01, ha="left",
                 fontsize=12, fontweight="bold")
    fig.tight_layout()
    return _save(fig, out, f"{scenario}_kinds")


# --- сводные графики ------------------------------------------------------------------------------
def _scenarios_of(runs) -> list[str]:
    present = {s for s, _ in runs}
    return [s for s in SCENARIO_ORDER if s in present]


def chart_overview(runs, out) -> str:
    scenarios = _scenarios_of(runs)
    fig, axes = plt.subplots(2, 1, figsize=(11, 8))
    for ax, (p, title) in zip(axes, ((0.5, "Медиана p50 по сценариям"), (0.99, "Хвост p99 по сценариям"))):
        values = {
            t: [float(np.quantile(merged(runs[(s, t)]), p)) if (s, t) in runs else np.nan for s in scenarios]
            for t in TARGET_ORDER
        }
        _grouped_bars(ax, [SCENARIO_SHORT[s] for s in scenarios], TARGET_ORDER, values,
                      TARGET_COLORS, TARGET_LABELS)
        ax.set_title(title)
    for ax in axes:
        ax.set_ylabel("задержка операции (лог. шкала)")
    axes[0].legend(loc="upper left", ncols=2)
    fig.tight_layout()
    return _save(fig, out, "overview_latency")


def chart_ratio(runs, out) -> str:
    scenarios = [s for s in _scenarios_of(runs) if all((s, t) in runs for t in TARGET_ORDER)]
    values = {"p50": [], "p99": []}
    for s in scenarios:
        sql, orm = merged(runs[(s, "sql")]), merged(runs[(s, "orm")])
        values["p50"].append(float(np.median(orm) / np.median(sql)))
        values["p99"].append(float(np.quantile(orm, 0.99) / np.quantile(sql, 0.99)))
    fig, ax = plt.subplots(figsize=(11, 4.0))
    _grouped_bars(
        ax, [SCENARIO_SHORT[s] for s in scenarios], ("p50", "p99"), values, RATIO_COLORS,
        {"p50": "по медиане p50", "p99": "по хвосту p99"}, value_fmt=lambda v: f"×{v:.1f}", log=False,
    )
    ax.axhline(1, color=INK_2, lw=1, zorder=4)
    ax.annotate("×1 — одинаково", (1, 1), xycoords=("axes fraction", "data"), xytext=(-4, 4),
                textcoords="offset points", ha="right", fontsize=8, color=INK_2)
    ax.set_ylim(0, max(max(v) for v in values.values()) * 1.2)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"×{v:g}"))
    ax.set_ylabel("ORM / SQL")
    ax.set_title("Во сколько раз ORM медленнее чистого SQL")
    ax.legend(loc="upper right", ncols=2)
    fig.tight_layout()
    return _save(fig, out, "overview_ratio")


def chart_overhead(runs, out) -> str:
    all_runs = [r for rs in runs.values() for r in rs]
    noop = np.array([r["overhead"]["percentiles"]["0.5"] for r in all_runs])
    timer_min = np.array([r["overhead"]["timer_call_min_ns"] for r in all_runs])
    scenarios = _scenarios_of(runs)
    values = {}
    for t in TARGET_ORDER:
        shares = []
        for s in scenarios:
            rs = runs.get((s, t), [])
            if not rs:
                shares.append(np.nan)
                continue
            share = [r["overhead"]["percentiles"]["0.5"] / r["summary"]["percentiles"]["0.5"] * 100 for r in rs]
            shares.append(float(np.median(share)))
        values[t] = shares
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.2), gridspec_kw={"width_ratios": [1, 2]})

    ax1.bar([0], [np.median(noop)], width=0.4, color=PHASE_COLORS["teardown"], zorder=3)
    ax1.bar([1], [np.median(timer_min)], width=0.4, color=PHASE_COLORS["teardown"], zorder=3)
    for x, v in ((0, np.median(noop)), (1, np.median(timer_min))):
        ax1.annotate(f"{v:.0f} нс", (x, v), xytext=(0, 3), textcoords="offset points",
                     ha="center", fontsize=9, color=INK)
    ax1.axhline(5, color=INK_2, lw=1, zorder=4)
    ax1.annotate("цель 4–5 нс", (0.5, 5), xycoords=("data", "data"), xytext=(0, 3),
                 textcoords="offset points", ha="center", fontsize=8, color=INK_2)
    ax1.set_xticks([0, 1], ["пустая операция\nв цикле замера, p50", "пара вызовов\nтаймера, min"])
    ax1.tick_params(axis="x", length=0)
    ax1.grid(axis="x", visible=False)
    ax1.set_ylim(0, max(np.median(noop), 5) * 1.3)
    ax1.set_ylabel("нс")
    ax1.set_title("Overhead инструмента")

    _grouped_bars(ax2, [SCENARIO_SHORT[s] for s in scenarios], TARGET_ORDER, values, TARGET_COLORS,
                  TARGET_LABELS, value_fmt=lambda v: f"{v:.2f}%", log=False)
    ax2.set_ylim(0, max(max(v) for v in values.values()) * 1.3)
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"{v:g}%"))
    ax2.set_title("Доля overhead в медиане операции")
    ax2.legend(loc="upper right", ncols=2)
    fig.tight_layout()
    return _save(fig, out, "overview_overhead")


def chart_stability(runs, out) -> str:
    scenarios = _scenarios_of(runs)
    fig, ax = plt.subplots(figsize=(11, 4.0))
    offsets = {"sql": -0.15, "orm": 0.15}
    for t in TARGET_ORDER:
        for i, s in enumerate(scenarios):
            rs = runs.get((s, t), [])
            if not rs:
                continue
            p50 = np.array([r["summary"]["percentiles"]["0.5"] for r in rs])
            dev = (p50 / np.median(p50) - 1) * 100
            ax.scatter(np.full(dev.size, i + offsets[t]), dev, s=60, color=TARGET_COLORS[t],
                       edgecolor=SURFACE, linewidth=2, zorder=3)
    ax.axhline(0, color=INK_2, lw=1, zorder=2)
    ax.set_xticks(range(len(scenarios)), [SCENARIO_SHORT[s] for s in scenarios])
    ax.tick_params(axis="x", length=0)
    ax.grid(axis="x", visible=False)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"{v:+.0f}%"))
    ax.set_ylabel("отклонение p50 прогона\nот медианы прогонов")
    n = max(len(rs) for rs in runs.values())
    isolated = "контейнере" if all(r["environment"]["in_docker"] for rs in runs.values() for r in rs) else "процессе"
    ax.set_title(f"Стабильность: p50 каждого прогона в отдельном {isolated} (до {n} на пару)")
    _legend_targets(ax, TARGET_ORDER, kind="dot", loc="upper right", ncols=2)
    fig.tight_layout()
    return _save(fig, out, "overview_stability")


# --- HTML ------------------------------------------------------------------------------------------
_CSS = """
:root { --surface:#fcfcfb; --page:#f9f9f7; --ink:#0b0b0b; --ink2:#52514e; --muted:#898781;
        --line:rgba(11,11,11,.10); }
* { box-sizing: border-box; }
body { margin:0; background:var(--page); color:var(--ink);
       font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; }
main { max-width:1180px; margin:0 auto; padding:32px 16px 64px; }
h1 { font-size:28px; margin:0 0 4px; } h2 { font-size:20px; margin:40px 0 8px; }
p.lead { color:var(--ink2); margin:0 0 24px; max-width:820px; }
.tiles { display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:12px; }
.tile { background:var(--surface); border:1px solid var(--line); border-radius:10px; padding:14px 16px; }
.tile .label { color:var(--ink2); font-size:13px; } .tile .value { font-size:24px; font-weight:600; }
figure { margin:16px 0; background:var(--surface); border:1px solid var(--line); border-radius:10px;
         padding:12px; } figure img { width:100%; height:auto; display:block; }
nav a { color:var(--ink2); margin-right:16px; } .env { color:var(--muted); font-size:13px; }
"""


def build_report(raw_dir: Path, out: Path) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    runs = load_runs(raw_dir)
    scenarios = _scenarios_of(runs)
    all_runs = [r for rs in runs.values() for r in rs]
    env = all_runs[0]["environment"]

    summary_imgs = [chart_overview(runs, out), chart_ratio(runs, out), chart_overhead(runs, out),
                    chart_stability(runs, out)]
    per_scenario = {}
    for s in scenarios:
        imgs = [chart_pbars(runs, s, out), chart_percentiles(runs, s, out), chart_histogram(runs, s, out)]
        kinds = chart_kinds(runs, s, out)
        if kinds:
            imgs.append(kinds)
        imgs += [chart_timeline(runs, s, out), chart_phases(runs, s, out)]
        per_scenario[s] = imgs

    samples = sum(r["phases"][1]["count"] for r in all_runs)
    noop = float(np.median([r["overhead"]["percentiles"]["0.5"] for r in all_runs]))
    tiles = [
        ("Прогонов (контейнеров)", f"{len(all_runs)}"),
        ("Измерений в статистике", f"{samples:,}".replace(",", " ")),
        ("Замеров на прогон", f"{all_runs[0]['config']['measure']:,}".replace(",", " ")),
        ("Overhead замера, p50", f"{noop:.0f} нс"),
        ("CPU на прогон", f"{len(env['cpu_affinity']) if env['cpu_affinity'] else '—'}"),
    ]
    parts = [
        "<!doctype html><html lang='ru'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        f"<title>ЛР3 — SQL vs ORM</title><style>{_CSS}</style></head><body><main>",
        "<h1>Микробенчмарк: SQL (sqlite3) против ORM (SQLAlchemy)</h1>",
        "<p class='lead'>Слой данных Wildlife Monitoring: одни и те же операции, одна и та же БД, "
        "одинаковый план операций. Каждый прогон — отдельный контейнер из одного образа, 1 ядро CPU.</p>",
        "<div class='tiles'>",
        *[f"<div class='tile'><div class='label'>{html.escape(a)}</div><div class='value'>{html.escape(b)}</div></div>"
          for a, b in tiles],
        "</div>",
        f"<p class='env'>Python {env['python']} · SQLite {env['sqlite']} · SQLAlchemy {env['sqlalchemy']} · "
        f"{html.escape(env['platform'])}</p>",
        "<nav>" + "".join(f"<a href='#{s}'>{SCENARIO_SHORT[s]}</a>" for s in scenarios) + "</nav>",
        "<h2>Сводка</h2>",
        *[f"<figure><img src='{i}' alt='{i}'></figure>" for i in summary_imgs],
    ]
    for s in scenarios:
        title = runs[(s, _targets_of(runs, s)[0])][0]["scenario_title"]
        parts.append(f"<h2 id='{s}'>{html.escape(title)}</h2>")
        parts += [f"<figure><img src='{i}' alt='{i}'></figure>" for i in per_scenario[s]]
    parts.append("</main></body></html>")
    index = out / "index.html"
    index.write_text("\n".join(parts), encoding="utf-8")
    return index
