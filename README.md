# ConversX — Communication Practice & Voice Coaching Platform

**ConversX** is an intelligent, privacy-first communication and voice practice platform designed to help individuals elevate their speaking and writing skills across real-world professional dialogues, interviews, presentations, and daily conversations.

ConversX functions as a **personal communication coach** that guides users through text and voice scenarios, analyzes speaking tempo (WPM), detects filler words, scores speech delivery, suggests deterministic "Say It Better" alternatives, enables multi-attempt retries with side-by-side comparison, and tracks improvement over time.

> **Core Principle:** ConversX is a practice and learning platform — not a certification platform.

---

## 1. Target Production Architecture

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
                             │
                ┌────────────┴────────────┐
                ↓                         ↓
         COMMUNICATION                 SAFETY
           ANALYSIS                   ENGINE
                │                         │
          ┌─────┼─────┐              ┌────┴────┐
          ↓     ↓     ↓              ↓         ↓
       Grammar Clarity Vocabulary   Safe    Violation
          │     │     │                        │
          └─────┼─────┘                     Warning
                ↓                           / Ban
          Feedback Engine                     │
                ↓                         Appeal
       Communication Score                    │
                ↓                         Admin Review
         Progress Tracking                    │
                                             ↓
                                       Admin Decision

                        FIREBASE
                            │
                            ↓
                   Moderation Rules
```

---

## 2. Infrastructure Components

### A. Frontend Layer (Vercel)
- **Framework**: Modern HTML5, Vanilla CSS3 design system, and ES Modules.
- **Routing & Security**: Configured via `frontend/vercel.json` with clean URLs, SPA rewrites, and security headers (`X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`).
- **Dynamic API Resolution**: `frontend/src/config.js` uses `VITE_API_BASE_URL` to point to the Oracle Cloud API gateway via HTTPS without hardcoding IPs or localhost.

### B. Backend API Gateway (Oracle Cloud VM)
- **Gateway**: FastAPI 0.115 running on Python 3.12+ inside Docker.
- **Reverse Proxy**: Nginx 1.27 with SSL termination, 20 req/s rate limiting, and 25 MB request body limit for audio uploads.
- **Health Checks**: `/health` and `/api/v1/health` providing operational readiness for API, Database, and ML services.
- **Observability**: Prometheus metrics on `/metrics` and structured JSON request logging.

### C. Database Layer (PostgreSQL 16)
- **Container**: `postgres:16.15-alpine` running on internal Docker network.
- **Security**: Port 5432 is strictly private and never exposed to the public internet.
- **Entities**: Users, Practice Sessions, Moderation Events, Appeals, and Admin Audit Logs.
- **Privacy Model**: Zero raw audio and zero private conversation text stored by default. Only aggregate metrics, scores, and timestamps are saved with user consent.

### D. ML / NLP Engine
- **Whisper Speech-to-Text**: Controlled singleton model (`faster-whisper 1.2.1`) on Oracle VM. Configurable via `WHISPER_MODEL=small` and `WHISPER_DEVICE=cpu`. Model is kept in memory and never reloaded per request.
- **Browser Web Speech API**: Retained as zero-latency client-side lightweight fallback.
- **Modular NLP Layer (`backend/app/services/nlp/`)**:
  - `grammar.py`: Rule-based grammar and friction point detection.
  - `vocabulary.py`: Type-token ratio and basic overused word analysis.
  - `clarity.py`: Wordy idioms and run-on sentence detection.
  - `confidence.py`: Hedging language vs assertive framing.
  - `structure.py`: 4-part delivery analysis (Opening, Main Point, Evidence, Conclusion).
  - `analyzer.py`: Unified NLP facade.

### E. Safety & Moderation Layer (Firebase Firestore)
- **Rule Source of Truth**: Centralized Firebase collections (`badWords`, `harassmentPatterns`, `categories`, `severityLevels`, `improvementSuggestions`).
- **Decoupled Governance**: Safety moderation is cleanly separated from user practice coaching. Violations log hashed records and provide formal appeal workflows (`/api/v1/appeals`).
- **Admin Security**: Admin governance endpoints (`/api/v1/admin/appeals`, `/api/v1/admin/analytics`) are protected by `X-Admin-Key` header authentication.

---

## 3. Environment Variables Configuration

Copy `.env.example` to `.env` (chmod 600 on Linux):

| Variable | Description | Example |
| :--- | :--- | :--- |
| `APP_ENV` | Application environment | `production` / `development` |
| `APP_SECRET_KEY` | 32-byte secret key | `secrets.token_hex(32)` |
| `VITE_API_BASE_URL` | Base URL for frontend API calls | `https://api.conversx.com` |
| `CORS_ORIGINS` | Allowed origins (no wildcards in prod) | `https://conversx.vercel.app` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@postgres:5432/conversx` |
| `WHISPER_MODEL` | Whisper model size | `small` |
| `WHISPER_DEVICE` | Whisper execution device | `cpu` / `cuda` |
| `ADMIN_API_KEY` | Admin API secret key | `your-secure-admin-key` |
| `FIREBASE_PROJECT_ID` | Firebase project identifier | `conversx-prod` |

---

## 4. Deployment Instructions

### Local Development
```bash
# 1. Start Docker stack (Postgres, Redis, API)
docker compose -f infra/docker-compose.yml --env-file .env up -d

# 2. Run backend locally without Docker (optional)
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 3. Serve frontend locally
npx serve frontend -p 3000
```

### Deploying Frontend to Vercel
```bash
# Using Vercel CLI
cd frontend
vercel --prod

# Configure Environment Variable in Vercel Dashboard:
# VITE_API_BASE_URL = https://api.conversx.com
```

### Deploying Backend to Oracle Cloud VM
```bash
# 1. SSH into Oracle VM
ssh opc@your-oracle-vm-ip

# 2. Clone repository & configure .env
git clone <repo-url> conversx && cd conversx
cp .env.example .env && nano .env

# 3. Start production containers with Nginx SSL reverse proxy
docker compose -f infra/docker-compose.yml --env-file .env up -d --build
```

---

## 5. Automated Testing

### Run All Test Suites
```bash
# Backend pytest suite (Moderation, Practice, Modular NLP, Security Hardening, Production Smoke)
pytest backend/tests tests/production/smoke -v

# Frontend test suites (Moderation, Practice, Voice coach, Vercel config)
node frontend/tests/test_moderation.js
node frontend/tests/test_practice.js
node frontend/tests/test_voice.js
node frontend/tests/test_production.js
```

**Verified Test Results:**
- **Backend Pytest**: **84 passed, 0 failed, 18 skipped** (includes baseline 63 + 12 security + 9 smoke).
- **Frontend Node.js**: **123 passed, 0 failed** (moderation, practice, voice, production).
- **Total Suite**: **207 passed, 0 failed, 18 skipped**.

---

## 6. Phase 7 Production Hardening Documentation

Comprehensive operational and architectural documentation:
- [Architecture & Data Flow](docs/ARCHITECTURE.md)
- [Production Deployment Guide](docs/DEPLOYMENT.md)
- [Security & Privacy Standards](docs/SECURITY.md)
- [Network Firewall & Oracle Cloud Hardening](docs/SECURITY_NETWORK.md)
- [PostgreSQL Backup & Disaster Recovery Guide](docs/DATABASE_BACKUP_RECOVERY.md)
- [Authentication & RBAC Architecture](docs/AUTHENTICATION.md)
- [Monitoring & Observability Guide](docs/MONITORING.md)
- [CI/CD Pipelines Documentation](docs/CI_CD.md)
- [Phase 7 Master Completion Report](docs/PHASE7_COMPLETION.md)
