"""
scripts/bench_ram.py
====================
Gate A RAM Benchmark for ConversX:
  1. Captures Idle baseline RAM across all running ConversX Docker containers.
  2. Runs concurrent STT, LLM, and rule-based moderation workloads.
  3. Samples memory usage from kernel cgroup (/sys/fs/cgroup/memory.peak)
     with streaming docker stats fallback.
  4. Inspects each container for OOMKilled events.
  5. Computes peak usage, records memory source per container, and compares against <= 8.5 GB gate.
  6. States explicitly that summed peaks represent an upper bound.
"""

import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

CONVERSX_CONTAINERS = [
    "conversx-postgres",
    "conversx-redis",
    "conversx-api",
    "conversx-worker",
    "conversx-ollama",
    "conversx-prometheus",
    "conversx-uptime-kuma",
]

GATE_LIMIT_MB = 8704.0  # 8.5 GB in MB


def parse_mem_to_mb(raw: str) -> float:
    """Parse docker stats memory strings (e.g. '45.2MiB', '1.2GiB', '500kB') to MB."""
    raw = raw.strip()
    match = re.match(r"^([\d.]+)\s*([A-Za-z]+)$", raw)
    if not match:
        return 0.0
    val = float(match.group(1))
    unit = match.group(2).lower()
    if "gib" in unit or "gb" in unit:
        return val * 1024.0
    elif "mib" in unit or "mb" in unit:
        return val
    elif "kib" in unit or "kb" in unit:
        return val / 1024.0
    elif "b" in unit:
        return val / (1024.0 * 1024.0)
    return val


def sample_container_ram() -> Dict[str, float]:
    """Capture a single snapshot of memory usage across all containers using docker stats."""
    cmd = ["docker", "stats", "--no-stream", "--format", "{{.Name}}\t{{.MemUsage}}"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
        ram_map: Dict[str, float] = {}
        for line in res.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                name = parts[0].strip()
                usage_part = parts[1].split("/")[0].strip()
                if name in CONVERSX_CONTAINERS:
                    ram_map[name] = parse_mem_to_mb(usage_part)
        for c in CONVERSX_CONTAINERS:
            if c not in ram_map:
                ram_map[c] = 0.0
        return ram_map
    except Exception as e:
        print(f"[bench_ram] Warning: failed to sample docker stats: {e}", file=sys.stderr)
        return {c: 0.0 for c in CONVERSX_CONTAINERS}


def get_cgroup_peak_ram(container_name: str) -> Optional[Tuple[float, str]]:
    """
    Read kernel cgroup memory.peak in MB.
    Returns (peak_mb, source_path) if successful, or None.
    cgroup v2: /sys/fs/cgroup/memory.peak
    cgroup v1: /sys/fs/cgroup/memory/memory.max_usage_in_bytes
    """
    paths = [
        "/sys/fs/cgroup/memory.peak",
        "/sys/fs/cgroup/memory/memory.max_usage_in_bytes",
    ]
    for p in paths:
        try:
            cmd = ["docker", "exec", container_name, "sh", "-c", f"cat {p} 2>/dev/null"]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5)
            out = res.stdout.strip()
            if res.returncode == 0 and out.isdigit():
                bytes_val = float(out)
                return round(bytes_val / (1024.0 * 1024.0), 1), p
        except Exception:
            pass
    return None


def check_oom_killed(container_name: str) -> bool:
    """Check if container was OOM killed using docker inspect."""
    try:
        res = subprocess.run(
            ["docker", "inspect", container_name, "--format", "{{.State.OOMKilled}}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
        return res.stdout.strip().lower() == "true"
    except Exception:
        return False


def trigger_stt_job(whisper_model: str) -> Tuple[str, bool, float, str]:
    """
    Execute a real STT transcription job inside conversx-worker on real audio clip.
    Fails loudly if /benchmark_audio is missing or contains no clips.
    """
    start = time.perf_counter()
    py_cmd = (
        "import sys, os, glob\n"
        "from faster_whisper import WhisperModel\n"
        "clips = glob.glob('/benchmark_audio/*.m4a') + glob.glob('/benchmark_audio/*.wav')\n"
        "if not clips:\n"
        "    print('ERROR: No benchmark clips found in /benchmark_audio', file=sys.stderr)\n"
        "    sys.exit(1)\n"
        f"model = WhisperModel('{whisper_model}', device='cpu', compute_type='int8', download_root='/models/whisper')\n"
        "segs, _ = model.transcribe(clips[0], beam_size=5, vad_filter=False, language='en')\n"
        "list(segs)\n"
    )
    cmd = ["docker", "exec", "conversx-worker", "python", "-c", py_cmd]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        elapsed = time.perf_counter() - start
        if res.returncode == 0:
            return "STT", True, elapsed, "ok"
        else:
            err = res.stderr.strip() or res.stdout.strip()
            return "STT", False, elapsed, f"exit {res.returncode}: {err[:200]}"
    except subprocess.TimeoutExpired:
        return "STT", False, 120.0, "Timeout expired (>120s)"
    except Exception as e:
        return "STT", False, time.perf_counter() - start, str(e)


def trigger_llm_job(llm_model: str) -> Tuple[str, bool, float, str]:
    """Execute an Ollama LLM prompt via conversx-api."""
    start = time.perf_counter()
    py_cmd = (
        "import urllib.request, json\n"
        "prompt = 'Write a 150-word conversation between two friends discussing weekend plans.'\n"
        f"payload = json.dumps({{'model': '{llm_model}', 'prompt': prompt, 'stream': False}}).encode('utf-8')\n"
        "req = urllib.request.Request('http://ollama:11434/api/generate', data=payload, headers={'Content-Type': 'application/json'})\n"
        "with urllib.request.urlopen(req, timeout=90) as resp:\n"
        "    data = json.loads(resp.read().decode('utf-8'))\n"
        "    assert 'response' in data and len(data['response']) > 10\n"
    )
    cmd = ["docker", "exec", "conversx-api", "python", "-c", py_cmd]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90)
        elapsed = time.perf_counter() - start
        if res.returncode == 0:
            return "LLM", True, elapsed, "ok"
        else:
            err = res.stderr.strip() or res.stdout.strip()
            return "LLM", False, elapsed, f"exit {res.returncode}: {err[:200]}"
    except subprocess.TimeoutExpired:
        return "LLM", False, 90.0, "Timeout expired (>90s)"
    except Exception as e:
        return "LLM", False, time.perf_counter() - start, str(e)


def trigger_moderation_job() -> Tuple[str, bool, float, str]:
    """Execute rule-based communication analysis inside conversx-api."""
    start = time.perf_counter()
    py_cmd = (
        "from app.services.moderation import get_moderation_service\n"
        "mod = get_moderation_service()\n"
        "r1 = mod.analyze_communication('This is a clean test message.')\n"
        "r2 = mod.analyze_communication('You are useless and incompetent!')\n"
        "assert r1.status == 'safe' and r2.status in ['warning', 'harmful']\n"
    )
    cmd = ["docker", "exec", "conversx-api", "python", "-c", py_cmd]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        elapsed = time.perf_counter() - start
        if res.returncode == 0:
            return "Moderation (Rule-based engine)", True, elapsed, "ok"
        else:
            err = res.stderr.strip() or res.stdout.strip()
            return "Moderation (Rule-based engine)", False, elapsed, f"exit {res.returncode}: {err[:200]}"
    except subprocess.TimeoutExpired:
        return "Moderation (Rule-based engine)", False, 60.0, "Timeout expired (>60s)"
    except Exception as e:
        return "Moderation (Rule-based engine)", False, time.perf_counter() - start, str(e)


def run_concurrent_stress_test(
    whisper_model: str = "small",
    llm_model: str = "qwen2.5:3b",
    sample_interval: float = 0.5,
) -> Tuple[Dict[str, float], Dict[str, str], List[Dict[str, float]], List[Tuple[str, bool, float, str]], Dict[str, bool]]:
    """
    Run STT, LLM, and Moderation concurrently while streaming docker stats.
    Returns (peak_container_map, peak_sources_map, streamed_samples, workload_results, oom_status_map).
    """
    print("\n[bench_ram] Initiating concurrent stress test (STT + LLM + Rule-based Moderation)...", flush=True)

    samples: List[Dict[str, float]] = []
    stop_sampling = False

    def sampler():
        while not stop_sampling:
            s = sample_container_ram()
            if s:
                samples.append(s)
            time.sleep(sample_interval)

    workload_results: List[Tuple[str, bool, float, str]] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        sample_future = executor.submit(sampler)

        f_stt = executor.submit(trigger_stt_job, whisper_model)
        f_llm = executor.submit(trigger_llm_job, llm_model)
        f_mod = executor.submit(trigger_moderation_job)

        futures_map = {f_stt: "STT", f_llm: "LLM", f_mod: "Moderation (Rule-based engine)"}

        for f in concurrent.futures.as_completed(futures_map):
            task_name = futures_map[f]
            try:
                res = f.result()
                workload_results.append(res)
                _, ok, elapsed, detail = res
                status_str = "completed [OK]" if ok else f"FAILED/SKIPPED [FAIL] ({detail})"
                print(f"  -> {task_name} workload {status_str} in {elapsed:.1f}s", flush=True)
            except Exception as err:
                workload_results.append((task_name, False, 0.0, f"Exception: {err}"))
                print(f"  -> {task_name} workload FAILED/SKIPPED [FAIL] (Exception: {err})", flush=True)

        stop_sampling = True
        try:
            sample_future.result(timeout=2)
        except Exception:
            pass

    # Read kernel cgroup memory.peak for every container and identify memory source
    final_peaks: Dict[str, float] = {}
    peak_sources: Dict[str, str] = {}
    oom_status: Dict[str, bool] = {}

    for c in CONVERSX_CONTAINERS:
        oom = check_oom_killed(c)
        oom_status[c] = oom
        cgroup_res = get_cgroup_peak_ram(c)
        if cgroup_res is not None:
            val, path = cgroup_res
            final_peaks[c] = val
            peak_sources[c] = f"cgroup ({path})"
        else:
            c_samples = [s.get(c, 0.0) for s in samples if c in s]
            final_peaks[c] = max(c_samples) if c_samples else 0.0
            peak_sources[c] = "docker stats stream fallback"

    return final_peaks, peak_sources, samples, workload_results, oom_status


def print_comparison_table(
    idle_map: Dict[str, float],
    peak_map: Dict[str, float],
    peak_source_map: Dict[str, str],
    oom_map: Dict[str, bool],
    all_succeeded: bool,
    workloads: List[Tuple[str, bool, float, str]],
) -> Tuple[bool, str]:
    idle_total = sum(idle_map.get(c, 0.0) for c in CONVERSX_CONTAINERS)
    peak_total = sum(peak_map.get(c, 0.0) for c in CONVERSX_CONTAINERS)
    any_oom = any(oom_map.values())

    print("\n" + "=" * 90)
    print("ConversX Gate A - Full-Stack RAM Measurement (Peak Memory Source & Idle)")
    print("=" * 90)
    print(f"{'Container':<24} {'Idle RAM':>10} {'Peak RAM':>12} {'Memory Source':>30} {'OOMKilled':>10}")
    print("-" * 90)

    for name in CONVERSX_CONTAINERS:
        idle_val = idle_map.get(name, -1)
        peak_val = peak_map.get(name, -1)
        source_str = peak_source_map.get(name, "unknown")
        oom_val = oom_map.get(name, False)
        idle_str = f"{idle_val:.0f} MB" if idle_val >= 0 else "n/a"
        peak_str = f"{peak_val:.0f} MB" if peak_val >= 0 else "n/a"
        oom_str = "YES (OOM!)" if oom_val else "false"
        print(f"  {name:<22} {idle_str:>10} {peak_str:>12} {source_str:>30} {oom_str:>10}")

    print("-" * 90)
    idle_total_str = f"{idle_total:.0f} MB ({idle_total/1024:.2f} GB)"
    peak_total_str = f"{peak_total:.0f} MB ({peak_total/1024:.2f} GB)"
    print(f"  {'TOTAL':<22} {idle_total_str:>10} {peak_total_str:>12} {'Summed peaks (Upper Bound)':>30} {'-':>10}")
    print("-" * 90)
    gate_limit_str = f"{GATE_LIMIT_MB:.0f} MB ({GATE_LIMIT_MB/1024:.1f} GB)"
    print(f"  {'GATE A LIMIT':<22} {'-':>10} {gate_limit_str:>12} {'Threshold: <= 8.5 GB':>30} {'-':>10}")

    # Gate logic:
    # 1. If any workload failed or was skipped -> INVALID (never PASS)
    # 2. If any container was OOMKilled -> FAIL
    # 3. If peak > limit -> FAIL
    # 4. Otherwise -> PASS
    if not all_succeeded:
        gate_pass = False
        failed_names = [name for name, ok, _, _ in workloads if not ok]
        verdict = f"INVALID (Workload failed/skipped: {', '.join(failed_names)})"
    elif any_oom:
        gate_pass = False
        oom_names = [c for c, is_oom in oom_map.items() if is_oom]
        verdict = f"FAIL (OOMKilled: {', '.join(oom_names)})"
    elif peak_total > GATE_LIMIT_MB:
        gate_pass = False
        verdict = f"FAIL (Peak RAM {peak_total:.0f}MB > limit {GATE_LIMIT_MB:.0f}MB)"
    else:
        gate_pass = True
        verdict = "PASS"

    print(f"  {'GATE A VERDICT':<22} {'-':>10} {verdict:>44} {'-':>10}")
    print("=" * 90)
    print("  * NOTICE: Summed peaks are an upper bound. Independent container peaks did not")
    print("    necessarily occur at the exact same microsecond during execution.")
    print("=" * 90)
    return gate_pass, verdict


def main() -> None:
    parser = argparse.ArgumentParser(description="Gate A Full-Stack RAM Benchmark")
    parser.add_argument("--llm-model", default="qwen2.5:3b", help="Candidate LLM model")
    parser.add_argument("--whisper-model", default="small", help="Candidate Whisper model")
    parser.add_argument("--idle-only", action="store_true", help="Record idle RAM only")
    args = parser.parse_args()

    print("[bench_ram] Capturing Idle baseline RAM across all containers...", flush=True)
    idle_ram = sample_container_ram()
    idle_total_mb = sum(idle_ram.values())

    if args.idle_only:
        print("\n[bench_ram] Idle snapshot:")
        for k, v in idle_ram.items():
            print(f"  {k:<28}: {v:.1f} MB")
        print(f"Total Idle: {idle_total_mb:.1f} MB ({idle_total_mb/1024:.2f} GB)")
        sys.exit(0)

    # Measure Peak RAM under simultaneous STT + LLM + Moderation
    peak_ram, peak_sources, all_samples, workloads, oom_map = run_concurrent_stress_test(
        whisper_model=args.whisper_model, llm_model=args.llm_model
    )
    peak_total_mb = sum(peak_ram.values())
    all_succeeded = all(ok for _, ok, _, _ in workloads) and len(workloads) == 3

    gate_pass, verdict = print_comparison_table(
        idle_ram, peak_ram, peak_sources, oom_map, all_succeeded, workloads
    )

    result_entry = {
        "benchmark": "full_stack_ram",
        "gate_criterion": "Peak RAM <= 8.5 GB with all models loaded & used together",
        "moderation_model": "Rule-based Firebase Engine",
        "workloads": [
            {"task": t, "success": ok, "elapsed_s": round(el, 2), "detail": det}
            for t, ok, el, det in workloads
        ],
        "all_workloads_succeeded": all_succeeded,
        "oom_killed_status": oom_map,
        "any_container_oom_killed": any(oom_map.values()),
        "idle_ram": {
            "total_mb": round(idle_total_mb, 1),
            "total_gb": round(idle_total_mb / 1024.0, 2),
            "containers": idle_ram,
        },
        "peak_ram": {
            "total_mb": round(peak_total_mb, 1),
            "total_gb": round(peak_total_mb / 1024.0, 2),
            "containers": peak_ram,
            "sources": peak_sources,
            "note": "Summed container peaks represent an upper bound (isolated container peaks did not necessarily occur concurrently).",
        },
        "gate_limit_mb": GATE_LIMIT_MB,
        "verdict": verdict,
        "gate_a_pass": gate_pass,
    }

    # Write results to benchmark_results/ram_results.jsonl
    results_dir = Path("/benchmark_results")
    if not results_dir.exists():
        results_dir = Path("benchmark_results")
    results_dir.mkdir(parents=True, exist_ok=True)

    with open(results_dir / "ram_results.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(result_entry) + "\n")

    sys.exit(0 if gate_pass else 1)


if __name__ == "__main__":
    main()
