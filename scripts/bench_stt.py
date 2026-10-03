#!/usr/bin/env python3
"""
scripts/bench_stt.py
Gate A benchmark — faster-whisper STT.

Measures:
  - Wall-clock time for 30 s and 60 s audio clips
  - Real-Time Factor (RTF = wall_clock / audio_duration)
  - Peak RSS memory during inference

Run inside the benchmark Docker container (see scripts/run_benchmarks.sh).
CPU-only, limited to 2 CPUs and memory as set by Docker flags.

Usage:
    python scripts/bench_stt.py --model small --compute_type int8
    python scripts/bench_stt.py --model base  --compute_type int8

Outputs a JSON result to stdout and appends a line to benchmark_results.jsonl.
"""
from __future__ import annotations

import argparse
import json
import os
import resource
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def generate_test_audio(duration_seconds: int, output_path: str) -> None:
    """Generate a sine-wave audio clip using ffmpeg (no external recording needed)."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"sine=frequency=440:duration={duration_seconds}",
        "-ar", "16000",   # Whisper expects 16 kHz
        "-ac", "1",        # mono
        "-acodec", "pcm_s16le",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ffmpeg error: {result.stderr}", file=sys.stderr)
        sys.exit(1)


def get_rss_kb() -> int:
    """Return current process RSS in KB."""
    try:
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except Exception:
        # Fallback: read /proc/self/status on Linux
        try:
            with open("/proc/self/status") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        return int(line.split()[1])
        except Exception:
            return -1
    return -1


def bench_model(model_name: str, compute_type: str, audio_path: str, audio_duration: float) -> dict:
    """Run faster-whisper on audio_path and return timing + memory stats."""
    from faster_whisper import WhisperModel

    rss_before = get_rss_kb()

    load_start = time.perf_counter()
    model = WhisperModel(
        model_name,
        device="cpu",
        compute_type=compute_type,
        download_root=os.environ.get("WHISPER_MODEL_DIR", "/models/whisper"),
        num_workers=1,
        cpu_threads=2,   # match 2-CPU gate limit
    )
    load_time = time.perf_counter() - load_start

    infer_start = time.perf_counter()
    segments, info = model.transcribe(
        audio_path,
        word_timestamps=True,
        initial_prompt="um, uh, er, hmm, like, you know, basically, actually, sort of",
    )
    # Consume the generator (lazy evaluation)
    segments_list = list(segments)
    infer_time = time.perf_counter() - infer_start

    rss_after = get_rss_kb()

    rtf = infer_time / audio_duration
    transcript = " ".join(s.text.strip() for s in segments_list)

    return {
        "model": model_name,
        "compute_type": compute_type,
        "audio_duration_s": audio_duration,
        "load_time_s": round(load_time, 3),
        "infer_time_s": round(infer_time, 3),
        "rtf": round(rtf, 4),
        "rtf_gate_pass": rtf <= 2.0,
        "rss_before_kb": rss_before,
        "rss_after_kb": rss_after,
        "rss_delta_mb": round((rss_after - rss_before) / 1024, 1),
        "detected_language": info.language,
        "transcript_preview": transcript[:100],
        "num_segments": len(segments_list),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Gate A STT benchmark")
    parser.add_argument("--model", default="small", choices=["tiny", "base", "small"])
    parser.add_argument("--compute_type", default="int8", choices=["int8", "float32"])
    args = parser.parse_args()

    results = []
    with tempfile.TemporaryDirectory() as tmpdir:
        for duration in [30, 60]:
            audio_path = os.path.join(tmpdir, f"test_{duration}s.wav")
            print(f"\n[bench_stt] Generating {duration}s sine-wave audio...", flush=True)
            generate_test_audio(duration, audio_path)

            print(f"[bench_stt] Benchmarking {args.model} ({args.compute_type}) on {duration}s clip...", flush=True)
            result = bench_model(args.model, args.compute_type, audio_path, float(duration))
            results.append(result)

            gate = "PASS ✓" if result["rtf_gate_pass"] else "FAIL ✗"
            print(
                f"[bench_stt] {duration}s | RTF={result['rtf']:.3f} ({gate}) | "
                f"infer={result['infer_time_s']:.1f}s | RSS delta={result['rss_delta_mb']:.0f} MB",
                flush=True,
            )

    # Write results
    output = {
        "benchmark": "stt",
        "model": args.model,
        "compute_type": args.compute_type,
        "results": results,
        "gate_a_pass": all(r["rtf_gate_pass"] for r in results),
    }
    print("\n=== RESULT JSON ===")
    print(json.dumps(output, indent=2))

    # Append to results file
    results_file = Path("/benchmark_results/stt_results.jsonl")
    results_file.parent.mkdir(parents=True, exist_ok=True)
    with open(results_file, "a") as f:
        f.write(json.dumps(output) + "\n")

    sys.exit(0 if output["gate_a_pass"] else 1)


if __name__ == "__main__":
    main()
