#!/usr/bin/env bash
# =============================================================================
# scripts/run_benchmarks.sh
# Gate A benchmark runner — ConversX local-first mode (§18.2)
#
# Prerequisites:
#   1. Docker Desktop installed and running
#   2. WSL2 configured with infra/wslconfig.example (2 CPUs, 9 GB)
#      → copy to C:\Users\<you>\.wslconfig, then: wsl --shutdown
#   3. .env file created from .env.example with at least:
#      POSTGRES_PASSWORD, APP_SECRET_KEY, JWT_SECRET_KEY
#
# What this script does:
#   1. Builds the backend image locally (tagged :local)
#   2. Starts postgres + redis (required for API health)
#   3. Starts the API — verifies /healthz
#   4. Runs STT benchmark (faster-whisper base and small, int8)
#   5. Starts Ollama, pulls candidate LLM models, runs LLM benchmark
#   6. Measures full-stack RAM with all services up
#   7. Prints a Gate A summary
#   8. Writes all results to benchmark_results/ dir
#
# CPU-only — no GPU flags. RTX 3050 results are a separate non-gating run.
#
# Usage (from repo root, in WSL2 or Linux):
#   bash scripts/run_benchmarks.sh
#   bash scripts/run_benchmarks.sh --skip-stt      # skip if already done
#   bash scripts/run_benchmarks.sh --skip-llm      # skip if already done
#   bash scripts/run_benchmarks.sh --llm-model qwen2.5:1.5b  # override model
# =============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESULTS_DIR="$REPO_ROOT/benchmark_results"
COMPOSE_FILE="$REPO_ROOT/infra/docker-compose.yml"
ENV_FILE="$REPO_ROOT/.env"

# Defaults
SKIP_STT=false
SKIP_LLM=false
LLM_MODELS=("qwen2.5:3b" "qwen2.5:1.5b")  # benchmark both; choose best

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

header() { echo; echo "════════════════════════════════════════════════════"; echo "  $1"; echo "════════════════════════════════════════════════════"; }
log() { echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$LOG"; }

header "ConversX Gate A Benchmark"
log "Repo: $REPO_ROOT"
log "Results: $RESULTS_DIR"
log "Log: $LOG"

# ── Prerequisite checks ─────────────────────────────────────────────────────
log "Checking prerequisites..."
command -v docker >/dev/null || { log "ERROR: docker not found. Install Docker Desktop."; exit 1; }
docker info >/dev/null 2>&1 || { log "ERROR: Docker daemon not running. Start Docker Desktop."; exit 1; }
[ -f "$ENV_FILE" ] || { log "ERROR: .env not found. Copy .env.example to .env and fill in values."; exit 1; }

# Record WSL2 / host RAM
log "Host memory:"
free -h 2>/dev/null || sysctl hw.memsize 2>/dev/null || echo "  (cannot determine)"
log "CPU info:"
nproc 2>/dev/null && grep "model name" /proc/cpuinfo 2>/dev/null | head -1 || true

# ── Build backend image ──────────────────────────────────────────────────────
header "Step 1 — Build backend image (CPU-only, :local tag)"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" \
  build api 2>&1 | tee -a "$LOG"
log "Image size:"
docker image ls conversx/backend:local --format "{{.Repository}}:{{.Tag}}  {{.Size}}" 2>/dev/null || \
  docker image ls --filter "label=com.docker.compose.service=api" --format "{{.Size}}" | head -1

# ── Start core services ──────────────────────────────────────────────────────
header "Step 2 — Start postgres + redis + API"
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
    docker compose -f "$COMPOSE_FILE" logs api | tail -30
    exit 1
  fi
  sleep 2
done

# ── STT benchmark ────────────────────────────────────────────────────────────
if [ "$SKIP_STT" = false ]; then
  header "Step 3 — STT benchmark (faster-whisper)"
  log "Note: First run downloads model weights from HuggingFace (~75 MB base, ~245 MB small)"
  log "At 25 Mbps: base ~30s, small ~80s download time"

  for MODEL in base small; do
    log "Benchmarking Whisper $MODEL int8..."
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" \
      run --rm \
      --cpus 2 \
      --memory 2g \
      -v "$RESULTS_DIR:/benchmark_results" \
      worker python /app/scripts/bench_stt.py \
        --model "$MODEL" --compute_type int8 \
      2>&1 | tee -a "$LOG"
  done
else
  log "STT benchmark skipped (--skip-stt)"
fi

# ── LLM benchmark ────────────────────────────────────────────────────────────
if [ "$SKIP_LLM" = false ]; then
  header "Step 4 — LLM benchmark (Ollama, CPU-only)"
  log "Starting Ollama container..."
  docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" \
    up -d ollama 2>&1 | tee -a "$LOG"

  log "Waiting for Ollama API..."
  for i in $(seq 1 30); do
    if curl -fsS http://127.0.0.1:11434/api/tags > /dev/null 2>&1; then
      log "Ollama healthy ✓"; break
    fi
    [ "$i" -eq 30 ] && { log "ERROR: Ollama did not start"; exit 1; }
    sleep 3
  done

  for MODEL in "${LLM_MODELS[@]}"; do
    log "Benchmarking LLM: $MODEL (downloading if needed — ~6-11 min at 25 Mbps)"
    docker run --rm \
      --network conversx_default \
      --cpus 2 \
      --memory 3g \
      -v "$RESULTS_DIR:/benchmark_results" \
      python:3.11-slim bash -c "
        pip install httpx -q
        python /scripts/bench_llm.py --model '$MODEL' --pull --runs 3
      " 2>&1 | tee -a "$LOG"
  done
else
  log "LLM benchmark skipped (--skip-llm)"
fi

# ── Full-stack RAM ────────────────────────────────────────────────────────────
header "Step 5 — Full-stack RAM (all containers up)"
log "Starting all remaining services..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" \
  up -d 2>&1 | tee -a "$LOG"

log "Waiting 30s for all containers to stabilise..."
sleep 30

log "Taking RAM snapshot..."
python3 "$REPO_ROOT/scripts/bench_ram.py" 2>&1 | tee -a "$LOG"

log "Watching RAM for 60s (catches post-startup growth)..."
python3 "$REPO_ROOT/scripts/bench_ram.py" --watch --interval 10 --duration 60 \
  2>&1 | tee -a "$LOG"

# ── Summary ──────────────────────────────────────────────────────────────────
header "Gate A Summary"
log "Results written to: $RESULTS_DIR"
log "Log: $LOG"
echo ""
echo "  Paste the contents of benchmark_results/ into docs/BENCHMARKS.md."
echo "  STT results:  $RESULTS_DIR/stt_results.jsonl"
echo "  LLM results:  $RESULTS_DIR/llm_results.jsonl"
echo "  RAM results:  $RESULTS_DIR/ram_results.jsonl"
echo ""
echo "  Review Gate A criteria:"
echo "    STT RTF ≤ 2.0 (30s clip ≤ 60s wall-clock)"
echo "    LLM ≥ 5 tokens/s (worst run)"
echo "    Full-stack RAM ≤ 8.5 GB"
echo ""
echo "  If any gate fails, see docs/DECISIONS.md for model step-down plan."
