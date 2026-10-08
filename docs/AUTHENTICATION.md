# ConversX — Production Authentication & Authorization Architecture

## 1. Overview

In Phase 7, ConversX replaced static header checks (`X-Admin-Key`) with a production-grade authentication and authorization system based on **RFC 7519 JSON Web Tokens (JWT)** and **Role-Based Access Control (RBAC)**.

---

## 2. Authentication Tokens & Session Management

- **Algorithm**: HMAC-SHA256 (`HS256`).
- **Signature Secret**: Configured via `JWT_SECRET_KEY` in environment variables; never hardcoded.
- **Expiration**: Configurable (default: 60 minutes for access tokens).
- **Issuer**: `conversx.com`.
- **Payload Claims**:
  - `sub`: User unique identifier (e.g. `usr_1234567890ab`).
  - `username`: User display handle.
  - `role`: Role assignment (`USER` or `ADMIN`).
  - `iss`: Token issuer (`conversx.com`).
  - `iat`: Issued-at UTC timestamp (seconds).
  - `exp`: Expiration UTC timestamp (seconds).

```json
{
  "alg": "HS256",
  "typ": "JWT"
}
.
{
  "sub": "usr_9b3e1f02c4a1",
  "username": "anand",
  "role": "USER",
  "iss": "conversx.com",
  "iat": 1791475200,
  "exp": 1791478800
}
.
[HMAC-SHA256 Signature]
```

---

## 3. Role-Based Access Control (RBAC)

Two primary roles are enforced across all endpoints:

| Role | Scope | Permitted Endpoints |
| :--- | :--- | :--- |
| `USER` | Standard Practitioner | Practice evaluation, voice coaching, saving own sessions, reading own progress, submitting own appeals. |
| `ADMIN` | Safety & Governance | All `USER` actions PLUS: listing appeals, adjudicating appeals (`POST /api/v1/admin/appeals/{id}/decision`), viewing aggregate analytics, inspecting audit logs. |

---

## 4. Insecure Direct Object Reference (IDOR) Protection

The server strictly verifies identity ownership for all user-scoped resources:
- `/api/v1/progress`: Rejects requests where `user_id` does not match the token's `sub`, unless the user has the `ADMIN` role.
- `/api/v1/practice/session`: Rejects recording sessions under a different `user_id`.
- `/api/v1/appeals/{appeal_id}`: Users can only query their own submitted appeals.

Verification is implemented via `verify_user_ownership(current_user, target_user_id)` in [`backend/app/core/auth.py`](file:///C:/Users/anand/Conversx/backend/app/core/auth.py).

---

## 5. Admin API Key Transition

The legacy `X-Admin-Key` header has been transitioned:
1. **Never Primary Auth**: Normal users cannot authenticate using `X-Admin-Key`.
2. **Operational Credential**: Retained strictly as an internal operational override for automated DevOps tasks (e.g., CI/CD deploy verification scripts, automated health probes).
3. **Audit Logged**: Actions performed via operational key are logged with `admin_id: "ops_internal_admin"` in `admin_audit_logs`.
4. **Environment-Only**: Loaded from `ADMIN_API_KEY` environment variable.

---

## 6. Auth API Endpoints

- `POST /api/v1/auth/register`: Register new user with username, email, and password.
- `POST /api/v1/auth/login`: Authenticate credentials, returns Bearer JWT.
- `GET /api/v1/auth/me`: Inspect current user session and active role.
- `POST /api/v1/auth/verify`: Validate external token structure and expiration.
