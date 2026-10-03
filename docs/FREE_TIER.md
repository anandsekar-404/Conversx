# ConversX Free-Tier Register

> **Rule (§0.3):** Never invent facts about free tiers. Every limit below is sourced. If unverifiable, it is marked **UNVERIFIED**.
> Last updated: 2026-10-03

---

## Cloudflare Pages

| Limit | Value | Alert at |
|---|---|---|
| Builds per month | 500 | 350 (70%) |
| Concurrent builds | 1 | — |
| Build timeout | 20 min | — |
| Custom domains per project | 100 | — |
| Static asset requests/bandwidth | Unlimited | — |
| Pages Functions requests/day | 100,000 (Workers Free quota) | 70,000 |

**Source:** https://developers.cloudflare.com/pages/platform/limits/ — verified 2026-10-03  
**Current usage:** 0 builds (project not yet created)  
**Mitigation:** Two separate Pages projects (app + admin) each consume from the same 500-build pool. Use preview URLs during heavy iteration.

---

## Cloudflare R2

| Limit | Value | Alert at |
|---|---|---|
| Storage | 10 GB-month | 7 GB |
| Class A operations (writes/lists) | 1,000,000/month | 700,000 |
| Class B operations (reads) | 10,000,000/month | 7,000,000 |
| Egress (internet) | Free | — |
| Delete operations | Free (not counted) | — |

**Source:** https://developers.cloudflare.com/r2/pricing/ — verified 2026-10-03  
**Notes:**
- Only Standard storage tier receives the free allowance.
- Daily backups (pg_dump compressed) estimated 10-50 MB each. 7-daily + 4-weekly + 3-monthly = ~500 MB worst-case. Well within 10 GB.
- Free tier does not expire. Confirmed.

---

## Cloudflare Access (Zero Trust Free)

| Limit | Value | Alert at |
|---|---|---|
| Active users (seats) | 50 | 40 |
| Log retention | 24 hours | — |
| Uptime SLA | None | — |

**Source:** https://www.cloudflare.com/plans/zero-trust-services/ — verified 2026-10-03  
**Notes:** 50 seats cover admin users only. End users are not behind Access. MVP admin team << 50, no risk.

---

## Cloudflare Turnstile

| Limit | Value |
|---|---|
| Requests | Unlimited on free plan |

**Source:** https://developers.cloudflare.com/turnstile/ — verified 2026-10-03

---

## Brevo (transactional email)

| Limit | Value | Alert at |
|---|---|---|
| Emails per day | 300 | 210 (70%) |
| Retry queue on limit hit | 1,000 transactional emails queued | — |
| Contact storage | 100,000 contacts | — |
| Branding | "Sent by Brevo" footer on free plan | — |

**Source:** https://www.brevo.com/pricing/ — verified 2026-10-03  
**Mitigation:** Code-side guard checks daily sent count from Brevo API before sending; on exhaustion, queue in DB and retry next day. Transactional retry queue of 1,000 provides a safety buffer.  
**Conflict:** At >200 registrations/day, the cap is hit. See DECISIONS.md.

---

## GHCR (GitHub Container Registry)

| Limit | Value | Alert at |
|---|---|---|
| Storage (public repos) | Unlimited | — |
| Storage (private repos) | 500 MB free | 350 MB |
| Bandwidth (private) | 1 GB/month free | 700 MB |

**Source:** https://docs.github.com/en/billing/managing-billing-for-github-packages/about-billing-for-github-packages — verified 2026-10-03  
**CONFLICT:** arm64 backend image estimated 600-900 MB compressed. If repo is private, this may exceed 500 MB. See DECISIONS.md.

---

## GitHub Actions

| Limit | Value | Alert at |
|---|---|---|
| Minutes/month (public repo) | Unlimited | — |
| Minutes/month (private repo) | 2,000 min free | 1,400 min |
| Concurrent jobs | 20 | — |

**Source:** https://docs.github.com/en/billing/managing-billing-for-github-actions — verified 2026-10-03  
**Notes:** QEMU-based arm64 builds count as Linux minutes (1x). Each build ~10-20 min; ~100-200 CI runs on a private repo budget. Mitigate with Docker layer caching and restricting image job to main.

---

## Oracle Always Free (target server — deferred to Gate B)

| Resource | Allowance |
|---|---|
| Ampere A1 compute | 4 OCPU + 24 GB RAM pool; allocate 2 OCPU + 12 GB |
| Block volume | 200 GB total |
| Boot volume backups | 5 free backup slots |
| Outbound data | 10 TB/month |

**Source:** https://www.oracle.com/cloud/free/ — **UNVERIFIED** (Oracle account blocked; numbers from public docs 2026-10-03)  
**Status:** Do not assume Oracle. Record here for Gate B planning only.

---

## Backblaze B2 (optional second backup)

| Limit | Notes |
|---|---|
| Free tier | **UNVERIFIED** — verify before Gate B |

**Action needed:** Verify B2 free tier availability before Gate B. R2 is primary.

---

## Risk Summary

| Service | Risk | Severity | Mitigation |
|---|---|---|---|
| CF Pages builds | 500/month shared | Low | Use preview deployments during dev |
| Brevo email cap | 300/day hard limit | Medium | Daily cap guard; queue on exhaustion |
| GHCR storage | 500 MB free (private) | Medium | Lean multi-stage image or public repo |
| GitHub Actions | 2,000 min/month (private) | Low-Medium | Cache layers; image job on main only |
| Oracle idle reclaim | Server may be terminated | High (Gate B) | Off-Oracle encrypted backups + rebuild procedure |
| CF Access seats | 50 admin seats | None for MVP | Admin team << 50 |
