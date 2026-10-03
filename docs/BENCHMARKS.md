# ConversX Benchmarks

> **Rule (§0.2):** Never invent measurements. All numbers below are **provisional (laptop)** until Gate B re-runs on the target server.
> Last updated: 2026-10-03

---

## Benchmark Environment

| Field | Value |
|---|---|
| Host OS | Windows 11 (AMD64) |
| Machine | ASUS TUF Gaming F15 FX506HC |
| CPU | Intel Core i5-11400H @ 2.70 GHz, 6 cores / 12 threads |
| GPU | NVIDIA RTX 3050 (4 GB) — **non-gating extra only** |
| Total RAM | 23.8 GB |
| Architecture | x86_64 (AMD64) |
| Docker | Install Docker Desktop; apply infra/wslconfig.example |
| Benchmark date | Not yet run — Gate A pending |
| Mode | Local-first (§18.2), container limits: 2 CPUs, 9 GB RAM |
| Gate scope | **CPU-only** (owner decision 2026-10-03). GPU results are recorded separately as informational extras, labelled **non-gating**. |
| Internet speed | 25 Mbps (affects model download times only, not gate criteria) |

> All numbers below are **PROVISIONAL (laptop, AMD64)**. They must be re-verified at Gate B on the target ARM64 server (Oracle A1 or equivalent). Performance on ARM64 with CPU-optimised inference may differ significantly.

---

## Gate A Targets (from §13 Week 1)

| Metric | Gate criterion | Provisional result |
|---|---|---|
| STT: 30 s clip wall-clock (RTF ≤ 2.0) | ≤ 60 s | **NOT YET MEASURED** |
| LLM throughput | ≥ 5 tokens/s | **NOT YET MEASURED** |
| Full-stack peak RAM (all containers) | ≤ 8.5 GB | **NOT YET MEASURED** |

**Gate A passes if all three criteria are met.** If any fails, step models down and record in DECISIONS.md before proceeding to Week 2.

---

## STT — faster-whisper (to be measured)

| Model | Quantization | Estimated RAM | Estimated RTF (x86 CPU) | Status |
|---|---|---|---|---|
| whisper-base | int8 | ~400–600 MB | < 1.0 (estimate) | **UNVERIFIED** |
| whisper-small | int8 | ~600–900 MB | ~0.5–1.5 (estimate) | **UNVERIFIED** |

**Benchmark plan:** Transcode a 30 s and a 60 s clean speech sample. Measure wall-clock time and RSS. Record RTF = wall_clock / audio_duration. Primary target: small int8. Fall back to base if RAM or RTF gate fails.

**Filler words:** After model selection, record 10 utterances containing common fillers (um, uh, er, like, you know). Count survival rate. If < 80%, report filler count as a lower bound (§9).

---

## LLM — Ollama (to be measured)

| Model | Quantization | Estimated RAM | Estimated t/s (x86 CPU) | Status |
|---|---|---|---|---|
| Qwen2.5 1.5B | Q4_K_M | ~1.0 GB | 20–160 t/s (estimate) | **UNVERIFIED** |
| Qwen2.5 3B | Q4_K_M | ~1.8–1.9 GB | 5–40 t/s (estimate) | **UNVERIFIED** |
| Llama 3.2 3B | Q4_K_M | ~1.8–2.0 GB | 5–35 t/s (estimate) | **UNVERIFIED** |
| Gemma 2 2B | Q4_K_M | ~1.4–1.6 GB | 10–50 t/s (estimate) | **UNVERIFIED** |

**Benchmark plan:** Run each model with Ollama via `ollama run <model> --verbose`. Measure eval rate (t/s) and RSS. Primary target: Qwen2.5 3B (quality). Fall back to 1.5B if < 5 t/s or RAM budget exceeded.

---

## Toxicity Model — Detoxify (to be measured)

| Model | Architecture | Estimated RAM | Status |
|---|---|---|---|
| detoxify `original` | BERT-base | ~500 MB–1 GB | **UNVERIFIED** |
| detoxify `original-small` | ALBERT | ~200–400 MB | **UNVERIFIED** |

**Benchmark plan:** Load model, run inference on 100 text samples. Measure RSS at peak.

---

## Full-Stack RAM Budget (target vs estimated)

| Component | §6 Target | Provisional Estimate | Actual (TBD) |
|---|---|---|---|
| faster-whisper (base/small int8) | 0.7–1.3 GB | 0.4–0.9 GB | — |
| Ollama + 1–3B Q4 | 1.5–3.0 GB | 1.0–1.9 GB | — |
| Detoxify toxicity model | 0.4–0.8 GB | 0.5–1.0 GB | — |
| PostgreSQL | 0.6 GB | 0.4–0.6 GB | — |
| Redis | 0.2 GB | 0.1–0.2 GB | — |
| API + worker processes | 1.2 GB | 0.8–1.2 GB | — |
| Prometheus + Uptime Kuma | 0.6 GB | 0.3–0.6 GB | — |
| cloudflared + Docker daemon + OS | 1.2 GB | 0.5–1.0 GB | — |
| **Headroom** | **≥ 3.5 GB** | TBD | — |
| **Total** | **≤ 9.0 GB (12 GB server)** | — | — |
| **Local gate (9 GB limit)** | **≤ 8.5 GB** | — | — |

---

## Non-LLM API Performance (to be measured)

| Endpoint | Target p95 | Actual (TBD) |
|---|---|---|
| Auth reads/writes | < 300 ms | — |
| Text scoring + moderation | < 500 ms | — |
| STT 30 s clip end-to-end | ≤ 90 s p95 (up to 3 queued) | — |
| LLM 100-token reply | ≤ 25 s (excl. queue wait) | — |

---

## Decisions Made from Benchmarks

*(This section populated after Gate A measurements)*

- [ ] STT model chosen: TBD
- [ ] LLM model chosen: TBD
- [ ] Multilingual toxicity model evaluated: TBD
- [ ] Grafana headroom check: TBD
- [ ] LanguageTool headroom check: TBD (expected: no room → use spaCy)
- [ ] 4 GB swap added: TBD
- [ ] Max audio clip duration (based on RTF): TBD
