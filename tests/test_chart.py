from wildlife_gui.chart import build_population_chart
from wildlife_gui.viewmodels import AnalyticsPoint


def _point(day: str, size: int) -> AnalyticsPoint:
    return AnalyticsPoint(day, size)


def test_chart_skipped_if_fewer_than_five_points() -> None:
    rows = [
        _point("2026-01-01", 2),
        _point("2026-02-01", 4),
        _point("2026-03-01", 5),
        _point("2026-04-01", 8),
    ]
    chart = build_population_chart(rows)
    assert chart.line_points == ""


def test_chart_built_from_five_points() -> None:
    rows = [
        _point("2026-01-01", 2),
        _point("2026-02-01", 4),
        _point("2026-03-01", 5),
        _point("2026-04-01", 8),
        _point("2026-05-01", 10),
    ]
    chart = build_population_chart(rows)
    assert chart.y_max == 10
    assert chart.line_points
    assert chart.x_labels == ["2026-01-01", "2026-05-01"]


def test_chart_x_follows_calendar_gaps() -> None:
    rows = [
        _point("2026-01-01", 1),
        _point("2026-01-02", 2),
        _point("2026-01-03", 3),
        _point("2026-01-04", 4),
        _point("2026-01-31", 5),
    ]
    xs = [
        float(pair.split(",")[0])
        for pair in build_population_chart(rows).line_points.split()
    ]
    day_gap = xs[1] - xs[0]
    late_gap = xs[4] - xs[3]
    assert late_gap > 20 * day_gap
