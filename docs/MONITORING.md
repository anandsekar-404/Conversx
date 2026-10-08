# ConversX — Monitoring, Observability & Alerting Guide

## 1. Health Probe Architecture

ConversX divides health verification into two distinct probe endpoints:

### Liveness Probe (`GET /healthz`)
- **Purpose**: Verifies that the FastAPI process is responsive.
- **Used By**: Docker health checks, container orchestrators, Uptime Kuma.
- **Expected Status**: HTTP 200 `{"status": "ok", "service": "conversx-api"}`.
- **Behavior**: Fast in-memory response; no heavy database queries.

### Readiness Probe (`GET /health` & `GET /api/v1/health`)
- **Purpose**: Validates connectivity to required external dependencies.
- **Checks**:
  - PostgreSQL connectivity (`check_db_health()`).
  - Whisper STT singleton configuration readiness.
- **Response**:
  ```json
  {
    "status": "ok",
    "database": "connected",
    "whisper_stt": "ready",
    "device": "cpu",
    "version": "1.0.0"
  }
  ```
- **Security**: Never leaks database credentials, internal IPs, or connection strings.

---

## 2. Prometheus Metrics

The FastAPI gateway exports Prometheus metrics on `GET /metrics` (internal only, blocked from public web):
- `conversx_http_requests_total`: Labeled by `method`, `path`, `status`.
- `conversx_http_request_duration_seconds`: Histogram measuring request latency.

### Prometheus Configuration
Location: [`infra/prometheus/prometheus.yml`](file:///C:/Users/anand/Conversx/infra/prometheus/prometheus.yml)
- Scrape interval: 15 seconds.
- Retention: 3 days (optimized for Oracle VM RAM constraints).

---

## 3. Prometheus Alert Rules

Location: [`infra/prometheus/alert_rules.yml`](file:///C:/Users/anand/Conversx/infra/prometheus/alert_rules.yml)

| Alert Rule | Condition | Severity | Description |
| :--- | :--- | :--- | :--- |
| `ApiUnavailable` | `up{job="conversx-api"} == 0` for 1m | **Critical** | FastAPI process is unreachable. |
| `ApiHigh5xxErrorRate` | 5xx error rate > 5% for 3m | **Critical** | Severe application runtime errors detected. |
| `ApiHighLatency` | p95 latency > 2.0s for 5m | **Warning** | Elevated API latency under load. |
| `DatabaseUnavailable` | `conversx_db_connected == 0` for 1m | **Critical** | PostgreSQL connection has failed. |
| `VoiceAudioProcessingFailures` | Voice STT 5xx rate > 0.5/s for 2m | **Warning** | Whisper STT audio transcription failures. |
| `SslCertificateExpiringSoon` | Cert expiry < 14 days | **Warning** | Let's Encrypt certificate renewal needed. |
| `PostgresBackupMissing` | Last backup > 36h ago | **Critical** | Automated daily backup failed to run. |
