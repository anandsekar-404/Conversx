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
