# ConversX Decisions Log

> Conflicts, trade-offs, and architectural choices are recorded here with options and a recommendation.
> Format: decision date, issue, options, recommendation, status.

---

## D-001 · GHCR storage vs private repo (2026-10-03)

**Trigger:** Free-tier check (FREE_TIER.md). GHCR private-repo free storage is 500 MB. The backend Docker image (Python + all ML deps) is estimated at 600–900 MB compressed. This may exceed the free allowance.

**Options:**
1. **Make the GitHub repo public.** GHCR storage becomes unlimited for public repos. Downside: source code is public. All secrets are in environment variables, never in the repo.
2. **Keep package public while repo stays private.** GitHub allows package visibility to be set independently of repo visibility. A private repo can publish a public GHCR package, getting unlimited storage while keeping source private. **This is the preferred option to investigate.**
3. **Keep private, accept GHCR billing.** ~$0.008/GB-month. Violates "no paid services" rule — do not use without owner approval.
4. **Optimize image size & layer architecture (Measured 2026-10-04):**
   - Current local build: 3.06 GB uncompressed, 701 MB compressed layer archive.
   - Largest layers over 100 MB:
     - `1.75 GB`: Python `site-packages` (torch CPU 698 MB, transformers 120 MB, spacy 113 MB, sympy 78 MB, ctranslate2.libs 75 MB, av.libs 72 MB, onnxruntime 67 MB).
     - `461 MB`: System apt runtime (`ffmpeg` + `libpq5` + `curl`).
     - `150 MB`: Debian `python:3.11-slim` base layers.
   - Proposed reductions:
     - **4a. Split API vs Worker images:** API service drops PyTorch/Whisper/Transformers entirely (API image ~250–300 MB, well under the 500 MB free tier). Only `worker` holds ML runtimes (~2.2 GB).
     - **4b. Keep model weights in volumes (implemented):** Named Docker volumes (`whisper_models`, `hf_cache`, `ollama_models`) keep all model checkpoints out of the container layers.
     - **4c. Slim system ffmpeg:** Since PyAV bundles its own codec binaries (`av.libs`, 72 MB), replace full `apt-get install ffmpeg` (460 MB) with static minimal binaries or rely on PyAV.

**Owner decision (2026-10-04):** Keep repo private; drop system ffmpeg in favor of PyAV for decoding and durations; split api/worker targets (API image lean, worker image holds ML dependencies); plan to publish the worker image as a public package, to be confirmed after the first push.

**Status:** Accepted - Plan confirmed. Multi-target Dockerfile (api vs worker), dropping system ffmpeg in favor of PyAV, and public GHCR package for worker image to be finalized after initial push.

---

## D-002 · GitHub repo visibility (2026-10-03)

**Trigger:** D-001.

**Owner decision (2026-10-03):** Keep repo private. Investigate GHCR public package setting (D-001 Option 2).

**Status:** Accepted — private repo. D-001 tracking image size.

---

## D-003 · Brevo daily cap vs growth (2026-10-03)

**Trigger:** FREE_TIER.md. Brevo free = 300 emails/day. At >200 new registrations/day (verification + welcome), cap is hit.

**Options:**
1. Stay on Brevo free until cap is hit; then upgrade (~€15/month Starter).
2. Self-host an SMTP relay (e.g., Postfix on the Oracle VM). Requires DKIM/SPF configuration and has deliverability risk.
3. Use a secondary provider as overflow.

**Recommendation:** Option 1. At MVP scale (no public launch until Gate B), 300/day is more than sufficient. Add a code-side daily-cap guard and queue on exhaustion. Revisit if DAU > 100 before Gate B.

**Status:** Accepted — implement cap guard in Week 12 prep. No action needed for Week 1.

---

## D-004 · LanguageTool vs rule-based grammar (2026-10-03)

**Trigger:** §6 of MASTER_PROMPT.md. LanguageTool requires ~1 GB of JVM RAM, which is excluded by default.

**Options:**
1. Rule-based grammar checks (spaCy + heuristics). Minimal RAM.
2. LanguageTool local server if Week 1 benchmark shows headroom.

**Recommendation:** Option 1 as default. Revisit only if Gate A/B headroom is > 4 GB after all other services. Record in BENCHMARKS.md.

**Status:** Accepted — use spaCy + heuristics.

---

## D-005 · LLM model selection (provisional — Week 1 benchmark gate) (2026-10-03)

**Trigger:** §6 and §13 Week 1 milestone. Model must be chosen by benchmark.

**Candidates (from §6):** Qwen2.5 1.5B Q4, Qwen2.5 3B Q4, Llama 3.2 3B Q4, Gemma 2 2B Q4.

**Gate scope (owner decision 2026-10-03):** CPU-only with 2 CPU / 9 GB container limits. GPU (RTX 3050) is **non-gating** — a separate GPU run may be recorded in BENCHMARKS.md as an informational extra, labelled non-gating.

**Preliminary estimates (laptop, AMD64, CPU-only):**
- Qwen2.5 1.5B Q4_K_M: ~1.0 GB RAM, ~20–160 t/s CPU
- Qwen2.5 3B Q4_K_M: ~1.8–1.9 GB RAM, ~5–40 t/s CPU
- Gate criterion: ≥ 5 t/s sustained. Both candidates likely pass.
- Prefer 3B for quality if ≥ 5 t/s confirmed; fall back to 1.5B if not.

**Download time note (25 Mbps connection):** 3B Q4 model ~2 GB → ~11 min download. 1.5B ~1 GB → ~6 min. Plan accordingly during benchmark run.

**Status:** Open — actual benchmark measurement required. Do not assume. Decision closes at Gate A.

---

## D-006 · STT model selection (provisional — Week 1 benchmark gate) (2026-10-03)

**Trigger:** §6 and §13 Week 1. Whisper base or small, int8.

**Preliminary estimates:**
- base int8: ~400–600 MB RAM, faster RTF
- small int8: ~600–900 MB RAM, better WER
- Gate criterion: 30 s clip RTF ≤ 2.0 (≤ 60 s wall-clock)

**Status:** Open — benchmark measurement required. Do not assume. Decision closes at Gate A.

---

## D-007 · Host selection post-Oracle (2026-10-03)

**Trigger:** §18 addendum — Oracle account blocked.

**Options (per §18.5):**
1. Oracle Always Free once payment verification unblocks.
2. Student-credit cloud (GCP, Azure, AWS Educate).
3. Home machine behind Cloudflare Tunnel (demo/beta only — no real user data without encrypted off-site backups).

**Trade-offs:**
- Oracle: best free specs (2 OCPU, 12 GB), but no uptime SLA and idle-reclaim risk.
- Student credit: expiry risk; credits may not cover all services.
- Home server: zero uptime guarantee; real user data should not live there (PRIVACY.md concern).

**Recommendation:** Wait for Oracle verification. Use local machine (owner's laptop) for Gate A. Gate B requires a real server before any public launch.

**Status:** Open — owner action required (Oracle payment verification).

---

## D-008 · Domain registration cost (2026-10-03)

**Trigger:** §3 — `conversx.com` is the one non-free item.

**Estimated cost:** ~$10–15/year for a .com domain (Cloudflare Registrar, Namecheap, or similar).

**Status:** Open — owner purchases the domain when ready for Gate B. No action in Week 1.

---

## D-009 · Multilingual toxicity detection gap (2026-10-03)

**Trigger:** §8 — Detoxify's multilingual model does not cover Hindi, Tamil or Hinglish.

**Options:**
1. Lexicon-only for Hindi/Tamil/Hinglish (conservative thresholds).
2. Evaluate a small multilingual model in Week 1 if RAM allows (per §8).

**Recommendation:** Option 1 as default. Week 1 benchmark will determine if there is headroom for Option 2. Record outcome in BENCHMARKS.md.

**Status:** Open — resolve after Gate A RAM measurements.

---

## D-010 · Moderation placement: text-chat moderation latency vs queue starvation (2026-10-04)

**Trigger:** Text-chat moderation must not queue behind long-running STT jobs (which take 15–60 seconds of CPU time). If audio transcription and chat moderation share a single-concurrency RQ worker (`stt llm`), a single user submitting a voice note blocks all text chat moderation for up to a minute (head-of-line blocking).

**Options:**
1. **In-process moderation inside FastAPI (`api` service) with pinned `--workers 1`:**
   - *Pros:* Zero queue latency for real-time text chat (synchronous or threadpool inference in <100 ms); instant feedback to users without network hops.
   - *Cons:* Allocates ~750 MB–1 GB RAM permanently inside the API container. If Uvicorn runs multiple workers (`--workers 2`), memory is duplicated (~1.5 GB). Requires strictly pinning Uvicorn to `--workers 1` in the API container.
2. **Dedicated RQ `moderation` queue with a dedicated worker container (`conversx-worker-mod`):**
   - *Pros:* Completely decouples moderation from STT (`worker` processes `stt`, `worker-mod` processes `moderation`). Chat messages are not blocked behind 30 s audio transcription jobs. Preserves single instance of Detoxify in memory (~750 MB).
   - *Cons:* Adds a separate worker container in `docker-compose.yml` (minimal overhead, ~50 MB RAM for the RQ loop when idle).
3. **Strict priority queue ordering on the existing single worker (`rq worker --with-scheduler moderation stt llm`):**
   - *Pros:* No extra container.
   - *Cons:* Cannot preempt an actively running STT job. If Whisper is currently transcribing a 30 s clip for 20 seconds, newly arrived chat messages must still wait 20 s for the running STT job to finish.

**Owner decision (2026-10-04):** Option 1 accepted (API `--workers 1`, model loaded once in FastAPI process; worker keeps its own copy for transcripts). Ensures zero queue latency for real-time text chat moderation while avoiding worker duplication.

**Status:** Accepted - Option 1 implemented for production architecture.


---

## D-011 — Transition to 100% Rule-Based Firebase Firestore Moderation (2026-10-08)

**Trigger:** Master Prompt architectural change. Complete removal of Machine Learning / AI-based moderation models (Detoxify, PyTorch, Transformers, BERT-base, and external AI APIs). Mandate for 100% deterministic rule-based detection using Firebase Firestore as the centralized source of truth.

**Architecture:**
- **Centralized Rule Repository:** Firebase Firestore collections (`badWords`, `harassmentPatterns`, `categories`, `severityLevels`, `improvementSuggestions`).
- **Matching Engine:** Token-aware word matching (Level 1) and boundary-aware phrase matching (Level 2) to eliminate false positives (e.g., "classic" does not trigger "ass", "therapist" does not trigger "rape").
- **Deterministic Severity & Score:** Deterministic mapping to 0 (Safe), 1 (Mild), 2 (Warning), 3 (Harmful), 4 (Severe), computing a 0–100 Communication Score and dimensions (Respectfulness, Clarity, Hostility Index, Professionalism).
- **Say It Better:** Deterministic constructive suggestion engine pairing each flagged category with practical rephrasing guidance and concrete alternatives.
- **In-Memory Caching & Offline Resilience:** Rules cached in-memory and in localStorage with 5-minute TTL to eliminate Firestore roundtrips on every keystroke, falling back gracefully to curated seed rules if offline.
- **Admin Governance:** Full admin dashboard (`admin.html`) and FastAPI admin endpoints for CRUD rule management, filtering by category/severity/status, and live sandbox testing.

**System Impacts:**
1. **Memory & Footprint:** Removed `torch` (~700 MB) and Detoxify models (~500 MB). Dramatically smaller Docker image and zero PyTorch CPU memory overhead.
2. **Latency:** Replaced ~7.8 s heavy CPU model inference with sub-millisecond in-memory regex and token lookups (<1 ms).
3. **Determinism:** 100% reproducible outcomes with zero model hallucinations.

**Status:** Accepted & Implemented (Backend `app/services/moderation.py`, `app/routers/moderation.py`, Frontend `src/moderation/`, `index.html`, `admin.html`).


---

## D-012 — Deterministic Communication Practice & Coaching Platform Architecture (2026-10-08)

**Trigger:** Master Implementation Prompt. Transition ConversX from primarily a moderation system into a complete communication improvement and practice platform ("personal communication coach").

**Core Requirements & Constraints:**
1. **Preserve Deterministic Moderation:** The Firebase Firestore rule-based moderation engine established in D-011 is preserved and reused for the Respectfulness dimension.
2. **Zero ML / No External AI:** Detoxify, PyTorch, BERT, Transformers, LLMs, and external AI moderation APIs must NOT be reintroduced. The entire communication analysis pipeline is 100% deterministic, rule-based, and explainable.
3. **Privacy First:** User communication content stays local during normal typing. Raw message text is never persisted to databases by default; only session scores and aggregate metrics are recorded with user consent.
4. **No Fake Functionality:** Every interactive element (practice modes, scenario selectors, analysis, Say It Better, retry attempt tracking, dashboard progress) is fully functional without mocks or placeholders.

**Architecture Components:**
- **5 Practice Modes & 21+ Scenarios (`backend/app/services/scenarios.py`, `frontend/src/practice/scenarios.js`):**
  - Casual Conversation (meeting someone new, talking with classmate, introducing self, asking for help, making small talk, starting conversation)
  - Interview Practice (tell me about yourself, strengths, why hire you, project overview, biggest weakness, 5-year outlook)
  - Presentation Practice (technical explanation, project presentation, 1-minute intro, non-technical cybersecurity)
  - Professional Communication (professor request, professional email/request, teammate communication, respectful disagreement, asking clarification)
  - Daily Challenge (deterministic day-of-year rotation with streak tracking)
- **8-Dimension Deterministic Scoring Formula:**
  $$\text{Overall Score} = \text{Clarity} \times 20\% + \text{Grammar} \times 15\% + \text{Vocabulary} \times 10\% + \text{Confidence} \times 15\% + \text{Professionalism} \times 15\% + \text{Respectfulness} \times 10\% + \text{Filler Control} \times 10\% + \text{Structure} \times 5\%$$
  - *Clarity (20%):* Penalizes wordy filler phrases ("at this point in time", "due to the fact that"), overly long run-on sentences (>32 words), and excessive repetition.
  - *Grammar (15%):* Deterministic rule-based detection of duplicated adjacent words ("the the"), double negatives ("don't know nothing"), article mismatches ("a apple", "an book"), and subject-verb disagreements ("they is", "we was").
  - *Vocabulary (10%):* Type-Token Ratio (TTR) lexical variety analysis combined with overused basic word detection ("thing", "stuff", "very", "good").
  - *Confidence (15%):* Detects hedging expressions ("i guess", "maybe kinda", "sort of think", "sorry but") and rewards assertive framing ("i recommend", "our analysis shows", "i am confident").
  - *Professionalism (15%):* Flags informal text-speak/slang ("gonna", "wanna", "u", "thx", "btw") and excessive capitalization shout-cases.
  - *Respectfulness (10%):* Reuses Firebase rule-based moderation engine (bad words, harassment patterns, severity mapping) without ML.
  - *Filler Control (10%):* Tracks filler words ("um", "uh", "like", "actually", "basically", "you know", "so", "hmm").
  - *Structure (5%):* Verifies four-part structure: Opening, Main point, Supporting information, Conclusion.
- **Constructive Coaching Feedback:**
  - Positive reinforcement ("What you did well")
  - Targeted areas ("What needs improvement")
  - Impact context ("Why it matters")
  - Actionable guidance ("How to improve")
- **Deterministic "Say It Better":** Automatically removes filler words, replaces wordy idioms with concise equivalents, fixes duplicate words, and details specific improvements.
- **Retry & Progression Loop:**
  - Tracks Attempt 1 → Attempt 2 → Attempt 3 with live delta calculation (+7 pts).
- **Progress Tracking & Isolated Firebase Data Model:**
  - Isolated collections: `userProgress/{userId}` and `practiceSessions/{sessionId}` secured by `request.auth.uid`.

**Status:** Accepted & Implemented (Backend `app/services/practice.py`, `app/services/scenarios.py`, `app/routers/practice.py`, Frontend `src/practice/`, `index.html`, `main.css`, `firestore.rules`).


---

## D-013 — Voice Communication Architecture & Deterministic Delivery Scoring (2026-10-08)

**Trigger:** ConversX Phase 5 — Execute Voice Communication Coach. Expand ConversX into an interactive voice coach allowing users to practice speaking out loud, inspect real-time speech pacing, filler frequencies, and speech delivery metrics without sacrificing user privacy or reintroducing ML/AI models.

**Architecture Decisions:**
1. **Native Browser Speech Recognition Adapter (`frontend/src/voice/speechRecognition.js`):**
   - Utilizes standard browser Web Speech API (`SpeechRecognition` / `webkitSpeechRecognition`).
   - Zero server-side audio processing, zero PyTorch/Transformers/Whisper dependencies in API containers.
   - Robust permission state machine: `IDLE`, `REQUESTING_PERMISSION`, `READY`, `RECORDING`, `STOPPED`, `PERMISSION_DENIED`, `UNSUPPORTED`, `ERROR`.
   - Fallback behavior: Gracefully guides users on unsupported browsers (or when microphone permission is denied) to continue with Text Practice.
2. **Deterministic Speaking Metrics (`speakingMetrics.js`, `backend/app/services/practice.py`):**
   - Word count: Strict whitespace and punctuation tokenization.
   - Speaking duration: Precise timer tracking in seconds.
   - Words Per Minute (WPM): $\text{WPM} = \frac{\text{wordCount}}{\text{durationSeconds} / 60}$.
   - Pace classification:
     - Optimal / Conversational: 120–160 WPM
     - Deliberate / Slow: < 120 WPM
     - Fast / Rushed: > 160 WPM
   - Filler frequency: Reuses configured filler list (`DEFAULT_FILLER_WORDS`) with word boundary matching.
   - Filler rate: $\text{fillerRate} = \frac{\text{fillerCount}}{\text{wordCount}} \times 100\%$.
   - Pause analysis: Gaps between speech chunk timestamps (>1.2s silence = pause, >2.5s = long pause). If browser does not provide chunk timestamps, cleanly flags `available: false` (no fabricated metrics).
3. **Speaking Delivery Scoring (0–100):**
   $$\text{Delivery Score} = \text{Pace Score} \times 35\% + \text{Filler Control} \times 35\% + \text{Flow Control} \times 30\%$$
   - Evaluated as a separate score alongside the existing 8-dimension Communication Score.
   - *Explicit Disclaimer:* ConversX evaluates delivery deterministically using measurable tempo, filler frequency, and vocal continuity. ConversX does NOT claim to detect emotions, psychological confidence, tone, personality, or psychological state.
4. **Integration with Existing Engines:**
   - Transcripts are seamlessly fed into `analyzePracticeResponse` (8 dimensions: Clarity, Grammar, Vocabulary, Confidence Language, Professionalism, Respectfulness, Filler Control, Structure).
   - Reuses Firebase rule-based moderation engine for the Respectfulness dimension and safety verification.
   - Deterministic "Say It Better" produces polished alternative text on the transcript.
5. **Multi-Attempt Voice Retries & Side-by-Side Comparison:**
   - Full side-by-side comparison between Attempt 1 and Attempt 2 tracking delta changes in Communication Score, Delivery Score, WPM, Fillers, Clarity, and Structure.
6. **Privacy Model:**
   - 100% local-first. Raw audio is neither streamed nor saved on any server.
   - Only aggregate session scores and metric statistics are saved with user consent.

**Status:** Accepted & Implemented (Frontend `src/voice/`, `index.html`, `main.css`, Backend `app/services/practice.py`, `app/routers/practice.py`, tests `test_voice.js`, `test_practice.py`).


---

## D-014 — Production Architecture: Vercel Frontend, Oracle Cloud VM Backend, PostgreSQL, and Whisper STT (2026-10-08)

**Trigger:** Master Antigravity Implementation Prompt. Transition ConversX from development prototype into a clean, production-ready architecture across Vercel, Oracle Cloud VM, PostgreSQL, and Firebase.

**Target Architecture:**
```text
                         INTERNET
                             │
                             ↓
                    ┌─────────────────┐
                    │      VERCEL     │
                    │                 │
                    │ ConversX        │
                    │ Frontend        │
                    └────────┬────────┘
                             │
                             │ HTTPS / REST API
                             ↓
                  ┌─────────────────────┐
                  │  ORACLE CLOUD VM    │
                  │                     │
                  │  FastAPI Backend    │
                  │        │            │
                  │   ┌────┴────┐       │
                  │   ↓         ↓       │
                  │ PostgreSQL  ML/NLP  │
                  │             Engine  │
                  │                │    │
                  │        ┌──────┼────┐│
                  │        ↓      ↓    ↓│
                  │     Whisper  NLP Safety
                  │                │    │
                  └─────────────────────┘
                             │
                             ↓
                       RESULT + FEEDBACK
```

**Key Architectural Decisions:**
1. **Frontend Hosting on Vercel:**
   - Cloudflare Pages is completely replaced by Vercel for frontend hosting.
   - Deployed with `frontend/vercel.json` defining clean URLs, SPA rewrites (`/admin` -> `/admin.html`), and strict security headers (`X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`).
   - Centralized API base URL resolution (`frontend/src/config.js`) reads `VITE_API_BASE_URL` (e.g. `https://api.conversx.com`) without hardcoding localhost or raw VM IPs.
2. **Oracle Cloud VM Backend Stack:**
   - Oracle Always Free A1 / VM hosts containerized services managed via `infra/docker-compose.yml`:
     - `api`: FastAPI 0.115 gateway with Prometheus metrics, `/health` and `/api/v1/health` checks, and structured logging.
     - `nginx`: SSL termination, rate limiting (20 r/s), request body limit (25 MB), and reverse proxying to `api:8000`.
     - `postgres`: PostgreSQL 16 on private Docker network; port 5432 is strictly internal and never exposed to the public internet.
     - `worker`: Background RQ worker for asynchronous audio/model processing.
3. **Database & Privacy Design (`app/models/entities.py`):**
   - Stores application entities: `User`, `PracticeSession`, `ModerationEvent`, `Appeal`, `AdminAuditLog`.
   - *Core Privacy Principle:* Raw audio files and private communication transcripts are NEVER persisted to the database by default. Only aggregate metrics (scores, WPM, filler rates, timestamps, scenario IDs) are stored with user consent.
4. **Whisper STT Singleton (`app/services/whisper_stt.py`):**
   - Controlled singleton model loading via `faster-whisper`.
   - Reuses loaded model across requests without per-request reloading.
   - Configurable via `WHISPER_MODEL` (default: `small`) and `WHISPER_DEVICE` (default: `cpu`).
   - Browser Web Speech API remains available as a client-side lightweight fallback.
5. **Modular NLP Engine (`app/services/nlp/`):**
   - Structured into `grammar.py`, `vocabulary.py`, `clarity.py`, `confidence.py`, `structure.py`, and `analyzer.py`.
   - 100% deterministic baseline maintained with zero hallucinations.
6. **Safety & Appeal Pipeline Separation:**
   - Safety moderation logic (Firebase Firestore rules) is cleanly decoupled from administrative governance.
   - Violations log hashed records (`ModerationEvent`).
   - Formal appeal workflow (`POST /api/v1/appeals`, `GET /api/v1/admin/appeals`, `POST /api/v1/admin/appeals/{id}/decision`) with full administrative audit logging (`AdminAuditLog`).
   - Admin routes strictly protected by `X-Admin-Key` header authentication.
7. **No Certification Platform:** ConversX is strictly a practice and learning platform; it does not issue certificates or badges.

**Status:** Accepted & Implemented (Backend `app/models/`, `app/db/`, `app/services/nlp/`, `app/services/whisper_stt.py`, `app/routers/appeals.py`, `app/routers/admin.py`, Frontend `vercel.json`, `src/config.js`, Infra `nginx/nginx.conf`, `docker-compose.yml`).


---

## D-015: Phase 7 Production Hardening, Security, Deployment Automation & Reliability

**Date:** 2026-10-08  
**Context:**  
Phase 6 established a working multi-service architecture including PostgreSQL, Whisper STT singleton, modular NLP services, Docker Compose, and Nginx. However, the system required enterprise-grade security hardening, JWT authentication, RBAC, automated backups, Let's Encrypt SSL auto-renewal, CI/CD pipelines, and network firewall isolation to be production-ready.

**Decisions:**
1. **RFC 7519 JWT & RBAC:** Replaced static `X-Admin-Key` authentication with signed HS256 JWT tokens with role separation (`USER` vs `ADMIN`). The server verifies resource ownership to prevent Insecure Direct Object References (IDOR).
2. **Audio Upload Security Ceilings:** Implemented a strict 25 MB payload ceiling on `POST /api/v1/practice/voice/analyze-audio`, enforced MIME type and extension allowlists, sanitized filenames to block path traversal, and ensured immediate disk cleanup in `finally:` blocks.
3. **Automated SSL Certificate Lifecycle:** Configured a dedicated `certbot` container service in `infra/docker-compose.yml` to automatically renew Let's Encrypt certificates every 12 hours via webroot ACME challenge, paired with `renew_certificates.sh` to trigger Nginx reloads.
4. **Automated PostgreSQL Backup & Verification:** Created daily automated backup scripts (`scripts/backup_postgres.sh`, `scripts/backup_postgres.py`) with gzip compression, timestamping, 7-day retention, and automated restore drill testing (`scripts/restore_postgres.py drill`).
5. **Observability Split & Alerting:** Separated Liveness (`/healthz`) from Readiness (`/health`, `/api/v1/health`) probes. Configured Prometheus alert rules for service downtime, elevated 5xx error rates, latency spikes, database disconnects, and certificate expiration.
6. **Production CI/CD Pipelines:** Created `.github/workflows/ci.yml` (multi-job testing, linting, Gitleaks scan) and `.github/workflows/deploy.yml` (Vercel deploy, Oracle VM SSH deploy, Alembic migrations, smoke tests).
7. **No Certification Platforms:** Retained strict commitment that ConversX is an interactive communication practice tool without badges, exams, or certificates.
8. **Deterministic Safety Unchanged:** Firebase Firestore rule-based deterministic moderation remains 100% intact with zero AI/ML replacement.

**Status:** Accepted & Implemented (Backend `app/core/auth.py`, `app/routers/auth.py`, `app/routers/admin.py`, `app/routers/practice.py`, `app/main.py`, Infra `nginx/nginx.conf`, `docker-compose.yml`, `prometheus/alert_rules.yml`, Scripts `scripts/backup_postgres.*`, `scripts/restore_postgres.*`, Tests `test_security_phase7.py`, `test_smoke.py`).
