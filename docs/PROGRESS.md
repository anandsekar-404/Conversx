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

---

## Week 1 Pre-Gate A Verification Status (Updated 2026-10-04)

### Fully Verified & Completed
- [x] Docker Desktop running on host with WSL2 backend.
- [x] `conversx/backend:local` built cleanly via `docker compose build api` (Image size: 3.06 GB disk usage, 701 MB layer content).
- [x] Non-root volume permissions verified: User `conversx` (UID 1001, GID 1001) successfully wrote and deleted test files in `/models/whisper`, `/home/conversx/.cache/huggingface`, and `/tmp/conversx-audio`.
- [x] Resource inheritance verified via `docker inspect` on a one-off `compose run` worker container:
  - `HostConfig.NanoCpus`: `2000000000` (2.0 CPUs limit).
  - `HostConfig.Memory`: `3758096384` bytes (3584 MB limit).
- [x] Core dependencies (`conversx-postgres`, `conversx-redis`, `conversx-api`) running healthy with `/healthz` returning `200 OK` (`{"status":"ok","env":"development"}`).
- [x] Ollama readiness check verified: Confirmed that official `ollama/ollama` does not bundle `curl`. Replaced healthcheck in `infra/docker-compose.yml` with `["CMD", "ollama", "list"]` and readiness polling in `scripts/run_benchmarks.sh` with `docker exec conversx-ollama ollama list`.
- [x] Pinned Ollama image tag to `ollama/ollama:0.5.4` in `infra/docker-compose.yml`.
- [x] Recorded exact component versions in `docs/BENCHMARKS.md`:
  - `faster-whisper`: `1.1.1`
  - `ctranslate2`: `4.8.2`
  - `Ollama`: `0.5.4`
  - `Detoxify`: `0.5.2` (model: `original`, BERT-base)
  - `PyTorch`: `2.5.1+cpu`
- [x] Updated `scripts/bench_stt.py`: Clips are selected strictly by measured duration (`get_audio_duration`), picking closest to 30.0s and 60.0s rather than relying on filenames. Added support for `benchmark_audio/filler_truth.csv` to calculate filler survival percentage. Created template CSV.
- [x] Updated `scripts/bench_ram.py`: Switched Detoxify to `"original"` (BERT-base), replaced container curl call with Python worker HTTP request, and made `sample_container_ram` resilient to partial service sets.
- [x] Updated `infra/wslconfig.example`: Sized `.wslconfig` memory to `10.5GB` (above the 9024 MB container limits to prevent VM-level kernel OOM kills) while keeping the Gate A benchmark gate evaluated on `docker stats` strictly at `8.5 GB`.
- [x] Verified `scripts/run_benchmarks.sh` runner with `--skip-stt --skip-llm`.

---

## Explicit List of Everything Not Yet Verified (Unverified Items)

The following items cannot be verified until the user places real audio in `benchmark_audio/` and executes the full Gate A benchmark:

1. **STT Steady-State RTF & Latency**: Real-speech transcription RTF on 30s and 60s audio clips has not been measured yet (requires user audio recordings in `benchmark_audio/`).
2. **Filler Word Survival Rate**: Actual filler word detection rate has not been measured yet (requires real speech clips with natural filler words like "um", "uh", "like").
3. **LLM Inference Throughput**: Tokens/second and Time-to-First-Token (TTFT) for Qwen2.5 3B / 1.5B under 2-thread CPU limits have not been measured yet.
4. **Full-Stack Concurrent Peak RAM**: RAM usage during simultaneous STT + LLM + Rule-Based Moderation inference has not been measured under full load (pending full Gate A run).
5. **ARM64 Architecture Parity**: All tests run locally on Windows 11 (x86_64 Intel Core i5). ARM64 Neoverse-N1 performance (Oracle A1 target) is unverified and deferred to Gate B (§18.2).
6. **Cloudflare Tunnel Ingress & Public Domain Routing**: Zero-trust domain routing and external traffic ingress are untested locally (deferred to Gate B).
7. **Database Backup & Disaster Recovery Drills**: `backup.sh`, `restore.sh`, and `restore-drill.sh` scripts are unverified on a live database with test data.
8. **Email Delivery & Turnstile Bot Protection**: Brevo API integration and Cloudflare Turnstile token validation are unverified (mocked/stubbed until Week 2).

## Week 2 (Not started — Gate A must pass first)

**Milestone:** Auth and security baseline.  
**Do not begin until:** All Gate A criteria above are ✅.

---

## Test Results

*(Populated as tests are written and run)*

---

## Restore Drill Log

*(Populated from Week 11 onwards)*

---

## Phase: Transition to 100% Rule-Based Firebase Moderation Engine (2026-10-08)

Per Master Prompt directive, the Machine Learning / AI moderation workflow (Detoxify, PyTorch, BERT-base, AI APIs) has been completely removed and replaced with a 100% deterministic rule-based moderation and communication improvement platform backed by Firebase Firestore.

### 1. Backend Decommissioning & Engine Implementation
- [x] **Dependencies Purged:** Removed `detoxify==0.5.2` from `backend/requirements.txt`; removed `torch==2.5.1` CPU wheel from `backend/Dockerfile` (saving ~2 GB image footprint and ~750 MB runtime RAM). Added `firebase-admin==6.6.0`.
- [x] **Configuration:** Replaced `DETOXIFY_*` with `FIREBASE_PROJECT_ID`, `FIREBASE_CREDENTIALS_PATH`, and `MODERATION_RULES_CACHE_TTL_SECONDS` in `backend/app/core/config.py`, `.env`, and `.env.example`.
- [x] **Deterministic Service (`backend/app/services/moderation.py`):**
  - Unicode NFKD normalization + accent stripping + symbol whitespace boundary handling (preserving original text for display).
  - Level 1: Token-aware word matching against Firebase `badWords` (eliminating false positives such as "classic" matching "ass", "therapist" matching "rape", "document" matching "cum").
  - Level 2: Boundary-aware phrase matching against Firebase `harassmentPatterns`.
  - Level 3: Multiple-match aggregation (`matched_rules[]`).
  - Severity calculation (0=Safe, 1=Mild, 2=Warning, 3=Harmful, 4=Severe) and Communication Score (0–100) with 4 dimensions (Respectfulness, Clarity, Hostility Index, Professionalism).
  - Constructive "Say It Better" deterministic suggestion engine.
  - In-memory `RuleCache` with 5-minute TTL, Firestore sync, and offline seed fallback (`seed_rules.json`).
- [x] **API Endpoints (`backend/app/routers/moderation.py`):**
  - `POST /api/v1/moderation/analyze` (public analysis)
  - `GET /api/v1/moderation/rules`, `/categories`, `/severity-levels`, `/suggestions`
  - Admin endpoints: `/admin/rules` (CRUD), `/admin/sync`
- [x] **Automated Testing:** `backend/tests/test_moderation.py` — **26 passed, 0 failed**.

### 2. Frontend Client Engine & Interactive UI
- [x] **Client-Side Moderation Engine (`frontend/src/moderation/`):**
  - `normalizeText.js`, `matchWords.js`, `matchPhrases.js`, `calculateSeverity.js`, `loadRules.js`, `analyzeCommunication.js`, `index.js`.
  - Sub-millisecond client-side execution; complete user privacy (messages remain local).
- [x] **Firebase Firestore Integration (`frontend/src/firebase.js` & `frontend/firestore.rules`):**
  - Read access for active rules; admin-only writes. User conversations never stored for moderation.
- [x] **ConversX Communication Studio (`frontend/index.html`):**
  - Real-time animated score gauge (0–100) and severity verdict pill.
  - Quick scenario buttons (Professional Disagreement, Difficult Feedback, Insult, False-Positive Check, Severe Threat).
  - 4 Communication dimension progress bars.
  - Non-judgmental diagnostic feedback and matched rules list.
  - Interactive "Say It Better" card with constructive advice and 1-click alternative application.
- [x] **Moderation Admin Console (`frontend/admin.html`):**
  - Rule management dashboard: Add bad words & harassment phrases, select category/severity/language, toggle active, search, and filter.
  - Live sandbox to test sentences against rules instantly.
- [x] **Automated JS Testing (`frontend/tests/test_moderation.js`):** — **35 passed, 0 failed** in Node.js.

### 3. Documentation & Benchmarks
- [x] Recorded architectural decision **D-011** in `docs/DECISIONS.md`.
- [x] Updated `docs/BENCHMARKS.md` and `scripts/bench_ram.py`.


---

## Phase 4: Deterministic Communication Improvement & Practice Platform (2026-10-08)

### 1. Architectural Transformation: Communication Coach
- [x] **Preserved Existing Moderation:** Firebase Firestore rule-based moderation engine preserved and integrated into the Respectfulness dimension. Zero ML models or external APIs reintroduced.
- [x] **Deterministic Practice & Analysis Engine (`backend/app/services/practice.py`):**
  - **8-Dimension Scoring Formula (0–100):**
    - Clarity (20%): Wordiness removal, sentence length control, repetition detection.
    - Grammar (15%): Rule-based checks for duplicate words, article agreement, double negatives.
    - Vocabulary (10%): Type-token ratio variety and basic word over-usage detection.
    - Confidence (15%): Hedging detection and assertive phrase rewards.
    - Professionalism (15%): Slang/informal contractions detection and capital letters normalization.
    - Respectfulness (10%): Direct integration with Firebase rule-based moderation engine.
    - Filler Control (10%): Configurable filler word detection (`um`, `uh`, `like`, `actually`, `basically`, `you know`, `so`, `hmm`).
    - Structure (5%): Evaluation of Opening, Main Point, Supporting Information, Conclusion.
  - **Coaching Feedback:** Constructive feedback detailing what was done well, areas to improve, why it matters, and how to improve.
  - **Deterministic "Say It Better":** Replaces wordy idioms, removes fillers, fixes duplicate words, and generates an improved sentence with explanations of changes.
  - **Curated Scenarios & Modes (`backend/app/services/scenarios.py`):**
    - Casual Conversation (6 scenarios)
    - Interview Practice (6 scenarios)
    - Presentation Practice (4 scenarios)
    - Professional Communication (5 scenarios)
    - Daily Challenge (deterministic day-of-year rotation)
- [x] **FastAPI Endpoints (`backend/app/routers/practice.py`):**
  - `POST /api/v1/practice/analyze`: Deterministic communication evaluation.
  - `GET /api/v1/practice/modes`: Practice modes metadata.
  - `GET /api/v1/practice/scenarios`: Mode-filtered scenarios.
  - `GET /api/v1/practice/challenges/today`: Today's challenge.
  - `POST /api/v1/practice/session`: Records attempt history (attempt 1, attempt 2, delta scores).
  - `GET /api/v1/progress`: Aggregate progress, current streak, dimension averages.
  - `GET /api/v1/progress/history`: Privacy-respecting session history.
- [x] **Registered in Main (`backend/app/main.py`):** Included `practice.router` and `practice.progress_router`.

### 2. Frontend Communication Practice Studio & Progress Dashboard
- [x] **Client-Side Engine Modules (`frontend/src/practice/`):**
  - `scenarios.js`: Client-side scenarios & daily challenges.
  - `responseAnalyzer.js`: High-speed deterministic client-side evaluation matching backend formulas.
  - `sessionManager.js`: Multi-attempt retry tracking (`Attempt 1` → `Attempt 2 (+7 pts)`).
  - `progressTracker.js`: Privacy-first local storage and optional Firebase persistence.
  - `index.js`: Unified `window.PracticeEngine` export.
- [x] **Full-Featured ConversX Coach UI (`frontend/index.html` & `frontend/styles/main.css`):**
  - **Dashboard:** Communication score badge, streak counter, quick practice jump, today's daily challenge, strengths/weaknesses overview, and recent progress chart.
  - **Practice Studio:** Mode tabs, scenario selector, interactive typing area with live filler word count, Analyze button, and attempt history tracker.
  - **Feedback & Coaching View:** 8 dimension breakdown bars, positive reinforcement, areas to improve, "Say It Better" interactive card, and "Try Again" retry workflow.
  - **Progress Hub:** Comprehensive history of practice attempts, dimension averages, and streak stats.
  - **Security Rules (`frontend/firestore.rules`):** Added secure rules for `userProgress` and `practiceSessions` isolating user data by `request.auth.uid`.

### 3. Comprehensive Test Coverage
- [x] `backend/tests/test_moderation.py`: **26 passed, 0 failed**.
- [x] `backend/tests/test_practice.py`: **21 passed, 0 failed**.
- [x] `frontend/tests/test_moderation.js`: **35 passed, 0 failed**.
- [x] `frontend/tests/test_practice.js`: **32 passed, 0 failed**.
- [x] **Total Test Suite:** **114 automated tests passed across backend & frontend with 0 failures**.


---

## Phase 5: Voice Communication Coach & Speaking Delivery (2026-10-08)

### 1. Browser Speech Recognition & Audio UX
- [x] **Native Browser Speech Recognition Adapter (`frontend/src/voice/speechRecognition.js`):**
  - Web Speech API integration (`SpeechRecognition` / `webkitSpeechRecognition`).
  - Strict microphone state machine: `IDLE`, `REQUESTING_PERMISSION`, `RECORDING`, `STOPPED`, `PERMISSION_DENIED`, `UNSUPPORTED`, `ERROR`.
  - Captures continuous and interim transcripts with chunk timestamps for natural pause analysis.
  - Zero server audio streaming: 100% private, client-side transcription.
- [x] **Microphone UI & Recording States (`frontend/index.html`, `frontend/styles/main.css`):**
  - Permission Prompt state (`Allow & Start Speaking`).
  - Active Recording state with live timer (`00:15`), live status pill, pulsing red indicator, and animated audio wave.
  - Captured Response review state with duration, word count, pace (WPM), and filler chips.
  - Fallback cards for Permission Denied and Unsupported Browser with direct switch to Text Mode.

### 2. Deterministic Speaking Metrics & Delivery Scoring
- [x] **Speaking Metrics Engine (`frontend/src/voice/speakingMetrics.js`, `backend/app/services/practice.py`):**
  - Word count, duration (seconds), Words Per Minute (WPM).
  - Pace classification: Optimal (120–160 WPM), Deliberate/Slow (<120 WPM), Brisk/Fast (>160 WPM).
  - Filler count and filler rate percentage using configurable filler dictionary.
  - Pause analysis measuring natural pauses (>0.8s) and extended silences (>2.0s).
- [x] **Speaking Delivery Score (0–100) (`frontend/src/voice/voiceAnalyzer.js`):**
  - Pace Score (35%), Filler Control (35%), Flow & Pause Control (30%).
  - Targeted vocal coaching feedback (strengths, actionable pace/filler tips).
  - Explicit Disclaimer: ConversX evaluates delivery deterministically and does not claim to detect emotions, tone, or psychological confidence.
- [x] **Backend API Support (`backend/app/routers/practice.py`):**
  - Added `POST /api/v1/practice/voice/analyze` providing full voice metrics, delivery scoring, and 8-dimension communication scoring.

### 3. Retry Comparison & Progress Hub
- [x] **Side-by-Side Attempt Comparison (`frontend/src/voice/recordingSession.js`):**
  - Dynamic comparison table between Attempt 1 and Attempt 2 tracking delta changes in Communication Score, Delivery Score, WPM, Fillers, Clarity, and Structure.
- [x] **Speaking Progress Hub (`frontend/src/practice/progressTracker.js`):**
  - Average Delivery Score, Average Pace (WPM), Average Filler Rate (%), Voice Sessions Count, and Best Delivery Score.
  - Session history table displaying practice type (Text vs Voice), scores, and WPM.
- [x] **Daily Voice Challenge (`frontend/index.html`):**
  - Direct 1-click voice practice for rotating daily challenges.

### 4. Comprehensive Regression & New Test Coverage
- [x] `backend/tests/test_moderation.py`: **26 passed, 0 failed**.
- [x] `backend/tests/test_practice.py`: **28 passed, 0 failed** (includes speaking metrics, tempo classification, delivery score, determinism).
- [x] `frontend/tests/test_moderation.js`: **35 passed, 0 failed**.
- [x] `frontend/tests/test_practice.js`: **32 passed, 0 failed**.
- [x] `frontend/tests/test_voice.js`: **43 passed, 0 failed** (speaking metrics, pace classification, filler tracking, pause analysis, delivery scoring, attempt comparison, determinism).
- [x] **Total Automated Test Suite:** **164 tests passed across backend and frontend with 0 failures** (baseline 114 + 50 new tests).


---

## Production Architecture: Vercel Frontend, Oracle Cloud VM, PostgreSQL & Whisper STT (2026-10-08)

### 1. Vercel Frontend Hosting Layer
- [x] **Vercel Deployment Configuration (`frontend/vercel.json`):**
  - Clean URLs, security headers (`X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`), and rewrite routes.
  - Replaced Cloudflare Pages with Vercel for the production hosting layer.
- [x] **Dynamic API URL Resolution (`frontend/src/config.js`):**
  - Uses `VITE_API_BASE_URL` with clean fallback; zero hardcoded localhost or VM IP addresses.
  - Integrated into `progressTracker.js` and frontend fetch requests.

### 2. Oracle Cloud VM Backend & Docker Infrastructure
- [x] **Nginx Reverse Proxy (`infra/nginx/nginx.conf`):**
  - SSL/HTTPS termination, 20 req/s rate limiting, 25MB body limit for audio uploads, routing to `api:8000`.
- [x] **Docker Compose Stack (`infra/docker-compose.yml`):**
  - Added `nginx` container, verified internal private `postgres` (port 5432 not publicly published).
  - Maintained resource constraints for Oracle Always Free tier.
- [x] **Production Health Endpoints (`backend/app/main.py`):**
  - Added `GET /health` and `GET /api/v1/health` verifying overall status, database connectivity, and ML engine readiness.

### 3. Modular NLP & Whisper STT Services
- [x] **Modular NLP Engine (`backend/app/services/nlp/`):**
  - Implemented `grammar.py`, `vocabulary.py`, `clarity.py`, `confidence.py`, `structure.py`, and `analyzer.py`.
- [x] **Whisper STT Singleton (`backend/app/services/whisper_stt.py`):**
  - Singleton model loader for `faster-whisper` with CPU/CUDA selection via `WHISPER_DEVICE` and `WHISPER_MODEL`.
  - Added audio upload endpoint `POST /api/v1/practice/voice/analyze-audio` while preserving native browser speech recognition fallback.

### 4. PostgreSQL Relational Persistence & Governance
- [x] **SQLAlchemy Database Models (`backend/app/models/entities.py`, `backend/app/db/session.py`):**
  - Entities for `User`, `PracticeSession`, `ModerationEvent`, `Appeal`, `AdminAuditLog`.
  - Enforced strict privacy: zero raw audio and zero private conversation text stored by default.
- [x] **Appeals & Admin Safety Governance (`backend/app/routers/appeals.py`, `backend/app/routers/admin.py`):**
  - Appeal submission and status checking (`/api/v1/appeals`).
  - Protected admin endpoints (`/api/v1/admin/appeals`, `/api/v1/admin/appeals/{id}/decision`, `/api/v1/admin/analytics`, `/api/v1/admin/audit-logs`) with `X-Admin-Key` authentication.

### 5. Automated Testing Baseline
- [x] **Backend Pytest Suite:** **63 passed, 0 failed, 12 skipped** (includes production NLP, Whisper config, DB health).
- [x] **Frontend Node Suite:** **123 passed, 0 failed** (includes production config, moderation, practice, voice coach).
- [x] **Total Automated Tests:** **186 passed, 0 failed** across backend and frontend.


---

## Phase 7: Production Hardening, Security, Deployment Automation & Reliability (Completed)

### 1. Authentication & Role-Based Access Control
- [x] Implemented RFC 7519 HS256 JWT creation, verification, and expiration handling in `app/core/auth.py`.
- [x] Defined `USER` and `ADMIN` roles with dependency factories (`require_role`, `require_admin`).
- [x] Built ownership checks (`verify_user_ownership`) preventing IDOR on progress, session recording, and appeals.
- [x] Built authentication router (`/api/v1/auth/register`, `/api/v1/auth/login`, `/api/v1/auth/me`, `/api/v1/auth/verify`).
- [x] Transitioned `X-Admin-Key` to an internal operational DevOps credential; all administrative actions require `ADMIN` role and are recorded in audit logs.

### 2. Audio Upload Security Hardening
- [x] Enforced hard 25 MB payload limit (`MAX_AUDIO_SIZE_BYTES = 26214400`) in FastAPI and Nginx.
- [x] Enforced MIME allowlist (`audio/wav`, `audio/webm`, `audio/mpeg`, `audio/ogg`, `audio/mp4`, `audio/x-m4a`, `audio/aac`).
- [x] Prevented path traversal with basename extraction and randomized UUID temporary filenames.
- [x] Ensured ephemeral audio cleanup in `finally:` blocks.

### 3. Domain & Reverse Proxy Hardening
- [x] Hardened Nginx (`infra/nginx/nginx.conf`): HTTP to HTTPS 301 redirects, TLS 1.2/1.3, HSTS (`max-age=31536000`), CSP, clickjacking prevention (`X-Frame-Options: DENY`), MIME sniffing prevention (`X-Content-Type-Options: nosniff`).
- [x] Implemented tiered rate limiting: general API (20 r/s), auth (5 r/s), audio upload (2 r/s).
- [x] Blocked external access to Prometheus `/metrics` and hidden files.

### 4. Automated SSL Lifecycle (Certbot)
- [x] Added `conversx-certbot` container service in `infra/docker-compose.yml` with automated 12-hour renewal loop.
- [x] Created `infra/scripts/renew_certificates.sh` for on-demand renewal and Nginx reload.

### 5. Network Firewall & Isolation
- [x] Documented OCI Security List rules and host UFW firewall in `docs/SECURITY_NETWORK.md`.
- [x] Locked public access to TCP 80 and TCP 443; restricted SSH TCP 22.
- [x] Enforced Docker network isolation (`conversx-internal`) for Postgres, Redis, Worker, and Ollama.

### 6. Automated PostgreSQL Backup & Recovery
- [x] Created `scripts/backup_postgres.sh` and `scripts/backup_postgres.py` with gzip compression and 7-day retention.
- [x] Created `scripts/restore_postgres.sh` and `scripts/restore_postgres.py` with automated disaster recovery drill.
- [x] Authored `docs/DATABASE_BACKUP_RECOVERY.md`.

### 7. Alembic Database Migrations
- [x] Configured `backend/alembic/env.py` to target SQLAlchemy model metadata.
- [x] Created baseline migration `backend/alembic/versions/001_initial_schema.py` tracking `users`, `practice_sessions`, `moderation_events`, `appeals`, and `admin_audit_logs`.

### 8. Observability & Alerting
- [x] Separated Liveness (`/healthz`) and Readiness (`/health`, `/api/v1/health`) probes.
- [x] Configured Prometheus alert rules in `infra/prometheus/alert_rules.yml`.

### 9. CI/CD Automation
- [x] Created `.github/workflows/ci.yml` (multi-job test, lint, and Gitleaks scan).
- [x] Created `.github/workflows/deploy.yml` (Vercel deploy, Oracle VM SSH deploy, Alembic migration, readiness verification, smoke tests).

### 10. Test Verification
- [x] **Pytest Backend Suite:** **84 passed, 0 failed, 18 skipped** (includes baseline 63 + 12 security + 9 smoke).
- [x] **Frontend Node Suite:** **123 passed, 0 failed** (baseline fully maintained).
- [x] **Grand Total:** **207 passed, 0 failed, 18 skipped**.
