"""CLI бенчмарка.

    python -m bench run --target sql --scenario read_by_id --repeat 0 --out results/bench/raw
    python -m bench report --raw results/bench/raw --out results/bench/report
    python -m bench grafana --raw results/bench/raw --out results/bench/grafana/01_bench.sql.gz
    python -m bench verify
    python -m bench list
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
from pathlib import Path


def _cmd_run(args: argparse.Namespace) -> int:
    from bench.harness import Config, run

    config = Config(
        warmup_min=args.warmup_min,
        warmup_max=args.warmup_max,
        measure=args.measure,
        teardown=args.teardown,
        calibration=args.calibration,
    )
    result = run(args.target, args.scenario, config, repeat=args.repeat, seed=args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{args.scenario}__{args.target}__r{args.repeat:02d}.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, separators=(",", ":"))

    s, o, d = result["summary"], result["overhead"], result["durations_ns"]
    p = s["percentiles"]
    counts = "/".join(str(ph["count"]) for ph in result["phases"])
    print(
        f"[bench] {args.scenario:<12} {args.target:<3} r{args.repeat:02d}  "
        f"p50={p['0.5'] / 1e3:8.2f}us p99={p['0.99'] / 1e3:8.2f}us  "
        f"overhead p50={o['percentiles']['0.5']:.0f}ns  "
        f"ops warmup/measure/teardown={counts}  total={d['total'] / 1e9:.2f}s  "
        f"cpus={result['environment']['cpu_affinity']}",
        flush=True,
    )
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    from bench.report import build_report

    index = build_report(Path(args.raw), Path(args.out))
    print(f"[bench] отчёт: {index}")
    return 0


def _cmd_grafana(args: argparse.Namespace) -> int:
    from bench.grafana_export import export_sql

    path = export_sql(Path(args.raw), Path(args.out))
    print(f"[bench] данные для Grafana: {path}")
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    from bench.verify import verify

    problems = verify(ops=args.ops)
    for problem in problems:
        print(f"[verify] FAIL {problem}", file=sys.stderr)
    return 1 if problems else 0


def _cmd_list(_args: argparse.Namespace) -> int:
    from bench.scenarios import SCENARIOS, TARGETS

    print("targets:  ", " ".join(TARGETS))
    print("scenarios:", " ".join(SCENARIOS))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m bench")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="один прогон: реализация × сценарий")
    run_p.add_argument("--target", required=True)
    run_p.add_argument("--scenario", required=True)
    run_p.add_argument("--repeat", type=int, default=0)
    run_p.add_argument("--seed", type=int, default=2026)
    run_p.add_argument("--out", default=os.environ.get("BENCH_RAW", "results/bench/raw"))
    run_p.add_argument("--warmup-min", type=int, default=2_000)
    run_p.add_argument("--warmup-max", type=int, default=20_000)
    run_p.add_argument("--measure", type=int, default=20_000)
    run_p.add_argument("--teardown", type=int, default=1_000)
    run_p.add_argument("--calibration", type=int, default=50_000)
    run_p.set_defaults(func=_cmd_run)

    report_p = sub.add_parser("report", help="графики по сырым результатам")
    report_p.add_argument("--raw", default="results/bench/raw")
    report_p.add_argument("--out", default="results/bench/report")
    report_p.set_defaults(func=_cmd_report)

    grafana_p = sub.add_parser("grafana", help="SQL-дамп результатов для дашборда Grafana")
    grafana_p.add_argument("--raw", default="results/bench/raw")
    grafana_p.add_argument("--out", default="results/bench/grafana/01_bench.sql.gz")
    grafana_p.set_defaults(func=_cmd_grafana)

    verify_p = sub.add_parser("verify", help="SQL и ORM дают одинаковые результаты на одном плане")
    verify_p.add_argument("--ops", type=int, default=300)
    verify_p.set_defaults(func=_cmd_verify)

    list_p = sub.add_parser("list", help="реализации и сценарии")
    list_p.set_defaults(func=_cmd_list)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
