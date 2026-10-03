#!/usr/bin/env python3
"""
scripts/bench_llm.py
Gate A benchmark — Ollama LLM throughput.

Measures:
  - Tokens per second (eval rate) for each candidate model
  - Time to first token (TTFT)
  - RAM usage of the Ollama container (via docker stats)

Run after Ollama is started (see scripts/run_benchmarks.sh).
CPU-only gate. Results written to /benchmark_results/llm_results.jsonl.

Usage:
    python scripts/bench_llm.py --model qwen2.5:3b
    python scripts/bench_llm.py --model qwen2.5:1.5b
    python scripts/bench_llm.py --model llama3.2:3b
    python scripts/bench_llm.py --model gemma2:2b
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import httpx

OLLAMA_BASE_URL = "http://localhost:11434"
TEST_PROMPT = (
    "You are a helpful communication coach. "
    "Give a single professional tip for improving clarity in a job interview. "
    "Be concise. Reply in exactly 2-3 sentences."
)
MAX_TOKENS = 120


def wait_for_ollama(timeout: int = 120) -> bool:
    """Wait until Ollama is responsive."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


def pull_model(model: str) -> None:
    """Pull the model if not already present."""
    print(f"[bench_llm] Pulling model: {model} (may take several minutes on 25 Mbps)", flush=True)
    with httpx.stream("POST", f"{OLLAMA_BASE_URL}/api/pull",
                      json={"name": model}, timeout=1800) as r:
        for line in r.iter_lines():
            if line:
                data = json.loads(line)
                status = data.get("status", "")
                if "pulling" in status or "verifying" in status or "success" in status:
                    print(f"  {status}", flush=True)


def benchmark_model(model: str, num_runs: int = 3) -> dict:
    """Run the model N times and collect timing stats."""
    run_results = []

    for run_i in range(num_runs):
        print(f"[bench_llm] Run {run_i + 1}/{num_runs} for {model}...", flush=True)

        start = time.perf_counter()
        first_token_time = None
        total_tokens = 0

        with httpx.stream(
            "POST",
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": model,
                "prompt": TEST_PROMPT,
                "stream": True,
                "options": {
                    "num_predict": MAX_TOKENS,
                    "num_thread": 2,   # match 2-CPU gate limit
                    "temperature": 0.7,
                },
            },
            timeout=120,
        ) as response:
            for line in response.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                if data.get("response") and first_token_time is None:
                    first_token_time = time.perf_counter() - start
                if not data.get("done", False):
                    total_tokens += 1
                else:
                    # Ollama eval stats in the done message
                    eval_duration_ns = data.get("eval_duration", 0)
                    eval_count = data.get("eval_count", total_tokens)
                    prompt_eval_ns = data.get("prompt_eval_duration", 0)
                    break

        wall_clock = time.perf_counter() - start
        tokens_per_second = (eval_count / (eval_duration_ns / 1e9)) if eval_duration_ns > 0 else 0

        run_result = {
            "run": run_i + 1,
            "wall_clock_s": round(wall_clock, 3),
            "ttft_s": round(first_token_time or 0, 3),
            "tokens_generated": eval_count,
            "tokens_per_second": round(tokens_per_second, 2),
            "prompt_eval_ms": round(prompt_eval_ns / 1e6, 1),
            "gate_pass": tokens_per_second >= 5.0,
        }
        run_results.append(run_result)
        print(
            f"  tokens/s={tokens_per_second:.1f} "
            f"({'PASS ✓' if run_result['gate_pass'] else 'FAIL ✗'}) "
            f"TTFT={first_token_time:.2f}s wall={wall_clock:.1f}s",
            flush=True,
        )

    avg_tps = sum(r["tokens_per_second"] for r in run_results) / len(run_results)
    min_tps = min(r["tokens_per_second"] for r in run_results)

    return {
        "model": model,
        "num_runs": num_runs,
        "max_tokens": MAX_TOKENS,
        "runs": run_results,
        "avg_tokens_per_second": round(avg_tps, 2),
        "min_tokens_per_second": round(min_tps, 2),
        "gate_a_pass": min_tps >= 5.0,  # worst run must pass
    }


def get_ollama_container_ram_mb() -> float:
    """Read Ollama container memory usage via docker stats (one snapshot)."""
    try:
        result = subprocess.run(
            ["docker", "stats", "--no-stream", "--format",
             "{{.MemUsage}}", "conversx-ollama"],
            capture_output=True, text=True, timeout=10,
        )
        # Format: "1.23GiB / 9GiB"
        mem_str = result.stdout.strip().split("/")[0].strip()
        if "GiB" in mem_str:
            return float(mem_str.replace("GiB", "")) * 1024
        elif "MiB" in mem_str:
            return float(mem_str.replace("MiB", ""))
        return -1
    except Exception:
        return -1


def main() -> None:
    parser = argparse.ArgumentParser(description="Gate A LLM benchmark")
    parser.add_argument("--model", default="qwen2.5:3b",
                        help="Ollama model tag to benchmark")
    parser.add_argument("--pull", action="store_true",
                        help="Pull the model before benchmarking")
    parser.add_argument("--runs", type=int, default=3,
                        help="Number of inference runs to average")
    args = parser.parse_args()

    print(f"[bench_llm] Waiting for Ollama at {OLLAMA_BASE_URL}...", flush=True)
    if not wait_for_ollama():
        print("[bench_llm] ERROR: Ollama not reachable", file=sys.stderr)
        sys.exit(1)

    if args.pull:
        pull_model(args.model)

    ram_before = get_ollama_container_ram_mb()
    result = benchmark_model(args.model, num_runs=args.runs)
    ram_after = get_ollama_container_ram_mb()

    result["ollama_ram_before_mb"] = round(ram_before, 1)
    result["ollama_ram_after_mb"] = round(ram_after, 1)

    print("\n=== RESULT JSON ===")
    print(json.dumps(result, indent=2))

    results_file = Path("/benchmark_results/llm_results.jsonl")
    results_file.parent.mkdir(parents=True, exist_ok=True)
    with open(results_file, "a") as f:
        f.write(json.dumps(result) + "\n")

    gate = "PASS ✓" if result["gate_a_pass"] else "FAIL ✗"
    print(f"\n[bench_llm] Gate A: {gate} (min {result['min_tokens_per_second']} t/s, need ≥ 5)")
    sys.exit(0 if result["gate_a_pass"] else 1)


if __name__ == "__main__":
    main()
