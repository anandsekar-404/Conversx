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
4. **Optimize image size.** Multi-stage Dockerfile, `python:3.11-slim` base, CPU-only PyTorch wheel, `--no-cache-dir`, strip build tools. Target < 500 MB compressed.

**Owner decision (2026-10-03):** Keep repo private. Use lean image (Option 4) as primary mitigation. Owner to verify whether the GHCR package can be set to public while the repo stays private (Option 2).

**Status:** Option 4 implemented in Dockerfile. Option 2 pending owner verification on GitHub package settings. If image > 500 MB after optimization AND Option 2 is unavailable, re-open for paid-vs-public decision.

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
