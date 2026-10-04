"""
scripts/bench_stt.py
====================
Gate A STT Benchmark for ConversX:
  1. Measures audio duration of all recordings in /benchmark_audio via ffprobe or PyAV.
  2. Dynamically assigns roles:
     - 30s role: closest measured duration to 30.0s
     - 60s role: closest measured duration to 60.0s
     - filler role: all remaining clips
  3. Reconciles filler_truth.csv against folder contents (matches, missing, typos).
  4. Runs prompt echo detection check on 3.0s silent audio.
  5. Runs warmup inference on 30s clip.
  6. Runs 3 timed steady-state runs per clip (30s and 60s). Gate uses the worst 30s run (RTF <= 2.0).
  7. Scores ALL clips (30s, 60s, and filler clips) against filler_truth.csv:
     - Core phonetic hesitation variants (um, uh, er, erm, hmm, mm) are always counted.
     - Conversational filler words ('like', 'actually', 'basically') count ONLY when listed
       in the truth file's per-clip words (supports optional 3rd CSV column: filename,count,filler_words).
     - Reports recall (min(matches, expected) / expected) and extra detected fillers separately.
  8. Records model configuration, beam_size, cpu_threads, vad_filter, language ("en"),
     peak_rss, and saves full transcripts to benchmark_results/transcripts/.
"""

import argparse
import csv
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional, Set, Tuple
import wave

# Ensure UTF-8 output encoding across environments
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import resource
except ImportError:
    resource = None  # Windows compatibility fallback

# Core phonetic filler regex (always counted)
PHONETIC_FILLER_REGEX = re.compile(
    r"\b(?:"
    r"u+m+|"           # um, umm, ummm...
    r"u+h+m*|"         # uh, uhh, uhm, uhmm...
    r"e+r+m*|"         # er, err, erm, ermm...
    r"e+r+|"           # er, err...
    r"h+m+|"           # hmm, hmmm...
    r"m{2,}"           # mm, mmm...
    r")\b",
    re.IGNORECASE,
)

# Conversational discourse filler candidates (ONLY counted when explicitly listed in 3rd CSV column)
DISCOURSE_FILLER_REGEX = re.compile(
    r"\b(?:"
    r"like|"           # like
    r"you\s+know|"     # you know
    r"basically|"      # basically
    r"actually|"       # actually
    r"sort\s+of"       # sort of
    r")\b",
    re.IGNORECASE,
)

DISCOURSE_WORDS = {"like", "actually", "basically", "you know", "sort of"}


def get_rss_kb() -> int:
    """Return current process RSS in KB (peak RSS on Linux)."""
    if resource is not None:
        try:
            return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        except Exception:
            return 0
    return 0


def get_audio_duration(file_path: Path) -> float:
    """
    Extract audio duration in seconds using ffprobe or PyAV (av).
    FAILS LOUDLY by raising RuntimeError if duration cannot be determined.
    """
    # 1. Attempt ffprobe (standard CLI tool in worker image)
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(file_path),
        ]
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
        val = float(res.stdout.strip())
        if val > 0.0:
            return val
    except Exception:
        pass

    # 2. Attempt PyAV (built-in dependency of faster-whisper)
    try:
        import av
        with av.open(str(file_path)) as container:
            if container.duration is not None:
                val = float(container.duration) / 1_000_000.0  # AV_TIME_BASE is 1,000,000 (microseconds)
                if val > 0.0:
                    return val
            for stream in container.streams.audio:
                if stream.duration is not None and stream.time_base is not None:
                    val = float(stream.duration * stream.time_base)
                    if val > 0.0:
                        return val
    except Exception:
        pass

    # 3. Attempt wave for uncompressed WAV
    if file_path.suffix.lower() == ".wav":
        try:
            with wave.open(str(file_path), "rb") as wf:
                val = wf.getnframes() / float(wf.getframerate())
                if val > 0.0:
                    return val
        except Exception:
            pass

    # Fail loudly: no silent fallback or default to 30.0 / 60.0
    raise RuntimeError(
        f"FAILED TO MEASURE DURATION for '{file_path.name}'. "
        f"Neither ffprobe nor PyAV could decode duration for this audio file. "
        f"Please ensure ffprobe is installed or the audio container is valid."
    )


def find_benchmark_clips(
    audio_dir: Path,
) -> Tuple[Tuple[Path, float], Tuple[Path, float], List[Tuple[Path, float]], List[Path]]:
    """
    Measure audio duration for every audio clip and assign roles:
      - 30s role: closest measured duration to 30.0s
      - 60s role: closest measured duration to 60.0s
      - filler role: all remaining clips
    FAILS LOUDLY if any clip's duration cannot be measured.
    Returns (clip_30s_entry, clip_60s_entry, filler_entries, all_audio_files).
    """
    all_files = sorted([
        f for f in audio_dir.iterdir()
        if f.is_file() and f.suffix.lower() in (".wav", ".mp3", ".m4a", ".ogg", ".flac")
    ])
    if not all_files:
        raise FileNotFoundError(
            f"No audio files (.wav, .mp3, .m4a, .ogg, .flac) found in '{audio_dir}'. "
            f"Please place benchmark recordings into this folder."
        )

    file_durations: List[Tuple[Path, float]] = []
    for f in all_files:
        dur = get_audio_duration(f)  # Will raise RuntimeError if undetectable
        file_durations.append((f, dur))

    # Pick clip whose measured duration is closest to 30.0s
    clip_30s_entry = min(file_durations, key=lambda x: abs(x[1] - 30.0))

    # Pick clip whose measured duration is closest to 60.0s from remaining files
    candidates_60 = [x for x in file_durations if x[0] != clip_30s_entry[0]]
    if candidates_60:
        clip_60s_entry = min(candidates_60, key=lambda x: abs(x[1] - 60.0))
    else:
        clip_60s_entry = clip_30s_entry

    assigned_files = {clip_30s_entry[0], clip_60s_entry[0]}
    filler_entries = [x for x in file_durations if x[0] not in assigned_files]

    return clip_30s_entry, clip_60s_entry, filler_entries, all_files


def print_role_assignment(
    clip_30s: Tuple[Path, float],
    clip_60s: Tuple[Path, float],
    filler_clips: List[Tuple[Path, float]],
) -> None:
    """Print a formatted breakdown showing each clip's measured duration, filename, and assigned role."""
    print("\n" + "=" * 74)
    print("ConversX Benchmark Audio - Measured Durations & Assigned Roles")
    print("=" * 74)
    print(f"{'Role':<10} {'Filename':<36} {'Measured Duration':>24}")
    print("-" * 74)
    print(f"{'30s':<10} {clip_30s[0].name:<36} {clip_30s[1]:>22.2f} s")
    print(f"{'60s':<10} {clip_60s[0].name:<36} {clip_60s[1]:>22.2f} s")
    for fc in filler_clips:
        print(f"{'filler':<10} {fc[0].name:<36} {fc[1]:>22.2f} s")
    print("-" * 74)
    unique_count = len({clip_30s[0], clip_60s[0]}.union({fc[0] for fc in filler_clips}))
    total_duration = clip_30s[1] + (clip_60s[1] if clip_30s[0] != clip_60s[0] else 0.0) + sum(x[1] for x in filler_clips)
    print(f"Total: {unique_count} audio clip(s), {total_duration:.2f} s total audio")
    print("=" * 74)


def load_and_reconcile_filler_truth(
    audio_dir: Path, audio_files: List[Path]
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """
    Load filler_truth.csv and reconcile entries with actual audio files in the folder.
    Supports optional 3rd column: filename, filler_count[, filler_words]
    Reports:
      - Exact matches
      - Files in folder missing from CSV
      - Entries in CSV missing from folder
      - Suggested matches for apparent typos
    """
    candidate_paths = [
        audio_dir / "filler_truth.csv",
        Path("benchmark_audio") / "filler_truth.csv",
        Path("/benchmark_audio") / "filler_truth.csv",
    ]
    truth_file = next((p for p in candidate_paths if p.exists() and p.is_file()), None)

    reconciliation: Dict[str, Any] = {
        "csv_found": bool(truth_file),
        "csv_path": str(truth_file) if truth_file else None,
        "total_csv_entries": 0,
        "matched_files": [],
        "missing_from_csv": [],
        "missing_from_folder": [],
        "typo_suggestions": [],
    }

    if not truth_file:
        print("\n[bench_stt] Optional filler_truth.csv not found; skipping ground-truth reconciliation.")
        return {}, reconciliation

    truth_map: Dict[str, Dict[str, Any]] = {}
    with open(truth_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or len(row) < 2:
                continue
            fname = row[0].strip()
            count_str = row[1].strip()
            words_str = row[2].strip() if len(row) > 2 else ""

            # Skip header row if present
            if fname.lower() in ("filename", "file", "clip", "audio") and not count_str.isdigit():
                continue
            try:
                expected_count = int(count_str)
            except ValueError:
                continue

            # Parse optional allowed conversational filler words (e.g. 'you know', 'sort of', 'like')
            allowed_words: Set[str] = set()
            if words_str:
                # Split primarily on delimiters (comma, semicolon, pipe, slash) to preserve multi-word phrases like 'you know'
                raw_tokens = re.split(r"[,;|/]+", words_str.lower())
                for raw_tok in raw_tokens:
                    cleaned = " ".join(raw_tok.strip().split())
                    if cleaned:
                        allowed_words.add(cleaned)

            truth_map[fname] = {
                "expected": expected_count,
                "allowed_words": allowed_words,
            }

    reconciliation["total_csv_entries"] = len(truth_map)

    folder_names = {f.name for f in audio_files}
    csv_names = set(truth_map.keys())

    matched = folder_names.intersection(csv_names)
    missing_from_csv = sorted(list(folder_names - csv_names))
    missing_from_folder = sorted(list(csv_names - folder_names))

    reconciliation["matched_files"] = sorted(list(matched))
    reconciliation["missing_from_csv"] = missing_from_csv
    reconciliation["missing_from_folder"] = missing_from_folder

    # Detect obvious typos like . vs _ or filter vs filler
    suggestions = []
    for mf in missing_from_folder:
        mf_dot = mf.replace("_", ".")
        mf_filter = mf.replace("filler", "filter")
        for f in missing_from_csv:
            if (f == mf_dot or f == mf_filter or
                f.replace("filter", "filler") == mf or
                f.replace(".", "_") == mf):
                suggestions.append({
                    "csv_entry": mf,
                    "folder_file": f,
                    "reason": f"CSV entry '{mf}' matches folder file '{f}' (differing in delimiter or 'filter'/'filler')"
                })
    reconciliation["typo_suggestions"] = suggestions

    total_clips_folder = len(folder_names)
    exact_matches_count = len(matched)
    exact_ratio = f"{exact_matches_count}/{total_clips_folder}"

    print("\n" + "=" * 74)
    print("ConversX Ground-Truth Reconciliation (filler_truth.csv vs Folder)")
    print("=" * 74)
    print(f"CSV file path           : {truth_file}")
    print(f"Total entries in CSV    : {len(truth_map)}")
    print(f"Total clips in folder   : {total_clips_folder}")
    print(f"Exact filename matches  : {exact_matches_count} ({exact_ratio} exact matches)")

    if matched:
        print("\n[OK] Matched Entries:")
        for m in sorted(matched):
            info = truth_map[m]
            custom_note = f" (allowed discourse words: {sorted(info['allowed_words'])})" if info["allowed_words"] else ""
            print(f"    {m:<32} -> {info['expected']} expected filler(s){custom_note}")

    if missing_from_csv:
        print("\n[!] Audio files in folder MISSING from CSV:")
        for f in missing_from_csv:
            print(f"  * {f}")

    if missing_from_folder:
        print("\n[!] Entries in CSV MISSING from folder:")
        for e in missing_from_folder:
            print(f"  * {e} (expected: {truth_map[e]['expected']})")

    if suggestions:
        print("\n[i] Detected Potential Filename Discrepancies:")
        for s in suggestions:
            print(f"  * {s['reason']}")
    print("=" * 74)

    return truth_map, reconciliation


def count_fillers(transcript: str, allowed_discourse_words: Optional[Set[str]] = None) -> Dict[str, int]:
    """
    Extract normalized filler counts:
      - Core phonetic hesitations (um, uh, er, erm, hmm, mm) are ALWAYS counted.
      - Conversational fillers ('like', 'actually', 'basically', 'you know', 'sort of')
        are counted ONLY if explicitly listed in allowed_discourse_words (from 3rd CSV column).
      - Custom words in allowed_discourse_words are also counted if present.
    """
    allowed_discourse = allowed_discourse_words or set()
    counts: Dict[str, int] = {}

    # 1. Phonetic hesitations (always counted)
    phonetic_matches = PHONETIC_FILLER_REGEX.findall(transcript)
    for raw in phonetic_matches:
        token = raw.lower().strip()
        if token.startswith("u") and token.endswith("m"):
            key = "um"
        elif token.startswith("u") and "h" in token and "m" in token:
            key = "uhm"
        elif token.startswith("u") and "h" in token:
            key = "uh"
        elif token.startswith("e") and "r" in token and "m" in token:
            key = "erm"
        elif token.startswith("e") and "r" in token:
            key = "er"
        elif token.startswith("h") and "m" in token:
            key = "hmm"
        elif set(token) == {"m"} and len(token) >= 2:
            key = "mm"
        else:
            key = token
        counts[key] = counts.get(key, 0) + 1

    # 2. Conversational discourse fillers (count ONLY if listed in allowed_discourse)
    discourse_matches = DISCOURSE_FILLER_REGEX.findall(transcript)
    for raw in discourse_matches:
        token = raw.lower().strip()
        canonical_key = "you know" if ("you" in token and "know" in token) else ("sort of" if ("sort" in token and "of" in token) else token)
        # Check if explicitly authorized for this clip
        if canonical_key in allowed_discourse or token in allowed_discourse:
            counts[canonical_key] = counts.get(canonical_key, 0) + 1

    # 3. Custom filler words in allowed_discourse that are not covered by default regexes
    for custom_word in allowed_discourse:
        if custom_word not in DISCOURSE_WORDS and custom_word not in ("um", "uh", "er", "erm", "hmm", "mm"):
            custom_matches = re.findall(rf"\b{re.escape(custom_word)}\b", transcript, re.IGNORECASE)
            if custom_matches:
                counts[custom_word] = counts.get(custom_word, 0) + len(custom_matches)

    return counts


def transcribe_file(
    model,
    audio_path: Path,
    beam_size: int = 5,
    vad_filter: bool = False,
    language: str = "en",
    save_transcript_dir: Optional[Path] = None,
    run_label: str = "run",
    role: str = "",
) -> Tuple[float, str, List[Any], str]:
    """
    Transcribe single audio file, returning (infer_time_s, transcript, segments_list, language).
    Saves full transcript text and segment timestamps to save_transcript_dir if specified.
    """
    start = time.perf_counter()
    segments, info = model.transcribe(
        str(audio_path),
        word_timestamps=True,
        beam_size=beam_size,
        vad_filter=vad_filter,
        language=language,
        initial_prompt="um, uh, er, hmm, like, you know, basically, actually, sort of",
    )
    segments_list = list(segments)
    infer_time = time.perf_counter() - start
    transcript = " ".join(s.text.strip() for s in segments_list)

    if save_transcript_dir is not None:
        save_transcript_dir.mkdir(parents=True, exist_ok=True)
        stem = audio_path.stem
        out_filename = f"{role}_{stem}_{run_label}.txt" if role else f"{stem}_{run_label}.txt"
        out_path = save_transcript_dir / out_filename
        with open(out_path, "w", encoding="utf-8") as tf:
            tf.write(f"=== Audio: {audio_path.name} (Role: {role}, Run: {run_label}) ===\n")
            tf.write(f"Language: {language} | Infer Time: {infer_time:.3f} s\n")
            tf.write(f"Transcript: {transcript}\n\n")
            tf.write("--- Segments with Timestamps ---\n")
            for seg in segments_list:
                tf.write(f"[{seg.start:.2f}s -> {seg.end:.2f}s] {seg.text}\n")

    return infer_time, transcript, segments_list, getattr(info, "language", language)


def run_prompt_echo_check(model, language: str = "en") -> Dict[str, Any]:
    """
    Check if Whisper echoes the initial prompt on pure silence.
    Generates a 3.0s synthetic silent audio clip (16kHz PCM WAV) and inspects output.
    """
    print("\n[bench_stt] Running prompt echo detection test on 3.0s silent audio...", flush=True)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        sample_rate = 16000
        duration_s = 3.0
        num_frames = int(sample_rate * duration_s)
        with wave.open(str(tmp_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(b"\x00\x00" * num_frames)

        infer_time, echo_tx, _, _ = transcribe_file(
            model,
            tmp_path,
            beam_size=5,
            vad_filter=False,
            language=language,
        )
        echo_tx_clean = echo_tx.strip()
        echo_fillers = count_fillers(echo_tx_clean)
        total_echo_fillers = sum(echo_fillers.values())
        echo_detected = total_echo_fillers > 0 or len(echo_tx_clean) > 0

        if echo_detected:
            print(f"  [!] Prompt echo detected on silence: '{echo_tx_clean}' ({total_echo_fillers} filler words echoed)", flush=True)
        else:
            print("  [OK] Prompt echo check passed: 0 filler words echoed on silence.", flush=True)

        return {
            "silent_clip_duration_s": duration_s,
            "prompt_echo_detected": echo_detected,
            "echo_transcript": echo_tx_clean,
            "echo_fillers_detected": echo_fillers,
            "total_echo_fillers": total_echo_fillers,
        }
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Gate A STT benchmark (faster-whisper)")
    parser.add_argument("--model", default="small", choices=["tiny", "base", "small"])
    parser.add_argument("--compute_type", default="int8", choices=["int8", "float32"])
    parser.add_argument("--beam_size", type=int, default=5, help="Beam size for decoding")
    parser.add_argument("--cpu_threads", type=int, default=2, help="CPU threads limit")
    parser.add_argument("--audio_dir", default="/benchmark_audio",
                        help="Path to folder containing real speech recordings")
    parser.add_argument("--duration-only", action="store_true",
                        help="Perform duration checks and CSV reconciliation without loading model or transcribing")
    args = parser.parse_args()

    audio_dir = Path(args.audio_dir)
    # Fallback to local ./benchmark_audio if default path is missing
    if not audio_dir.exists() and Path("benchmark_audio").exists():
        audio_dir = Path("benchmark_audio")

    print(f"[bench_stt] Examining audio recordings in: {audio_dir}", flush=True)

    try:
        clip_30s_entry, clip_60s_entry, filler_entries, all_audio_files = find_benchmark_clips(audio_dir)
    except Exception as err:
        print(f"\n[bench_stt] ERROR: {err}", file=sys.stderr)
        sys.exit(1)

    clip_30s, dur_30s = clip_30s_entry
    clip_60s, dur_60s = clip_60s_entry

    # Print duration breakdown and assigned roles
    print_role_assignment(clip_30s_entry, clip_60s_entry, filler_entries)

    # Reconcile filler_truth.csv with folder contents
    filler_truth, reconciliation = load_and_reconcile_filler_truth(audio_dir, all_audio_files)

    if args.duration_only:
        print("\n[bench_stt] Duration-only check completed successfully. Model inference skipped.")
        sys.exit(0)

    # Locate transcripts directory
    results_base = Path("/benchmark_results")
    if not results_base.exists():
        results_base = Path("benchmark_results")
    transcripts_dir = results_base / "transcripts"
    try:
        transcripts_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"[bench_stt] Warning: could not create transcripts directory '{transcripts_dir}': {e}", file=sys.stderr)

    rss_before = get_rss_kb()

    # 1. Model Load
    print(f"\n[bench_stt] Loading faster-whisper model '{args.model}' ({args.compute_type}, {args.cpu_threads} threads)...", flush=True)
    from faster_whisper import WhisperModel

    load_start = time.perf_counter()
    model = WhisperModel(
        args.model,
        device="cpu",
        compute_type=args.compute_type,
        cpu_threads=args.cpu_threads,
        download_root="/models/whisper",
    )
    load_time_s = time.perf_counter() - load_start
    print(f"[bench_stt] Model loaded in {load_time_s:.2f}s", flush=True)

    # 2. Prompt Echo Check on pure silence
    echo_result = run_prompt_echo_check(model, language="en")

    # 3. Warm-up run on 30s clip (excluded from steady-state RTF)
    print(f"\n[bench_stt] Running warmup on {clip_30s.name} ({dur_30s:.2f}s)...", flush=True)
    warmup_start = time.perf_counter()
    _warmup_infer, _, _, _ = transcribe_file(
        model,
        clip_30s,
        beam_size=args.beam_size,
        vad_filter=False,
        language="en",
        save_transcript_dir=transcripts_dir,
        run_label="warmup",
        role="30s",
    )
    warmup_time_s = time.perf_counter() - warmup_start
    print(f"[bench_stt] Warmup completed in {warmup_time_s:.2f}s (inference: {_warmup_infer:.2f}s)", flush=True)

    # 4. Steady-state runs: 3 timed runs per clip (30s and 60s)
    print(f"\n[bench_stt] Running 3 steady-state runs on 30 s clip ({clip_30s.name}, measured: {dur_30s:.2f}s)...", flush=True)
    runs_30s: List[Dict[str, Any]] = []
    tx_30s_run1 = ""
    infer_30s_run1 = 0.0

    for run_i in range(1, 4):
        infer_i, tx_i, segs_i, lang_i = transcribe_file(
            model,
            clip_30s,
            beam_size=args.beam_size,
            vad_filter=False,
            language="en",
            save_transcript_dir=transcripts_dir,
            run_label=f"steady_run{run_i}",
            role="30s",
        )
        if run_i == 1:
            tx_30s_run1 = tx_i
            infer_30s_run1 = infer_i

        rtf_i = infer_i / dur_30s
        runs_30s.append({
            "run": run_i,
            "infer_time_s": round(infer_i, 3),
            "rtf": round(rtf_i, 4),
            "pass": rtf_i <= 2.0,
            "transcript_preview": tx_i[:80],
        })
        print(f"  -> Run {run_i}: infer={infer_i:.2f}s | RTF={rtf_i:.3f} ({'PASS [OK]' if rtf_i <= 2.0 else 'FAIL [FAIL]'})", flush=True)

    rtfs_30s = [r["rtf"] for r in runs_30s]
    median_rtf_30s = statistics.median(rtfs_30s)
    worst_rtf_30s = max(rtfs_30s)
    best_rtf_30s = min(rtfs_30s)
    gate_30s_pass = worst_rtf_30s <= 2.0  # Gate uses the WORST 30s run

    print(f"[bench_stt] 30 s clip summary: Worst RTF = {worst_rtf_30s:.3f}, Median RTF = {median_rtf_30s:.3f} "
          f"({'PASS [OK]' if gate_30s_pass else 'FAIL [FAIL]'} | Gate Limit <= 2.0 on worst run)")

    # 60 s clip
    print(f"\n[bench_stt] Running 3 steady-state runs on 60 s clip ({clip_60s.name}, measured: {dur_60s:.2f}s)...", flush=True)
    runs_60s: List[Dict[str, Any]] = []
    tx_60s_run1 = ""
    infer_60s_run1 = 0.0

    for run_i in range(1, 4):
        infer_i, tx_i, segs_i, lang_i = transcribe_file(
            model,
            clip_60s,
            beam_size=args.beam_size,
            vad_filter=False,
            language="en",
            save_transcript_dir=transcripts_dir,
            run_label=f"steady_run{run_i}",
            role="60s",
        )
        if run_i == 1:
            tx_60s_run1 = tx_i
            infer_60s_run1 = infer_i

        rtf_i = infer_i / dur_60s
        runs_60s.append({
            "run": run_i,
            "infer_time_s": round(infer_i, 3),
            "rtf": round(rtf_i, 4),
            "pass": rtf_i <= 2.0,
            "transcript_preview": tx_i[:80],
        })
        print(f"  -> Run {run_i}: infer={infer_i:.2f}s | RTF={rtf_i:.3f} ({'PASS [OK]' if rtf_i <= 2.0 else 'FAIL [FAIL]'})", flush=True)

    rtfs_60s = [r["rtf"] for r in runs_60s]
    median_rtf_60s = statistics.median(rtfs_60s)
    worst_rtf_60s = max(rtfs_60s)
    best_rtf_60s = min(rtfs_60s)
    gate_60s_pass = worst_rtf_60s <= 2.0

    print(f"[bench_stt] 60 s clip summary: Worst RTF = {worst_rtf_60s:.3f}, Median RTF = {median_rtf_60s:.3f}")

    # 5. Filler Evaluation (Scores 30s, 60s, and all filler clips against filler_truth.csv)
    filler_results: List[Dict[str, Any]] = []
    total_recalled_fillers = 0
    total_extra_fillers = 0
    total_expected_fillers = 0

    # Build unique ordered list of clips to score
    clips_to_score: List[Tuple[Path, str]] = []
    clips_to_score.append((clip_30s, "30s"))
    if clip_60s != clip_30s:
        clips_to_score.append((clip_60s, "60s"))
    for fc, _ in filler_entries:
        if fc not in (clip_30s, clip_60s):
            clips_to_score.append((fc, "filler"))

    print(f"\n[bench_stt] Evaluating filler words across all {len(clips_to_score)} clip(s) against ground truth...", flush=True)

    for clip_path, role in clips_to_score:
        if role == "30s" and runs_30s:
            fc_tx = tx_30s_run1
            fc_infer = infer_30s_run1
            fc_dur = dur_30s
        elif role == "60s" and runs_60s:
            fc_tx = tx_60s_run1
            fc_infer = infer_60s_run1
            fc_dur = dur_60s
        else:
            fc_dur = get_audio_duration(clip_path)
            fc_infer, fc_tx, _, _ = transcribe_file(
                model,
                clip_path,
                beam_size=args.beam_size,
                vad_filter=False,
                language="en",
                save_transcript_dir=transcripts_dir,
                run_label="filler_eval",
                role=role,
            )

        # Match ground truth (exact or normalized alias)
        matched_key = clip_path.name if clip_path.name in filler_truth else None
        if not matched_key:
            alt1 = clip_path.name.replace("filter", "filler")
            alt2 = clip_path.name.replace(".", "_")
            if alt1 in filler_truth:
                matched_key = alt1
            elif alt2 in filler_truth:
                matched_key = alt2

        truth_entry = filler_truth.get(matched_key) if matched_key else None
        truth_val = truth_entry["expected"] if truth_entry else None
        allowed_discourse = truth_entry["allowed_words"] if truth_entry else set()

        detected_counts = count_fillers(fc_tx, allowed_discourse_words=allowed_discourse)
        total_detected = sum(detected_counts.values())

        # Calculate recall: min(matches, expected) / expected
        if truth_val is not None and truth_val > 0:
            recalled = min(total_detected, truth_val)
            extra = max(0, total_detected - truth_val)
            recall_percent = round((recalled / truth_val) * 100.0, 1)
            total_recalled_fillers += recalled
            total_extra_fillers += extra
            total_expected_fillers += truth_val
        elif truth_val == 0:
            recalled = 0
            extra = total_detected
            recall_percent = 100.0 if total_detected == 0 else 0.0
            total_extra_fillers += extra
        else:
            recalled = total_detected
            extra = 0
            recall_percent = None

        entry: Dict[str, Any] = {
            "clip": clip_path.name,
            "role": role,
            "duration_s": round(fc_dur, 2),
            "infer_time_s": round(fc_infer, 2),
            "allowed_discourse_fillers": sorted(list(allowed_discourse)),
            "fillers_detected": detected_counts,
            "total_fillers_detected": total_detected,
            "truth_filler_expected": truth_val,
            "matched_csv_entry": matched_key,
            "recalled_count": recalled,
            "extra_detected_count": extra,
            "recall_percent": recall_percent,
            "transcript_snippet": fc_tx[:100],
        }

        if truth_val is not None:
            discourse_info = f" (allowed: {sorted(allowed_discourse)})" if allowed_discourse else ""
            print(f"  -> [{role}] {clip_path.name} (CSV: {matched_key}): detected {total_detected} "
                  f"(recall: {recalled}/{truth_val} [{recall_percent}%], extra: {extra}){discourse_info}", flush=True)
        else:
            print(f"  -> [{role}] {clip_path.name}: detected {total_detected} fillers {detected_counts}", flush=True)

        filler_results.append(entry)

    overall_recall = (
        round((total_recalled_fillers / total_expected_fillers) * 100.0, 1)
        if total_expected_fillers > 0 else None
    )

    rss_after = get_rss_kb()
    peak_rss_mb = round(rss_after / 1024.0, 1)

    # 6. Overall Output JSON
    output: Dict[str, Any] = {
        "benchmark": "stt",
        "model": args.model,
        "compute_type": args.compute_type,
        "beam_size": args.beam_size,
        "vad_filter": False,
        "cpu_threads": args.cpu_threads,
        "language": "en",
        "transcripts_directory": str(transcripts_dir),
        "clip_selection_method": "measured_duration_closest_match",
        "model_load_time_s": round(load_time_s, 3),
        "prompt_echo_check": echo_result,
        "warmup_time_s": round(warmup_time_s, 3),
        "steady_state": {
            "clip_30s": {
                "file": clip_30s.name,
                "audio_duration_s": round(dur_30s, 2),
                "runs": runs_30s,
                "best_rtf": round(best_rtf_30s, 4),
                "median_rtf": round(median_rtf_30s, 4),
                "worst_rtf": round(worst_rtf_30s, 4),
                "rtf_gate_pass": gate_30s_pass,
            },
            "clip_60s": {
                "file": clip_60s.name,
                "audio_duration_s": round(dur_60s, 2),
                "runs": runs_60s,
                "best_rtf": round(best_rtf_60s, 4),
                "median_rtf": round(median_rtf_60s, 4),
                "worst_rtf": round(worst_rtf_60s, 4),
                "rtf_gate_pass": gate_60s_pass,
            },
        },
        "filler_evaluation": {
            "truth_file_loaded": bool(filler_truth),
            "clips_evaluated": len(filler_results),
            "total_fillers_expected": total_expected_fillers,
            "total_fillers_recalled": total_recalled_fillers,
            "total_extra_detected": total_extra_fillers,
            "overall_recall_percent": overall_recall,
            "clips": filler_results,
        },
        "reconciliation": reconciliation,
        "rss_before_kb": rss_before,
        "peak_rss_kb": rss_after,
        "peak_rss_mb": peak_rss_mb,
        "gate_a_target": "Worst 30s run RTF <= 2.0 (30s clip <= 60s wall-clock)",
        "gate_a_pass": gate_30s_pass,
    }

    print("\n=== RESULT JSON ===")
    print(json.dumps(output, indent=2))

    with open(results_base / "stt_results.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(output) + "\n")

    sys.exit(0 if gate_30s_pass else 1)


if __name__ == "__main__":
    main()
