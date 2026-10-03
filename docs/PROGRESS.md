# ConversX Progress Log

> Updated after every milestone. This is the source of truth for project state.
> Last updated: 2026-10-03

---

## Current milestone: Week 1 — Benchmark Gate (LOCAL-FIRST MODE)

**Status:** 🟡 In progress — pre-coding review complete; waiting on owner inputs before coding begins.

---

## Completed

- [x] Read MASTER_PROMPT.md v4 including Section 18 (local-first addendum)
- [x] Created docs/FREE_TIER.md — verified all service limits with sources
- [x] Created docs/DECISIONS.md — 9 decisions recorded (D-001 through D-009)
- [x] Created docs/BENCHMARKS.md — machine specs recorded; Gate A targets documented
- [x] Identified machine: ASUS TUF Gaming F15, i5-11400H 6-core, 23.8 GB RAM, AMD64, RTX 3050 (non-gating)
- [x] Created infra/wslconfig.example (2 CPUs, 9 GB, 4 GB swap)
- [x] Created .gitignore, .env.example, .pre-commit-config.yaml
- [x] Created infra/docker-compose.yml (all services, resource limits, AOF Redis, audio tmp volume)
- [x] Created infra/prometheus/prometheus.yml
- [x] Created infra/cloudflared/config.yml (template, UNTESTED, conversx.example placeholder)
- [x] Created infra/scripts/deploy.sh, backup.sh, restore.sh, restore-drill.sh (all UNTESTED)
- [x] Created infra/systemd/ units (deploy timer+service, backup timer+service)
- [x] Created .github/workflows/backend.yml (CI: test+gitleaks+multi-arch image+Trivy, actions pinned)
- [x] Created backend/Dockerfile (multi-stage, python:3.11-slim, CPU-only torch, non-root user)
- [x] Created backend/requirements.txt and requirements-dev.txt (all pinned)
- [x] Created backend/app/main.py (FastAPI skeleton: /healthz, /metrics, /api/v1/hello, CORS, middleware)
- [x] Created backend/app/core/config.py (pydantic-settings, no hardcoded secrets)
- [x] Created backend/alembic.ini and backend/alembic/env.py (DATABASE_URL from env)
- [x] Created backend/tests/test_health.py (smoke tests: healthz, hello, CORS, metrics)
- [x] Created scripts/bench_stt.py (faster-whisper benchmark, RTF gate check)
- [x] Created scripts/bench_llm.py (Ollama LLM t/s benchmark, gate check)
- [x] Created scripts/bench_ram.py (full-stack docker stats, gate check)
- [x] Created scripts/run_benchmarks.sh (master runner: build, start, STT, LLM, RAM, summary)

---

## Next Step (owner action required)

1. **Install Docker Desktop** on Windows. Enable WSL2 backend.
2. **Apply .wslconfig**: copy `infra/wslconfig.example` to `C:\Users\anand\.wslconfig`, then `wsl --shutdown` and restart Docker Desktop.
3. **Create .env**: copy `.env.example` to `.env`, set at minimum `POSTGRES_PASSWORD`, `APP_SECRET_KEY`, `JWT_SECRET_KEY`.
4. **Run benchmarks** from WSL2:
   ```bash
   bash scripts/run_benchmarks.sh
   ```
5. **Paste results** into docs/BENCHMARKS.md. I will analyse them and fill in all UNVERIFIED fields.
6. Gate A decision: model sizes chosen, RAM budget confirmed, Week 2 unlocked.

---

## Week 1 Acceptance Criteria (from §13)

- [ ] BENCHMARKS.md with real numbers (all currently UNVERIFIED)
- [ ] Model sizes chosen (STT and LLM)
- [ ] FREE_TIER.md started with sources ✅
- [ ] "hello" API reachable via Cloudflare Tunnel **(deferred — no server yet, §18)**
- [ ] nmap shows no open inbound ports **(deferred — no server yet, §18)**
- [ ] Gate A: 30 s clip RTF ≤ 2.0, LLM ≥ 5 t/s, full stack ≤ 8.5 GB peak

**Note (§18):** In local-first mode, Tunnel/nmap tests are deferred to Gate B. Gate A = benchmarks pass on laptop with 2 CPU / 9 GB container limits.

---

## Known Issues / Blockers

1. **Docker not installed** on owner's Windows machine. Required to run local-first stack. Owner must install Docker Desktop.
2. **Oracle account blocked** on payment verification. No server available for Gate B yet. Using laptop for Gate A.
3. **GitHub repo visibility undecided** (D-002). Affects GHCR storage limit (D-001). Decision needed if Docker image > 500 MB compressed.
4. **Domain not registered** (D-008). Not needed for Week 1; needed before Gate B.

---

## Week 2 (Not started — Gate A must pass first)

**Milestone:** Auth and security baseline.  
**Do not begin until:** All Gate A criteria above are ✅.

---

## Test Results

*(Populated as tests are written and run)*

---

## Restore Drill Log

*(Populated from Week 11 onwards)*
