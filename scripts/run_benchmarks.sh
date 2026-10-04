#!/usr/bin/env bash
# =============================================================================
# scripts/run_benchmarks.sh
# Gate A benchmark runner - ConversX local-first mode (§18.2)
#
# Prerequisites:
#   1. Docker Desktop installed and running
#   2. WSL2 configured with infra/wslconfig.example (2 CPUs, 10.5 GB)
#        copy to C:\Users\<you>\.wslconfig, then: wsl --shutdown
#   3. .env file created from .env.example with at least:
#      POSTGRES_PASSWORD, APP_SECRET_KEY, JWT_SECRET_KEY
#   4. benchmark_audio/ populated with real audio recordings:
#      - ~30 s clip
#      - ~60 s clip
#      - ~10 short clips containing natural filler words
#
# What this script does:
#   1. Runs pre-flight checks (CPU, memory, port 11434 check, audio folder)
#   2. Builds the backend image locally (tagged :local)
#   3. Starts postgres + redis + API, verifies /healthz
#   4. Runs STT benchmark (faster-whisper base and small, int8) with real audio
#   5. Starts Ollama (CPU-only), runs LLM benchmark with realistic role-play prompt
#   6. Measures full-stack idle and peak RAM under simultaneous STT+LLM+Moderation load
#   7. Prints Gate A summary and consolidated pass/fail report
#
# CPU-only - no GPU flags. RTX 3050 results are a separate non-gating run.
#
# Usage (from repo root, in WSL2 or Linux):
#   bash scripts/run_benchmarks.sh
#   bash scripts/run_benchmarks.sh --skip-stt      # skip if already done
#   bash scripts/run_benchmarks.sh --skip-llm      # skip if already done
#   bash scripts/run_benchmarks.sh --llm-model qwen2.5:1.5b  # override model
# =============================================================================
set -euo pipefail

export MSYS_NO_PATHCONV=1
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && (pwd -W 2>/dev/null || pwd))"
RESULTS_DIR="$REPO_ROOT/benchmark_results"
COMPOSE_FILE="$REPO_ROOT/infra/docker-compose.yml"
ENV_FILE="$REPO_ROOT/.env"
AUDIO_DIR="$REPO_ROOT/benchmark_audio"

# Defaults
SKIP_STT=false
SKIP_LLM=false
LLM_MODELS=("qwen2.5:3b" "qwen2.5:1.5b")  # benchmark both; choose best

# Track results per benchmark
declare -A BENCHMARK_STATUS
OVERALL_SUCCESS=true

# Parse flags
while [[ $# -gt 0 ]]; do
  case $1 in
    --skip-stt) SKIP_STT=true; shift ;;
    --skip-llm) SKIP_LLM=true; shift ;;
    --llm-model) LLM_MODELS=("$2"); shift 2 ;;
    *) echo "Unknown flag: $1"; exit 1 ;;
  esac
done

mkdir -p "$RESULTS_DIR"
LOG="$RESULTS_DIR/run_$(date -u +%Y%m%dT%H%M%SZ).log"

header() { echo; echo "================================================================================"; echo "  $1"; echo "================================================================================"; }
log() { echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$LOG"; }
err() { echo "[$(date -u +%H:%M:%S)] ❌ $*" | tee -a "$LOG"; }

header "ConversX Gate A Benchmark Setup"
log "Repo root : $REPO_ROOT"
log "Results   : $RESULTS_DIR"
log "Log file  : $LOG"

# ── Step 0: Pre-flight checks ──
header "Pre-flight checks"

log "Checking Docker availability..."
command -v docker >/dev/null || { log "ERROR: docker command not found. Install Docker Desktop."; exit 1; }
docker info >/dev/null 2>&1 || { log "ERROR: Docker daemon is not running. Start Docker Desktop."; exit 1; }

[ -f "$ENV_FILE" ] || { log "ERROR: .env not found. Copy .env.example to .env and configure secrets."; exit 1; }

# Docker daemon resources (authoritative check per .wslconfig, replacing nproc)
DOCKER_CPUS=$(docker info --format '{{.NCPU}}' 2>/dev/null || echo "unknown")
DOCKER_MEM_BYTES=$(docker info --format '{{.MemTotal}}' 2>/dev/null || echo 0)
if [ "$DOCKER_MEM_BYTES" -gt 0 ] 2>/dev/null; then
  DOCKER_MEM_GB=$(awk -v b="$DOCKER_MEM_BYTES" 'BEGIN { printf "%.2f GB", b / (1024*1024*1024) }')
else
  DOCKER_MEM_GB="unknown"
fi
log "Docker daemon resources (docker info):"
log "  CPUs   : $DOCKER_CPUS"
log "  Memory : $DOCKER_MEM_GB ($DOCKER_MEM_BYTES bytes)"

# Check if native Windows Ollama is running on port 11434
if curl -s -m 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1 || \
   (exec 3<>/dev/tcp/127.0.0.1/11434) 2>/dev/null; then
  exec 3<&- 2>/dev/null || true
  exec 3>&- 2>/dev/null || true
  echo "" | tee -a "$LOG"
  log "⚠️  WARNING: Port 11434 on 127.0.0.1 responded!"
  log "    Native Windows Ollama appears to be running on the host."
  log "    Please quit native Ollama (right-click taskbar icon -> Quit) to prevent resource or port contention."
  echo "" | tee -a "$LOG"
fi

# Check benchmark_audio folder if STT is not skipped
if [ "$SKIP_STT" = false ]; then
  mkdir -p "$AUDIO_DIR"
  AUDIO_COUNT=$(find "$AUDIO_DIR" -type f \( -name "*.wav" -o -name "*.mp3" -o -name "*.m4a" -o -name "*.ogg" -o -name "*.flac" \) 2>/dev/null | wc -l || echo 0)
  if [ "$AUDIO_COUNT" -eq 0 ]; then
    log "ERROR: benchmark_audio/ is empty or missing valid audio files!"
    log "Please place your real recordings in '$AUDIO_DIR' before running Gate A:"
    log "  - 30 s clip (e.g. speech_30s.m4a)"
    log "  - 60 s clip (e.g. speech_60s.m4a)"
    log "  - ~10 short clips containing natural filler words"
    exit 1
  else
    log "Audio recordings check: Found $AUDIO_COUNT audio file(s) in benchmark_audio/ ✓"
  fi
fi

# ── Step 1: Build backend image ──
header "Step 1 - Build backend image (CPU-only, :local tag)"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" \
  build api 2>&1 | tee -a "$LOG"
log "Image verified:"
docker image ls conversx/backend:local --format "{{.Repository}}:{{.Tag}}  {{.Size}}" 2>/dev/null || \
  docker image ls --filter "label=com.docker.compose.service=api" --format "{{.Size}}" | head -1

# ── Step 2: Start core services ──
header "Step 2 - Start postgres + redis + API"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" \
  up -d postgres redis api 2>&1 | tee -a "$LOG"

log "Waiting for API /healthz..."
for i in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8000/healthz > /dev/null 2>&1; then
    log "API healthy ✓"
    break
  fi
  if [ "$i" -eq 30 ]; then
    log "ERROR: API did not become healthy after 60s"
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs api | tail -30
    exit 1
  fi
  sleep 2
done

# ── Step 3: STT benchmark ──
if [ "$SKIP_STT" = false ]; then
  header "Step 3 - STT benchmark (faster-whisper)"
  log "Note: First run downloads model weights into named volume whisper_models"

  for MODEL in base small; do
    log "Benchmarking Whisper $MODEL int8 on real speech clips..."
    set +e
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" \
      run --rm \
      -v "$RESULTS_DIR:/benchmark_results" \
      -v "$REPO_ROOT/scripts:/scripts:ro" \
      -v "$AUDIO_DIR:/benchmark_audio:ro" \
      worker python /scripts/bench_stt.py \
        --model "$MODEL" --compute_type int8 --audio_dir /benchmark_audio \
      2>&1 | tee -a "$LOG"
    STT_CODE="${PIPESTATUS[0]}"
    set -e

    if [ "$STT_CODE" -eq 0 ]; then
      log "Whisper $MODEL benchmark PASSED (exit code 0)"
      BENCHMARK_STATUS["STT_$MODEL"]="PASS"
    else
      err "Whisper $MODEL benchmark FAILED (exit code $STT_CODE)"
      BENCHMARK_STATUS["STT_$MODEL"]="FAIL (exit $STT_CODE)"
      OVERALL_SUCCESS=false
    fi
  done
else
  log "STT benchmark skipped (--skip-stt)"
  BENCHMARK_STATUS["STT"]="SKIPPED"
fi

# ── Step 4: LLM benchmark ──
if [ "$SKIP_LLM" = false ]; then
  header "Step 4 - LLM benchmark (Ollama, CPU-only)"
  log "Starting Ollama container..."
  docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" \
    up -d ollama 2>&1 | tee -a "$LOG"

  log "Waiting for Ollama container ready via internal check..."
  for i in $(seq 1 30); do
    if docker exec conversx-ollama ollama list > /dev/null 2>&1; then
      log "Ollama healthy ✓"; break
    fi
    [ "$i" -eq 30 ] && { log "ERROR: Ollama did not start after 90s"; exit 1; }
    sleep 3
  done

  for MODEL in "${LLM_MODELS[@]}"; do
    log "Benchmarking LLM: $MODEL (pulling if not cached in ollama_models volume)..."
    set +e
    docker run --rm \
      --network conversx_default \
      --cpus 2 \
      --memory 3g \
      -v "$RESULTS_DIR:/benchmark_results" \
      -v "$REPO_ROOT/scripts:/scripts:ro" \
      python:3.11-slim bash -c "
        pip install httpx -q
        python /scripts/bench_llm.py --model '$MODEL' --url http://ollama:11434 --pull --runs 3
      " 2>&1 | tee -a "$LOG"
    LLM_CODE="${PIPESTATUS[0]}"
    set -e

    if [ "$LLM_CODE" -eq 0 ]; then
      log "LLM $MODEL benchmark PASSED (exit code 0)"
      BENCHMARK_STATUS["LLM_$MODEL"]="PASS"
    else
      err "LLM $MODEL benchmark FAILED (exit code $LLM_CODE)"
      BENCHMARK_STATUS["LLM_$MODEL"]="FAIL (exit $LLM_CODE)"
      OVERALL_SUCCESS=false
    fi
  done
else
  log "LLM benchmark skipped (--skip-llm)"
  BENCHMARK_STATUS["LLM"]="SKIPPED"
fi

# ── Step 5: Full-stack RAM benchmark ──
header "Step 5 - Full-stack RAM (Idle vs Peak under concurrent stress)"
log "Starting all remaining services (worker, prometheus, uptime-kuma)..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" \
  up -d 2>&1 | tee -a "$LOG"

log "Waiting 20s for all containers to stabilise..."
sleep 20

log "Executing full-stack RAM benchmark (captures Idle baseline + simultaneous STT/LLM/Moderation peak)..."
PYTHON_BIN=$(command -v python || command -v python3)
set +e
$PYTHON_BIN "$REPO_ROOT/scripts/bench_ram.py" --llm-model "${LLM_MODELS[0]}" --whisper-model small \
  2>&1 | tee -a "$LOG"
RAM_CODE="${PIPESTATUS[0]}"
set -e

if [ "$RAM_CODE" -eq 0 ]; then
  log "Full-stack RAM benchmark PASSED (exit code 0)"
  BENCHMARK_STATUS["RAM"]="PASS"
else
  err "Full-stack RAM benchmark FAILED (exit code $RAM_CODE)"
  BENCHMARK_STATUS["RAM"]="FAIL (exit $RAM_CODE)"
  OVERALL_SUCCESS=false
fi

# ── Summary ──
header "Gate A Summary & Status Overview"
log "Results written to: $RESULTS_DIR"
log "Log: $LOG"
echo ""
echo "================================================================================"
echo "  ConversX Gate A Status Table"
echo "================================================================================"
for K in "${!BENCHMARK_STATUS[@]}"; do
  printf "  %-30s : %s\n" "$K" "${BENCHMARK_STATUS[$K]}"
done
echo "================================================================================"
echo ""
echo "  Review Gate A criteria:"
echo "    1. STT 30s clip RTF <= 2.0 (wall-clock <= 60s, worst run of 3)"
echo "    2. LLM throughput >= 5.0 tokens/s (worst run on realistic prompt)"
echo "    3. Full-stack Peak RAM <= 8.5 GB (all models loaded and used concurrently)"
echo ""
echo "  Results files:"
echo "    STT results:  $RESULTS_DIR/stt_results.jsonl"
echo "    LLM results:  $RESULTS_DIR/llm_results.jsonl"
echo "    RAM results:  $RESULTS_DIR/ram_results.jsonl"
echo "    Transcripts:  $RESULTS_DIR/transcripts/"
echo ""

if [ "$OVERALL_SUCCESS" = true ]; then
  log "Gate A Summary: All executed benchmark suites PASSED ✓"
  exit 0
else
  err "Gate A Summary: One or more benchmark suites FAILED ✗"
  exit 1
fi
