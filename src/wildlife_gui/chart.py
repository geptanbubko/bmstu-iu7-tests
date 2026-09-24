"""Координаты SVG-графика численности: ось X — календарное время, Y — от нуля."""
from __future__ import annotations

from datetime import date

from wildlife_gui.viewmodels import AnalyticsPoint, PopulationChart

CHART_W = 100.0
CHART_H = 40.0
PAD_X = 2.0
PAD_Y = 4.0
MIN_POINTS = 5


def build_population_chart(rows: list[AnalyticsPoint]) -> PopulationChart:
    if len(rows) < MIN_POINTS:
        return PopulationChart()
    sizes = [row.size for row in rows]
    y_max = max(sizes)
    scale = max(y_max, 1)
    plot_w = CHART_W - 2 * PAD_X
    plot_h = CHART_H - 2 * PAD_Y
    xs = _time_xs([date.fromisoformat(row.date) for row in rows], plot_w)
    points = [
        (x, PAD_Y + plot_h * (1 - row.size / scale))
        for x, row in zip(xs, rows)
    ]
    line = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    first_x, last_x = points[0][0], points[-1][0]
    area = f"{first_x:.2f},{CHART_H - PAD_Y:.2f} {line} {last_x:.2f},{CHART_H - PAD_Y:.2f}"
    return PopulationChart(
        line_points=line,
        area_points=area,
        y_max=y_max,
        x_labels=[rows[0].date, rows[-1].date],
    )


def _time_xs(dates: list[date], plot_w: float) -> list[float]:
    start, end = dates[0], dates[-1]
    span_days = (end - start).days
    if span_days <= 0:
        return [PAD_X + plot_w / 2] * len(dates)
    return [PAD_X + plot_w * (item - start).days / span_days for item in dates]
