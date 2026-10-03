#!/usr/bin/env python3
"""
scripts/bench_ram.py
Gate A benchmark — full-stack peak RAM measurement.

Reads `docker stats` for all conversx containers, sums their memory usage,
and compares against the 8.5 GB gate limit.

Run after `docker compose up -d` with all services healthy.

Usage:
    python scripts/bench_ram.py
    python scripts/bench_ram.py --watch --interval 5   # poll every 5s
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


CONVERSX_CONTAINERS = [
    "conversx-api",
    "conversx-worker",
    "conversx-postgres",
    "conversx-redis",
    "conversx-ollama",
    "conversx-prometheus",
    "conversx-uptime-kuma",
]

GATE_LIMIT_MB = 8.5 * 1024  # 8.5 GB in MB


def parse_mem(mem_str: str) -> float:
    """Parse '1.23GiB' or '512MiB' into MB."""
    mem_str = mem_str.strip()
    if "GiB" in mem_str:
        return float(mem_str.replace("GiB", "")) * 1024
    elif "MiB" in mem_str:
        return float(mem_str.replace("MiB", ""))
    elif "kB" in mem_str:
        return float(mem_str.replace("kB", "")) / 1024
    elif "B" in mem_str:
        return float(mem_str.replace("B", "")) / 1024 / 1024
    return 0.0


def sample_ram() -> dict[str, float]:
    """Take one snapshot of all conversx container RAM usage."""
    result = subprocess.run(
        [
            "docker", "stats", "--no-stream", "--format",
            "{{.Name}}\t{{.MemUsage}}",
        ] + CONVERSX_CONTAINERS,
        capture_output=True, text=True, timeout=15,
    )

    container_ram: dict[str, float] = {}
    for line in result.stdout.strip().splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        name = parts[0].strip()
        mem_usage = parts[1].split("/")[0].strip()
        container_ram[name] = round(parse_mem(mem_usage), 1)

    return container_ram


def report(container_ram: dict[str, float], timestamp: float) -> dict:
    total_mb = sum(container_ram.values())
    gate_pass = total_mb <= GATE_LIMIT_MB

    print(f"\n[bench_ram] Snapshot at {time.strftime('%H:%M:%S', time.localtime(timestamp))}")
    print(f"{'Container':<30} {'RAM (MB)':>10}")
    print("-" * 42)
    for name in CONVERSX_CONTAINERS:
        mb = container_ram.get(name, -1)
        status = f"{mb:>10.0f}" if mb >= 0 else "     n/a"
        print(f"  {name:<28} {status}")
    print("-" * 42)
    print(f"  {'TOTAL':<28} {total_mb:>10.0f}")
    print(f"  {'GATE LIMIT (8.5 GB)':<28} {GATE_LIMIT_MB:>10.0f}")
    gate_str = "PASS ✓" if gate_pass else "FAIL ✗"
    print(f"  Gate A: {gate_str} (used {total_mb/1024:.2f} GB of 8.5 GB)")

    return {
        "timestamp": timestamp,
        "containers": container_ram,
        "total_mb": round(total_mb, 1),
        "gate_limit_mb": GATE_LIMIT_MB,
        "gate_a_pass": gate_pass,
        "utilisation_pct": round(total_mb / GATE_LIMIT_MB * 100, 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Gate A full-stack RAM benchmark")
    parser.add_argument("--watch", action="store_true",
                        help="Continuously poll every --interval seconds")
    parser.add_argument("--interval", type=int, default=10,
                        help="Poll interval in seconds (with --watch)")
    parser.add_argument("--duration", type=int, default=60,
                        help="Watch duration in seconds (with --watch)")
    args = parser.parse_args()

    results = []
    results_file = Path("/benchmark_results/ram_results.jsonl")
    results_file.parent.mkdir(parents=True, exist_ok=True)

    if args.watch:
        print(f"[bench_ram] Watching for {args.duration}s (interval {args.interval}s)...")
        deadline = time.time() + args.duration
        while time.time() < deadline:
            ts = time.time()
            container_ram = sample_ram()
            result = report(container_ram, ts)
            results.append(result)
            with open(results_file, "a") as f:
                f.write(json.dumps(result) + "\n")
            time.sleep(args.interval)

        peak = max(results, key=lambda r: r["total_mb"])
        print(f"\n[bench_ram] Peak during watch: {peak['total_mb']/1024:.2f} GB")
        gate_pass = peak["gate_a_pass"]
    else:
        ts = time.time()
        container_ram = sample_ram()
        result = report(container_ram, ts)
        results.append(result)
        with open(results_file, "a") as f:
            f.write(json.dumps(result) + "\n")
        gate_pass = result["gate_a_pass"]

    sys.exit(0 if gate_pass else 1)


if __name__ == "__main__":
    main()
