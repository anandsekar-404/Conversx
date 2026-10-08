# ConversX — CI/CD Pipeline Documentation

## 1. Continuous Integration (`.github/workflows/ci.yml`)

The CI workflow triggers on every Pull Request and Push to `main`. It guarantees that no broken or insecure code is merged.

```text
Pull Request / Push
        │
        ├── 1. Backend Pytest Job (Ubuntu + Postgres 16 + Redis 7)
        │      ├── Setup Python 3.11
        │      ├── Install dependencies (CPU Torch, FastAPI, faster-whisper)
        │      ├── Run Alembic migrations (alembic upgrade head)
        │      ├── Execute Pytest Suite (Unit, NLP, Security, Smoke)
        │      └── Enforce ZERO failures
        │
        ├── 2. Frontend Node.js Job (Node 20)
        │      ├── Run Moderation Tests (test_moderation.js)
        │      ├── Run Practice Tests (test_practice.js)
        │      ├── Run Voice Coach Tests (test_voice.js)
        │      └── Run Production Architecture Tests (test_production.js)
        │
        └── 3. Security & Privacy Scan Job
               └── Run Gitleaks secret scan across Git history
```

---

## 2. Continuous Deployment (`.github/workflows/deploy.yml`)

The CD workflow triggers on merge to the `main` branch after CI succeeds.

```text
Merge to main
     │
     ├── 1. Deploy Frontend to Vercel
     │      └── Vercel CLI builds & deploys to production edge
     │
     └── 2. Deploy Backend to Oracle Cloud VM (via SSH)
            ├── Pull latest code
            ├── Pull updated container images
            ├── Run Alembic migrations (alembic upgrade head)
            ├── Zero-downtime container restart (docker compose up -d)
            ├── Wait for readiness health check (https://api.conversx.com/health)
            └── Run automated production smoke tests
```

---

## 3. GitHub Secrets Configuration

The following encrypted secrets must be configured in GitHub repository settings:
- `VERCEL_TOKEN`: Vercel automation deployment token.
- `VERCEL_ORG_ID`: Vercel organization ID.
- `VERCEL_PROJECT_ID`: Vercel project ID.
- `ORACLE_VM_HOST`: Public IP address or hostname of Oracle Cloud VM.
- `ORACLE_VM_USER`: SSH username (e.g. `ubuntu`).
- `ORACLE_SSH_KEY`: Private SSH key for Oracle VM deployment.
