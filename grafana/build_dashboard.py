"""Генерирует grafana/dashboards/bench.json — дашборд ЛР3 (только графики, без таблиц).

    py grafana/build_dashboard.py

Цвета — та же проверенная палитра, что в статическом отчёте: SQL синий, ORM оранжевый,
фазы warmup / measure / teardown — жёлтый / бирюзовый / фиолетовый.
"""
from __future__ import annotations

import json
from pathlib import Path

DS = {"type": "grafana-postgresql-datasource", "uid": "bench-pg"}
# Без pluginVersion Grafana считает панель созданной до 11.1 и «мигрирует» опции XY-графика
# по старой схеме, ломая ручное сопоставление серий.
GRAFANA_VERSION = "11.4.0"

SQL_LABEL, ORM_LABEL = "SQL · sqlite3", "ORM · SQLAlchemy"
COLORS = {
    SQL_LABEL: "#2a78d6",
    ORM_LABEL: "#eb6834",
    "warmup (прогрев)": "#eda100",
    "measure (замер)": "#1baf7a",
    "teardown (хвост)": "#6250d6",
    "setup + калибровка + cleanup": "#c3c2b7",
    "по медиане p50": "#1baf7a",
    "по хвосту p99": "#6250d6",
    "warmup": "#eda100",
    "teardown": "#6250d6",
    "скользящая медиана": "#52514e",
}
SC = "'$scenario'"

_panels: list[dict] = []
_next_id = [1]


def target(sql: str, ref: str = "A") -> dict:
    return {"datasource": DS, "refId": ref, "rawSql": " ".join(sql.split()), "format": "table",
            "editorMode": "code", "rawQuery": True}


def color_overrides(names) -> list[dict]:
    return [
        {"matcher": {"id": "byName", "options": n},
         "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": COLORS[n]}}]}
        for n in names if n in COLORS
    ]


def panel(kind: str, title: str, grid: tuple[int, int, int, int], targets: list[dict], *,
          description: str = "", options: dict | None = None, defaults: dict | None = None,
          overrides: list | None = None) -> dict:
    x, y, w, h = grid
    p = {
        "id": _next_id[0], "type": kind, "title": title, "description": description, "datasource": DS,
        "pluginVersion": GRAFANA_VERSION,
        "gridPos": {"x": x, "y": y, "w": w, "h": h}, "targets": targets,
        "options": options or {},
        "fieldConfig": {"defaults": defaults or {}, "overrides": overrides or []},
    }
    _next_id[0] += 1
    _panels.append(p)
    return p


def row(title: str, y: int) -> None:
    _panels.append({"id": _next_id[0], "type": "row", "title": title, "collapsed": False,
                    "gridPos": {"x": 0, "y": y, "w": 24, "h": 1}, "panels": []})
    _next_id[0] += 1


def bars(title, grid, sql, series, *, unit="µs", log=True, decimals=None, horizontal=False,
         stacked=False, description="", value_size=11, min_value=None, rotate=0) -> dict:
    custom = {"fillOpacity": 100, "lineWidth": 0, "gradientMode": "none", "axisPlacement": "auto",
              "axisGridShow": True, "axisBorderShow": False,
              "scaleDistribution": {"type": "log", "log": 10} if log else {"type": "linear"}}
    defaults = {"unit": unit, "custom": custom, "color": {"mode": "fixed", "fixedColor": "#2a78d6"}}
    if decimals is not None:
        defaults["decimals"] = decimals
    if min_value is not None:
        defaults["min"] = min_value
    return panel(
        "barchart", title, grid, [target(sql)], description=description,
        options={
            "orientation": "horizontal" if horizontal else "vertical",
            # у составных столбцов Grafana сама прячет подписи, которые не влезают в сегмент
            "showValue": "auto" if stacked else "always", "stacking": "normal" if stacked else "none",
            "groupWidth": 0.62 if not horizontal else 0.5, "barWidth": 0.9, "barRadius": 0.06,
            "fullHighlight": False, "xTickLabelRotation": rotate, "xTickLabelSpacing": 0,
            "text": {"valueSize": value_size},
            "legend": {"showLegend": True, "displayMode": "list", "placement": "bottom"},
            "tooltip": {"mode": "multi", "sort": "none"},
        },
        defaults=defaults, overrides=color_overrides(series),
    )


def xy(title, grid, queries: list[tuple[str, str, str]], *, x_label: str, x_log=False, y_log=True,
       y_unit="µs", description="", x_unit="none", x_min=None, x_max=None) -> dict:
    """queries: (sql, имя серии, режим points|lines). Каждый запрос — отдельный кадр: x, y."""
    targets, overrides, series = [], [], []
    for i, (sql, name, mode) in enumerate(queries):
        ref = chr(ord("A") + i)
        targets.append(target(sql, ref))
        series.append({
            "frame": {"matcher": {"id": "byIndex", "options": i}},
            "x": {"matcher": {"id": "byName", "options": "x"}},
            "y": {"matcher": {"id": "byName", "options": name}},
            "name": {"fixed": name},
        })
        props = [{"id": "custom.show", "value": mode}]
        if mode == "points":
            props.append({"id": "custom.pointSize.fixed", "value": 2 if "время" in x_label else 8})
            if "…" in name:  # отметки требуемых перцентилей: цвет линии уже есть в легенде
                props.append({"id": "custom.hideFrom", "value": {"legend": True, "tooltip": False, "viz": False}})
        else:
            props.append({"id": "custom.lineWidth", "value": 2})
            props.append({"id": "custom.pointSize.fixed", "value": 1})
        if name in COLORS:
            props.append({"id": "color", "value": {"mode": "fixed", "fixedColor": COLORS[name]}})
        overrides.append({"matcher": {"id": "byName", "options": name}, "properties": props})
    overrides.append({
        "matcher": {"id": "byName", "options": "x"},
        "properties": [
            {"id": "unit", "value": x_unit},
            {"id": "custom.axisLabel", "value": x_label},
            {"id": "custom.scaleDistribution",
             "value": {"type": "log", "log": 10} if x_log else {"type": "linear"}},
            *([{"id": "min", "value": x_min}] if x_min is not None else []),
            *([{"id": "max", "value": x_max}] if x_max is not None else []),
        ],
    })
    return panel(
        "xychart", title, grid, targets, description=description,
        options={"mapping": "manual", "series": series,
                 "legend": {"showLegend": True, "displayMode": "list", "placement": "bottom"},
                 "tooltip": {"mode": "single", "sort": "none"}},
        defaults={
            "unit": y_unit,
            "color": {"mode": "fixed", "fixedColor": "#2a78d6"},
            "custom": {"show": "points", "pointSize": {"fixed": 5}, "pointShape": "circle",
                       "pointStrokeWidth": 1, "fillOpacity": 60, "lineWidth": 2, "axisPlacement": "auto",
                       "axisBorderShow": False,
                       "scaleDistribution": {"type": "log", "log": 10} if y_log else {"type": "linear"}},
        },
        overrides=overrides,
    )


def stat(title, grid, sql, *, unit="none", decimals=0, description="") -> dict:
    return panel(
        "stat", title, grid, [target(sql)], description=description,
        options={"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                 "colorMode": "none", "graphMode": "none", "textMode": "value", "justifyMode": "center",
                 "orientation": "auto", "text": {"valueSize": 34}},
        defaults={"unit": unit, "decimals": decimals, "color": {"mode": "fixed", "fixedColor": "#0b0b0b"}},
    )


def pivot(value: str, where: str, group: str, label: str, order: str, table: str, join: str = "") -> str:
    return f"""SELECT {group} AS "{label}",
        max({value}) FILTER (WHERE m.target = 'sql') AS "{SQL_LABEL}",
        max({value}) FILTER (WHERE m.target = 'orm') AS "{ORM_LABEL}"
        FROM {table} m {join} WHERE {where} GROUP BY {group}, {order} ORDER BY {order}"""


def build() -> dict:
    y = 0
    # --- плитки ----------------------------------------------------------------------------------
    stat("Прогонов (контейнеров)", (0, y, 5, 4), "SELECT count(*) AS v FROM runs")
    stat("Измерений в статистике", (5, y, 5, 4),
         "SELECT sum(ops) * (SELECT count(*) FROM runs) / count(*) AS v FROM phases WHERE phase = 'measure'")
    stat("Overhead замера, p50", (10, y, 5, 4),
         "SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY noop_ns) AS v FROM overhead", unit="ns",
         description="Тот же цикл замера с пустой функцией вместо операции")
    stat("CPU на прогон", (15, y, 4, 4),
         "SELECT max(array_length(string_to_array(trim(both '[]' from cpu), ','), 1)) AS v FROM runs")
    stat("Окружение", (19, y, 5, 4),
         "SELECT 'Python ' || max(python) || ' · SQLite ' || max(sqlite) AS v FROM runs")
    _panels[-1]["options"]["reduceOptions"]["fields"] = "/.*/"  # строковое значение
    _panels[-1]["options"]["text"] = {"valueSize": 16}
    y += 4

    # --- сводка ----------------------------------------------------------------------------------
    row("Сводка по всем сценариям", y)
    y += 1
    join_sc = "JOIN scenarios s USING (scenario)"
    bars("Медиана p50 по сценариям", (0, y, 12, 9),
         pivot("m.latency_us", "m.p = 0.5", "s.short", "сценарий", "s.ord", "summary", join_sc),
         [SQL_LABEL, ORM_LABEL])
    bars("Хвост p99 по сценариям", (12, y, 12, 9),
         pivot("m.latency_us", "m.p = 0.99", "s.short", "сценарий", "s.ord", "summary", join_sc),
         [SQL_LABEL, ORM_LABEL])
    y += 9
    bars("Во сколько раз ORM медленнее чистого SQL", (0, y, 12, 8), """
        SELECT s.short AS "сценарий",
          max(latency_us) FILTER (WHERE target = 'orm' AND p = 0.5)
            / max(latency_us) FILTER (WHERE target = 'sql' AND p = 0.5) AS "по медиане p50",
          max(latency_us) FILTER (WHERE target = 'orm' AND p = 0.99)
            / max(latency_us) FILTER (WHERE target = 'sql' AND p = 0.99) AS "по хвосту p99"
        FROM summary JOIN scenarios s USING (scenario) GROUP BY s.short, s.ord ORDER BY s.ord""",
         ["по медиане p50", "по хвосту p99"], unit="prefix:×", log=False, decimals=1, min_value=0)
    bars("Доля overhead инструмента в медиане операции", (12, y, 12, 8),
         pivot("m.share_pct", "true", "s.short", "сценарий", "s.ord",
               "(SELECT scenario, target, percentile_cont(0.5) WITHIN GROUP (ORDER BY share_pct) AS share_pct "
               "FROM overhead GROUP BY scenario, target)", join_sc),
         [SQL_LABEL, ORM_LABEL], unit="percent", log=False, decimals=2, min_value=0,
         description="overhead (пустая операция в цикле замера) / p50 операции, медиана по прогонам")
    y += 8

    # --- сценарий --------------------------------------------------------------------------------
    row("Сценарий: $scenario", y)
    y += 1
    bars("Требуемые перцентили 0.5 / 0.75 / 0.9 / 0.95 / 0.99", (0, y, 12, 9),
         pivot("m.latency_us", f"m.scenario = {SC} AND m.p <= 0.99", "m.label", "перцентиль", "m.p", "summary"),
         [SQL_LABEL, ORM_LABEL])
    xy("Распределение по перцентилям (логарифмическая шкала, одна линия на реализацию)", (12, y, 12, 9), [
        (f"SELECT nines AS x, latency_us AS \"{SQL_LABEL}\" FROM curve WHERE scenario = {SC} AND target = 'sql' "
         "ORDER BY nines", SQL_LABEL, "lines"),
        (f"SELECT nines AS x, latency_us AS \"{ORM_LABEL}\" FROM curve WHERE scenario = {SC} AND target = 'orm' "
         "ORDER BY nines", ORM_LABEL, "lines"),
        (f"SELECT -log(1 - p) AS x, latency_us AS \"SQL · p50…p99\" FROM summary WHERE scenario = {SC} "
         "AND target = 'sql' AND p <= 0.99 ORDER BY p", "SQL · p50…p99", "points"),
        (f"SELECT -log(1 - p) AS x, latency_us AS \"ORM · p50…p99\" FROM summary WHERE scenario = {SC} "
         "AND target = 'orm' AND p <= 0.99 ORDER BY p", "ORM · p50…p99", "points"),
    ], x_label="перцентиль, «девятки»: 0.3 = 50 %, 1 = 90 %, 2 = 99 %, 3 = 99.9 %, 4 = 99.99 %",
        x_min=0, description="x = −log10(1 − p); точки — требуемые перцентили. Все прогоны пары вместе.")
    COLORS["SQL · p50…p99"] = COLORS[SQL_LABEL]
    COLORS["ORM · p50…p99"] = COLORS[ORM_LABEL]
    _fix_colors(_panels[-1])
    y += 9
    xy("Гистограмма распределения (логарифмические корзины)", (0, y, 12, 9), [
        (f"SELECT bin_us AS x, share_pct AS \"{SQL_LABEL}\" FROM histogram WHERE scenario = {SC} "
         "AND target = 'sql' ORDER BY bin_us", SQL_LABEL, "lines"),
        (f"SELECT bin_us AS x, share_pct AS \"{ORM_LABEL}\" FROM histogram WHERE scenario = {SC} "
         "AND target = 'orm' ORDER BY bin_us", ORM_LABEL, "lines"),
    ], x_label="задержка", x_log=True, x_unit="µs", y_log=False, y_unit="percent")
    bars("Перцентили по видам операций (чтение / запись)", (12, y, 12, 9), f"""
        SELECT CASE kind WHEN 'read' THEN 'чтение ' ELSE 'запись ' END || label AS "операция",
          max(latency_us) FILTER (WHERE target = 'sql') AS "{SQL_LABEL}",
          max(latency_us) FILTER (WHERE target = 'orm') AS "{ORM_LABEL}"
        FROM kinds WHERE scenario = {SC} GROUP BY kind, label, p ORDER BY kind, p""",
         [SQL_LABEL, ORM_LABEL], value_size=9, rotate=-35)
    y += 9
    for i, (tgt, label) in enumerate((("sql", SQL_LABEL), ("orm", ORM_LABEL))):
        COLORS[f"measure · {label}"] = COLORS[label]
        xy(f"Задержка во времени — {label} (прогон r00, все фазы)", (12 * i, y, 12, 9), [
            *[(f"SELECT t_s AS x, latency_us AS \"{name}\" FROM timeline WHERE scenario = {SC} "
               f"AND target = '{tgt}' AND phase = '{phase}' ORDER BY t_s", name, "points")
              for phase, name in (("warmup", "warmup"), ("measure", f"measure · {label}"),
                                  ("teardown", "teardown"))],
            (f"SELECT t_s AS x, latency_us AS \"скользящая медиана\" FROM timeline_median "
             f"WHERE scenario = {SC} AND target = '{tgt}' ORDER BY t_s", "скользящая медиана", "lines"),
        ], x_label="время от начала прогрева", x_unit="s", x_min=0)
        _fix_colors(_panels[-1])
    y += 9
    phases_sql = """SELECT t.label AS "реализация", {cols}
        FROM phases p JOIN targets t USING (target) WHERE p.scenario = {sc}
        GROUP BY t.label, t.ord ORDER BY t.ord"""
    ops_cols = ", ".join(
        f"max(ops) FILTER (WHERE phase = '{ph}') AS \"{name}\""
        for ph, name in (("warmup", "warmup (прогрев)"), ("measure", "measure (замер)"),
                         ("teardown", "teardown (хвост)")))
    dur_cols = ", ".join(
        f"max(duration_s) FILTER (WHERE phase = '{ph}') AS \"{name}\""
        for ph, name in (("other", "setup + калибровка + cleanup"), ("warmup", "warmup (прогрев)"),
                         ("measure", "measure (замер)"), ("teardown", "teardown (хвост)")))
    bars("Количество операций по фазам (среднее на прогон)", (0, y, 12, 7),
         phases_sql.format(cols=ops_cols, sc=SC),
         ["warmup (прогрев)", "measure (замер)", "teardown (хвост)"],
         unit="short", log=False, decimals=0, horizontal=True, stacked=True, min_value=0)
    bars("Время выполнения теста по фазам (среднее на прогон)", (12, y, 12, 7),
         phases_sql.format(cols=dur_cols, sc=SC),
         ["setup + калибровка + cleanup", "warmup (прогрев)", "measure (замер)", "teardown (хвост)"],
         unit="s", log=False, decimals=2, horizontal=True, stacked=True, min_value=0)
    y += 7
    bars("Стабильность: отклонение p50 каждого прогона от медианы прогонов", (0, y, 24, 7), f"""
        WITH med AS (SELECT target, percentile_cont(0.5) WITHIN GROUP (ORDER BY p50_us) AS m
                     FROM runs WHERE scenario = {SC} GROUP BY target)
        SELECT 'r' || lpad(repeat::text, 2, '0') AS "прогон",
          max((p50_us / m - 1) * 100) FILTER (WHERE target = 'sql') AS "{SQL_LABEL}",
          max((p50_us / m - 1) * 100) FILTER (WHERE target = 'orm') AS "{ORM_LABEL}"
        FROM runs JOIN med USING (target) WHERE scenario = {SC} GROUP BY repeat ORDER BY repeat""",
         [SQL_LABEL, ORM_LABEL], unit="percent", log=False, decimals=1,
         description="Каждый прогон — отдельный контейнер; разброс показывает воспроизводимость условий")

    return {
        "uid": "wildlife-bench",
        "title": "ЛР3 — SQL vs ORM (микробенчмарк)",
        "tags": ["lab3", "benchmark"],
        "timezone": "browser",
        "editable": False,
        "graphTooltip": 0,
        "time": {"from": "now-1h", "to": "now"},
        "timepicker": {"hidden": True},
        "refresh": "",
        "schemaVersion": 39,
        "templating": {"list": [{
            "name": "scenario", "label": "Сценарий", "type": "query", "datasource": DS,
            "query": "SELECT short AS __text, scenario AS __value FROM scenarios ORDER BY ord",
            "definition": "SELECT short AS __text, scenario AS __value FROM scenarios ORDER BY ord",
            "refresh": 1, "current": {}, "multi": False, "includeAll": False, "sort": 0,
        }]},
        "panels": _panels,
    }


def _fix_colors(p: dict) -> None:
    """Повторно проставить цвета серий, добавленных в COLORS после создания панели."""
    for ov in p["fieldConfig"]["overrides"]:
        name = ov["matcher"]["options"]
        if name in COLORS and not any(pr["id"] == "color" for pr in ov["properties"]):
            ov["properties"].append({"id": "color", "value": {"mode": "fixed", "fixedColor": COLORS[name]}})


if __name__ == "__main__":
    out = Path(__file__).parent / "dashboards" / "bench.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"dashboard: {out}")
