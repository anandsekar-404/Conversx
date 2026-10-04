#!/usr/bin/env python3
"""
scripts/bench_llm.py
Gate A benchmark - Ollama LLM throughput.

Measures:
  - Model load time (reported separately from generation speed)
  - One warm-up run (discarded from steady-state metrics)
  - Tokens per second (eval rate) per run on a realistic role-play turn (~100-150 tokens context -> 100-token reply)
  - Time to first token (TTFT)
  - Worst run speed (Gate A target: worst run >= 5.0 tokens/s)

Run inside the benchmark Docker container or client container connected to conversx_default.
CPU-only gate. Results written to /benchmark_results/llm_results.jsonl.

Usage:
    python scripts/bench_llm.py --model qwen2.5:3b --url http://ollama:11434
    python scripts/bench_llm.py --model qwen2.5:1.5b --url http://ollama:11434
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434")

# Realistic role-play prompt: ~130 tokens of context, requesting ~100 tokens of feedback
REALISTIC_ROLEPLAY_PROMPT = (
    "Scenario: Behavioral interview for a Senior Engineering role.\n"
    "Context: The candidate answered: 'In my last project, our payment service experienced intermittent "
    "504 timeouts during a high-traffic marketing campaign. Instead of jumping to add more servers, I analyzed "
    "the connection pool metrics, found that our PostgreSQL connection pool was exhausted by unindexed queries, "
    "and introduced Redis caching for hot read paths. That dropped latency by 80% and resolved the timeouts.'\n\n"
    "Task: Provide constructive feedback in about 100 words. Point out one strong aspect of the candidate's answer "
    "using the STAR method, suggest one area for improvement regarding business impact or stakeholder communication, "
    "and ask one targeted follow-up question to probe deeper."
)
TARGET_REPLY_TOKENS = 100


def wait_for_ollama(base_url: str, timeout: int = 120) -> bool:
    """Wait until Ollama is responsive."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(f"{base_url}/api/tags", timeout=5)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


def pull_model(base_url: str, model: str) -> None:
    """Pull the model if not already present."""
    print(f"[bench_llm] Checking / pulling model: {model} (may take several minutes on 25 Mbps)", flush=True)
    with httpx.stream(
        "POST",
        f"{base_url}/api/pull",
        json={"name": model},
        timeout=1800,
    ) as r:
        for line in r.iter_lines():
            if line:
                try:
                    data = json.loads(line)
                    status = data.get("status", "")
                    if "pulling" in status or "verifying" in status or "success" in status:
                        completed = data.get("completed", 0)
                        total = data.get("total", 0)
                        if total > 0:
                            pct = (completed / total) * 100
                            print(f"\r  {status} ({pct:.1f}%)", end="", flush=True)
                        else:
                            print(f"\r  {status}", end="", flush=True)
                except Exception:
                    pass
    print("", flush=True)


def run_inference_turn(base_url: str, model: str, prompt: str, num_predict: int = 100) -> Tuple[Dict[str, Any], str]:
    """Execute one streaming generation turn against Ollama."""
    start = time.perf_counter()
    first_token_time: Optional[float] = None
    accumulated_text: List[str] = []
    final_stats: Dict[str, Any] = {}

    with httpx.stream(
        "POST",
        f"{base_url}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "num_predict": num_predict,
                "num_thread": 2,   # match 2-CPU gate limit
                "temperature": 0.7,
            },
        },
        timeout=180,
    ) as response:
        for line in response.iter_lines():
            if not line:
                continue
            data = json.loads(line)
            chunk = data.get("response", "")
            if chunk:
                if first_token_time is None:
                    first_token_time = time.perf_counter() - start
                accumulated_text.append(chunk)

            if data.get("done", False):
                final_stats = data
                break

    wall_clock = time.perf_counter() - start
    eval_count = final_stats.get("eval_count", len(accumulated_text))
    eval_duration_ns = final_stats.get("eval_duration", 0)
    prompt_eval_ns = final_stats.get("prompt_eval_duration", 0)
    load_duration_ns = final_stats.get("load_duration", 0)

    tps = (eval_count / (eval_duration_ns / 1e9)) if eval_duration_ns > 0 else (
        eval_count / wall_clock if wall_clock > 0 else 0
    )

    metrics = {
        "wall_clock_s": round(wall_clock, 3),
        "ttft_s": round(first_token_time or wall_clock, 3),
        "tokens_generated": eval_count,
        "tokens_per_second": round(tps, 2),
        "prompt_eval_ms": round(prompt_eval_ns / 1e6, 1),
        "load_duration_s": round(load_duration_ns / 1e9, 3),
        "gate_pass": tps >= 5.0,
    }
    return metrics, "".join(accumulated_text)


def benchmark_model(base_url: str, model: str, num_runs: int = 3) -> Dict[str, Any]:
    """Execute warm-up and measured runs for the candidate model."""
    print(f"\n[bench_llm] Starting benchmark for model '{model}'", flush=True)

    # 1. Warm-up Run (measures model load time; speed discarded from steady-state)
    print("[bench_llm] Executing warm-up run (will be discarded from steady-state metrics)...", flush=True)
    warmup_metrics, warmup_reply = run_inference_turn(
        base_url, model, REALISTIC_ROLEPLAY_PROMPT, num_predict=TARGET_REPLY_TOKENS
    )
    model_load_time_s = warmup_metrics.get("load_duration_s", 0) or warmup_metrics["ttft_s"]
    print(
        f"[bench_llm] Warm-up completed: {warmup_metrics['tokens_generated']} tokens, "
        f"{warmup_metrics['tokens_per_second']:.1f} t/s (DISCARDED). "
        f"Model load time: {model_load_time_s:.2f} s",
        flush=True,
    )

    # 2. Measured Steady-State Runs
    run_results = []
    for run_i in range(1, num_runs + 1):
        print(f"[bench_llm] Steady-state run {run_i}/{num_runs} for {model}...", flush=True)
        metrics, reply = run_inference_turn(
            base_url, model, REALISTIC_ROLEPLAY_PROMPT, num_predict=TARGET_REPLY_TOKENS
        )
        metrics["run"] = run_i
        run_results.append(metrics)
        gate_str = "PASS V" if metrics["gate_pass"] else "FAIL ?"
        print(
            f"  Run {run_i}: {metrics['tokens_per_second']:.1f} tokens/s ({gate_str}) | "
            f"TTFT={metrics['ttft_s']:.2f}s | wall={metrics['wall_clock_s']:.2f}s | "
            f"tokens={metrics['tokens_generated']}",
            flush=True,
        )

    tps_list = [r["tokens_per_second"] for r in run_results]
    avg_tps = sum(tps_list) / len(tps_list)
    min_tps = min(tps_list)
    max_tps = max(tps_list)
    gate_a_pass = min_tps >= 5.0  # Worst run must satisfy >= 5.0 tokens/s

    return {
        "model": model,
        "prompt_context": "Realistic communication coach behavioral interview scenario (~130 tokens)",
        "target_tokens": TARGET_REPLY_TOKENS,
        "model_load_time_s": model_load_time_s,
        "warmup_run": warmup_metrics,
        "num_runs": num_runs,
        "runs": run_results,
        "avg_tokens_per_second": round(avg_tps, 2),
        "min_tokens_per_second": round(min_tps, 2),
        "max_tokens_per_second": round(max_tps, 2),
        "gate_a_target": ">= 5.0 tokens/s on worst run",
        "gate_a_pass": gate_a_pass,
    }


def get_ollama_container_ram_mb() -> float:
    """Read Ollama container memory usage via docker stats if available."""
    try:
        result = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "{{.MemUsage}}", "conversx-ollama"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10,
        )
        mem_str = result.stdout.strip().split("/")[0].strip()
        if "GiB" in mem_str:
            return float(mem_str.replace("GiB", "")) * 1024
        elif "MiB" in mem_str:
            return float(mem_str.replace("MiB", ""))
        return -1
    except Exception:
        return -1


def main() -> None:
    parser = argparse.ArgumentParser(description="Gate A LLM benchmark (Ollama)")
    parser.add_argument("--model", default="qwen2.5:3b",
                        help="Ollama model tag to benchmark")
    parser.add_argument("--url", default=DEFAULT_OLLAMA_URL,
                        help="Ollama base URL (default: http://ollama:11434)")
    parser.add_argument("--pull", action="store_true",
                        help="Pull the model before benchmarking")
    parser.add_argument("--runs", type=int, default=3,
                        help="Number of steady-state runs to measure")
    args = parser.parse_args()

    print(f"[bench_llm] Connecting to Ollama at {args.url}...", flush=True)
    if not wait_for_ollama(args.url):
        print(f"[bench_llm] ERROR: Ollama not reachable at {args.url}", file=sys.stderr)
        sys.exit(1)

    if args.pull:
        pull_model(args.url, args.model)

    ram_before = get_ollama_container_ram_mb()
    result = benchmark_model(args.url, args.model, num_runs=args.runs)
    ram_after = get_ollama_container_ram_mb()

    result["ollama_ram_before_mb"] = round(ram_before, 1)
    result["ollama_ram_after_mb"] = round(ram_after, 1)

    print("\n=== RESULT JSON ===")
    print(json.dumps(result, indent=2))

    results_dir = Path("/benchmark_results")
    if not results_dir.exists():
        results_dir = Path("benchmark_results")
    results_dir.mkdir(parents=True, exist_ok=True)

    with open(results_dir / "llm_results.jsonl", "a") as f:
        f.write(json.dumps(result) + "\n")

    gate = "PASS V" if result["gate_a_pass"] else "FAIL ?"
    print(
        f"\n[bench_llm] Gate A Result: {gate} "
        f"(Worst run: {result['min_tokens_per_second']:.1f} t/s, "
        f"Avg: {result['avg_tokens_per_second']:.1f} t/s, "
        f"Load: {result['model_load_time_s']:.2f}s | Target: >= 5.0 t/s)"
    )
    sys.exit(0 if result["gate_a_pass"] else 1)


if __name__ == "__main__":
    main()
