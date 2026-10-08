# ConversX — Production Security & Privacy Architecture

## 1. Security Principles

ConversX adheres to four non-negotiable security principles:
1. **Privacy-First Data Minimization**: Never store raw user conversation text or raw audio recordings without explicit user consent.
2. **Deterministic Safety Moderation**: Moderation decisions remain 100% rule-based and Firestore-driven; no opaque AI/ML models are used for moderation.
3. **Zero Trust Network Boundaries**: Internal microservices (Postgres, Redis, Ollama, Worker) are never exposed directly to the Internet.
4. **Defense in Depth**: Security controls operate at the Cloud VCN, Host Firewall (UFW), Reverse Proxy (Nginx), Gateway (FastAPI middleware), and Application Logic layers.

---

## 2. Privacy Audit & Data Protection

| Data Type | Persistence Policy | Storage Location | Protection Mechanism |
| :--- | :--- | :--- | :--- |
| **User Spoken Audio** | **EPHEMERAL ONLY** | `/tmp/conversx-audio` | Streamed to disk for STT transcription, then deleted immediately in `finally:` block. Never persisted to permanent storage. |
| **Practice Response Text** | **TRANSIENT** | Memory only | Processed in-memory for 8-dimension scoring. Never stored in PostgreSQL tables. |
| **Communication Scores** | **PERSISTENT** | PostgreSQL `practice_sessions` | Stores aggregate integer scores (0–100) and delivery metrics (WPM, filler rate). |
| **Moderation Violations** | **HASHED AUDIT** | PostgreSQL `moderation_events` | Stores SHA-256 hash of content (`content_hash`), matched rule ID, and severity level. No raw text. |
| **User Passwords** | **SALTED HASH** | PostgreSQL `users` | NIST PBKDF2-HMAC-SHA256 with random 16-byte salt and 100,000 iterations. |
| **JWT Secrets & API Keys** | **ENVIRONMENT ONLY** | `.env` / Secret Manager | Never committed to Git; scanned via Gitleaks in CI. |

---

## 3. Audio Upload Security Hardening

Endpoint: `POST /api/v1/practice/voice/analyze-audio`

1. **Payload Size Limit**: Hard ceiling of **25 MB** (`MAX_AUDIO_SIZE_BYTES = 26214400`). Enforced both in Nginx (`client_max_body_size 25M;`) and in FastAPI streaming loop (HTTP 413 Payload Too Large).
2. **MIME Type Allowlist**: Strictly validates `Content-Type`:
   - `audio/wav`, `audio/webm`, `audio/mpeg`, `audio/ogg`, `audio/mp4`, `audio/x-m4a`, `audio/aac`.
3. **File Extension Validation**: Allowed extensions restricted to `.wav`, `.webm`, `.mp3`, `.ogg`, `.m4a`, `.aac`.
4. **Path Traversal Prevention**: Client-supplied filename is never used to construct server file paths. Files are written using randomized UUID identifiers (`conversx_voice_{uuid}.{ext}`).
5. **Guaranteed Cleanup**: Temporary audio files are purged in a `finally:` block regardless of transcription success or failure.

---

## 4. Nginx Reverse Proxy Hardening

- **TLS Version**: TLS 1.2 and TLS 1.3 only; SSLv2, SSLv3, TLS 1.0, and TLS 1.1 are explicitly disabled.
- **HSTS**: `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload` always applied.
- **Content Security Policy**: Restricts script execution, fonts from Google Fonts, and API connections to `api.conversx.com` and `firestore.googleapis.com`.
- **Anti-Clickjacking**: `X-Frame-Options: DENY`.
- **MIME Sniffing Prevention**: `X-Content-Type-Options: nosniff`.
- **Microphone Permissions**: `Permissions-Policy: microphone=(self), camera=(), geolocation=()`.
- **Metrics Isolation**: `GET /metrics` returns HTTP 403 Forbidden on public requests.

---

## 5. Rate Limiting Policy

| Target Endpoint | Rate Limit | Burst Allowance | Zone Purpose |
| :--- | :--- | :--- | :--- |
| **General API** | 20 req/s | Burst 30 | Protects against traffic surges. |
| **Audio STT Upload** | 2 req/s | Burst 4 | Prevents CPU/RAM exhaustion on Whisper STT singleton. |
| **Authentication** | 5 req/s | Burst 10 | Mitigates credential stuffing and brute-force attacks. |
