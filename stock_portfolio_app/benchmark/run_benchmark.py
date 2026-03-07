#!/usr/bin/env python3
"""
Run safe API performance benchmarks against a cloned SQLite database.

This script always clones the source database into data/benchmark/ and starts
an isolated API process pointing to that clone via PORTFOLIO_DB_PATH.
It then runs Locust headless, stores artifacts, and appends a summary to
stock_portfolio_app/benchmark/results/results.md.
"""

from __future__ import annotations

import argparse
import csv
import os
import socket
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List


@dataclass
class BenchmarkConfig:
    profile: str
    users: int
    spawn_rate: int
    duration: str
    api_port: int
    source_db: Path
    benchmark_db: Path
    results_prefix: str
    run_id: str


def parse_args(repo_root: Path) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run safe API benchmark on cloned DB.")
    parser.add_argument("--profile", choices=["read_heavy", "mixed"], default="read_heavy")
    parser.add_argument("--users", type=int, default=50)
    parser.add_argument("--spawn-rate", type=int, default=10, dest="spawn_rate")
    parser.add_argument("--duration", default="2m", help="Locust run duration (e.g. 45s, 2m)")
    parser.add_argument("--api-port", type=int, default=8010, dest="api_port")
    parser.add_argument(
        "--source-db",
        default=str(repo_root / "data" / "portfolio.db"),
        help="Path to source DB that will be cloned before benchmark",
    )
    return parser.parse_args()


def wait_for_healthcheck(host: str, timeout_seconds: int = 60) -> None:
    deadline = time.time() + timeout_seconds
    last_error = "unknown"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{host}/api/health", timeout=3) as response:
                if response.status == 200:
                    return
                last_error = f"status={response.status}"
        except urllib.error.URLError as exc:
            last_error = str(exc)
        except TimeoutError as exc:
            last_error = str(exc)
        time.sleep(1)
    raise RuntimeError(f"API did not become healthy in time ({last_error})")


def ensure_port_available(port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError as exc:
            raise RuntimeError(
                f"Port {port} is already in use. Choose another --api-port to avoid "
                "accidentally hitting an existing API process."
            ) from exc


def read_stats(stats_csv: Path) -> tuple[dict, List[dict]]:
    with stats_csv.open("r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    aggregated = next((r for r in rows if r["Name"] == "Aggregated"), None)
    if aggregated is None:
        raise RuntimeError(f"Missing Aggregated row in {stats_csv}")
    endpoint_rows = [r for r in rows if r["Name"] != "Aggregated" and r["Name"]]
    return aggregated, endpoint_rows


def append_results_markdown(config: BenchmarkConfig, aggregated: dict, endpoint_rows: List[dict], results_md: Path) -> None:
    endpoint_rows_sorted = sorted(
        endpoint_rows,
        key=lambda row: float(row.get("95%", 0) or 0),
        reverse=True,
    )
    top_slow = endpoint_rows_sorted[:5]

    results_md.parent.mkdir(parents=True, exist_ok=True)
    if not results_md.exists():
        results_md.write_text("# Benchmark Run Summaries\n\n", encoding="utf-8")

    fail_count = int(aggregated["Failure Count"])
    req_count = int(aggregated["Request Count"])
    fail_rate = (100.0 * fail_count / req_count) if req_count else 0.0
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        f"## {generated} - {config.profile}",
        "",
        f"- **Config:** users={config.users}, spawn_rate={config.spawn_rate}/s, duration={config.duration}, api_port={config.api_port}",
        f"- **DB Clone:** `{config.benchmark_db}`",
        f"- **Artifacts:** `{config.results_prefix}_stats.csv`, `{config.results_prefix}_failures.csv`, `{config.results_prefix}_stats_history.csv`, `{config.results_prefix}.html`",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Requests | {req_count} |",
        f"| Failures | {fail_count} ({fail_rate:.2f}%) |",
        f"| RPS | {aggregated['Requests/s']} |",
        f"| p50 (ms) | {aggregated['50%']} |",
        f"| p95 (ms) | {aggregated['95%']} |",
        f"| p99 (ms) | {aggregated['99%']} |",
        "",
        "| Slow Endpoints (p95) | p95 (ms) | Failures |",
        "|---|---|---|",
    ]

    for row in top_slow:
        lines.append(f"| `{row['Name']}` | {row['95%']} | {row['Failure Count']} |")

    lines.extend(["", ""])
    with results_md.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    benchmark_root = Path(__file__).resolve().parent
    results_dir = benchmark_root / "results"
    benchmark_db_dir = repo_root / "data" / "benchmark"

    args = parse_args(repo_root)

    source_db = Path(args.source_db).resolve()
    if not source_db.exists():
        print(f"Source DB not found: {source_db}", file=sys.stderr)
        return 2

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    benchmark_db_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    benchmark_db = benchmark_db_dir / f"portfolio_benchmark_{run_id}.db"
    shutil.copy2(source_db, benchmark_db)
    if benchmark_db.resolve() == source_db.resolve():
        print("Safety check failed: benchmark DB matches source DB.", file=sys.stderr)
        return 2

    results_prefix = str(results_dir / f"run_{run_id}_{args.profile}")
    config = BenchmarkConfig(
        profile=args.profile,
        users=args.users,
        spawn_rate=args.spawn_rate,
        duration=args.duration,
        api_port=args.api_port,
        source_db=source_db,
        benchmark_db=benchmark_db,
        results_prefix=results_prefix,
        run_id=run_id,
    )

    api_env = os.environ.copy()
    api_env["PORTFOLIO_DB_PATH"] = str(benchmark_db)
    python_bin = repo_root / ".venv" / "bin" / "python"
    locust_bin = repo_root / ".venv" / "bin" / "locust"

    if not python_bin.exists() or not locust_bin.exists():
        print("Missing .venv binaries (.venv/bin/python and .venv/bin/locust required)", file=sys.stderr)
        return 2
    try:
        ensure_port_available(args.api_port)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    api_cmd = [
        str(python_bin),
        "-m",
        "uvicorn",
        "api.app:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(args.api_port),
    ]
    locust_cmd = [
        str(locust_bin),
        "-f",
        str(benchmark_root / "locustfile.py"),
        "--host",
        f"http://127.0.0.1:{args.api_port}",
        "--headless",
        "-u",
        str(args.users),
        "-r",
        str(args.spawn_rate),
        "--run-time",
        args.duration,
        "--csv",
        results_prefix,
        "--html",
        f"{results_prefix}.html",
    ]

    api_proc = subprocess.Popen(
        api_cmd,
        cwd=str(repo_root / "stock_portfolio_app"),
        env=api_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        wait_for_healthcheck(f"http://127.0.0.1:{args.api_port}", timeout_seconds=60)

        locust_env = os.environ.copy()
        locust_env["PERF_PROFILE"] = args.profile
        subprocess.run(locust_cmd, cwd=str(repo_root), env=locust_env, check=True)

        stats_csv = Path(f"{results_prefix}_stats.csv")
        aggregated, endpoints = read_stats(stats_csv)
        append_results_markdown(config, aggregated, endpoints, results_dir / "results.md")

        print(f"Benchmark completed successfully: {config.run_id}")
        print(f"Results: {results_prefix}_stats.csv and {results_prefix}.html")
        print(f"Summary appended to: {results_dir / 'results.md'}")
        return 0
    finally:
        api_proc.terminate()
        try:
            api_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            api_proc.kill()
            api_proc.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
