# ConversX — Production Architecture Documentation

## 1. System Overview

ConversX is a production-hardened communication learning and practice platform. It empowers users to practice conversation, presentation, interview, and voice communication skills with instant deterministic feedback and delivery coaching.

```text
                                  ┌─────────────────────────────┐
                                  │      Vercel Frontend        │
                                  │    https://conversx.com     │
                                  │  - Static SPA & HTML5/ES6   │
                                  │  - Web Speech API (Client)  │
                                  │  - Client Practice Engine   │
                                  └──────────────┬──────────────┘
                                                 │
                                                 │ HTTPS / TLS 1.3
                                                 ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        Oracle Cloud Infrastructure (A1 VM)                             │
│                                                                                        │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │                            Nginx Reverse Proxy                                   │  │
│  │                         https://api.conversx.com                                 │  │
│  │  - SSL Termination (Let's Encrypt / Certbot Auto-Renew)                         │  │
│  │  - Rate Limiting (General 20r/s, Audio 2r/s, Auth 5r/s)                          │  │
│  │  - Security Headers (HSTS, CSP, X-Frame-Options, Permissions-Policy)             │  │
│  └──────────────────────────────────────────┬───────────────────────────────────────┘  │
│                                             │ conversx-internal network                │
│                                             ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │                               FastAPI Gateway                                    │  │
│  │  - RFC 7519 JWT Auth (USER vs ADMIN RBAC)                                        │  │
│  │  - Audio Upload Security (25MB limit, MIME verification, path isolation)         │  │
│  │  - Liveness (/healthz) & Readiness (/health, /api/v1/health) Probes              │  │
│  │  - Prometheus Metrics Exporter (/metrics)                                        │  │
│  └───────┬───────────────────────────┬───────────────────────────┬──────────────────┘  │
│          │                           │                           │                     │
│          ▼                           ▼                           ▼                     │
│  ┌───────────────┐           ┌───────────────┐           ┌───────────────┐             │
│  │  PostgreSQL   │           │    Redis 7    │           │  Whisper STT  │             │
│  │  (Port 5432)  │           │  (Port 6379)  │           │   Singleton   │             │
│  │  - Internal   │           │  - Internal   │           │  - CPU / int8 │             │
│  │  - Privacy DB │           │  - AOF broker │           │  - Ephemeral  │             │
│  └───────────────┘           └───────┬───────┘           └───────────────┘             │
│                                      │                                                 │
│                                      ▼                                                 │
│                              ┌───────────────┐                                         │
│                              │   RQ Worker   │                                         │
│                              │  - Background │                                         │
│                              └───────┬───────┘                                         │
│                                      │                                                 │
│                                      ▼                                                 │
│                              ┌───────────────┐                                         │
│                              │  Ollama LLM   │                                         │
│                              │ (Port 11434)  │                                         │
│                              └───────────────┘                                         │
└────────────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼ HTTPS
                        ┌─────────────────────────────┐
                        │     Firebase Firestore      │
                        │ - Deterministic Moderation  │
                        │ - Bad Words & Harassment    │
                        │ - Zero AI/ML Moderation     │
                        └─────────────────────────────┘
```

---

## 2. Component Directory

| Layer | Technology | Hosting | Purpose |
| :--- | :--- | :--- | :--- |
| **Frontend** | Vanilla JS, CSS3, HTML5 | Vercel Edge | Serves UI, client-side speech recognition, practice scenarios, and progress hub. |
| **Edge Ingress** | Nginx 1.27 Alpine | Oracle Cloud VM | Terminates SSL, manages ACME renewal, enforces security headers, rate limiting. |
| **API Gateway** | FastAPI / Python 3.11 | Docker on Oracle VM | JWT Auth, RBAC, Audio STT upload, Appeals, Practice analytics, Health probes. |
| **Database** | PostgreSQL 16 Alpine | Docker on Oracle VM | Stores users, practice attempts, delivery metrics, moderation audit events, appeals. |
| **Queue & Broker** | Redis 7 Alpine / RQ | Docker on Oracle VM | Asynchronous task processing for heavy audio and LLM batch jobs. |
| **Speech-to-Text** | Faster-Whisper (small, int8) | Docker Singleton | Transcribes uploaded user audio clips (ephemeral storage only). |
| **Safety Engine** | Firebase Firestore Rules | Firebase | Centralized deterministic rule source for bad words and harassment patterns. |
| **Monitoring** | Prometheus & Uptime Kuma | Docker on Oracle VM | System metrics collection, alert rules, and uptime tracking. |
