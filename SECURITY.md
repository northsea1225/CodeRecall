# Security Policy

This document covers the security posture of CodeRecall / 码错本 and serves as the production deployment security checklist.

## Scope

| Component | In Scope |
|-----------|----------|
| Backend API (FastAPI) | Yes |
| Frontend SPA (React) | Yes |
| SQLite database | Yes |
| JWT authentication | Yes |
| LLM / AI integration | Yes |
| Alembic migrations | Yes |

## Supported Deployment Modes

| Mode | JWT Secret | old_user | Registration | Notes |
|------|-----------|----------|--------------|-------|
| Local dev | Default OK | Default OK | Open | `APP_ENV=development` |
| Demo / staging | Must change | Must change | Open or restricted | `APP_ENV=production` |
| Production | **Must change** | **Disable or change** | Restrict | `APP_ENV=production` |

## Required Production Environment Variables

| Variable | Requirement | How to Generate |
|----------|------------|-----------------|
| `JWT_SECRET_KEY` | Non-default, ≥ 32 bytes random | `openssl rand -hex 32` |
| `JWT_ALGORITHM` | `HS256` (default) | — |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Default 120 (2 hours, was 10080 pre-C-005) | Lower values reduce XSS exposure window; refresh endpoint keeps sessions alive |
| `ACCESS_TOKEN_REFRESH_GRACE_SECONDS` | Default 120 | Leeway for `/auth/refresh` to tolerate clock skew (do not set > 600) |
| `TOKEN_BLACKLIST_CLEANUP_INTERVAL_SECONDS` | Default 600 | Throttled lazy cleanup of expired blacklist rows |
| `OLD_USER_INITIAL_PASSWORD` | Non-default, strong | Must be changed after first login |
| `APP_ENV` | `production` | Set explicitly in deployment |
| `FRONTEND_ORIGIN` | Your actual frontend origin | No trailing slash, no wildcard |
| `LLM_API_KEY` | Secret, never commit | Provided by LLM vendor |

## JWT Security Checklist

- [ ] `JWT_SECRET_KEY` is set to a randomly generated value (not the default `change-me-in-production`)
- [ ] `APP_ENV=production` is set — this triggers the backend fail-fast check on startup
- [ ] Token TTL (`ACCESS_TOKEN_EXPIRE_MINUTES`) is reviewed and set appropriately
- [ ] Tokens are stored in `localStorage` on the frontend — XSS exposure window is **2h** after C-005 Part 1 (was 7d); Part 2 will move to HttpOnly Cookie + CSRF
- [ ] Logout calls `POST /auth/logout` to revoke the token's `jti` server-side; `get_current_user` rejects requests with revoked jti
- [ ] Silent refresh uses an isolated axios instance (no interceptor recursion); single-flight + 0-60s jitter prevents refresh thundering herd
- [ ] HTTPS is used in production — tokens in transit must be encrypted
- [ ] Frontend logout clears token from localStorage and redirects to `/login`

## Token Revocation (C-005 Part 1)

Implemented 2026-05-03 to address attack chain risk from `localStorage`-stored 7-day JWTs.

**Mechanism**:
- Every issued JWT includes a unique `jti` (uuid4 hex) claim
- `POST /api/v1/auth/logout` writes the current token's `jti` into `token_jti_blacklist` (alembic migration `0011`)
- `get_current_user` rejects any request whose `jti` is on the blacklist (returns 401 `token_revoked`)
- Logout endpoint also throttle-triggers cleanup of expired blacklist rows (every 600s)

**Refresh path**:
- `POST /api/v1/auth/refresh` accepts the current Bearer token, validates signature + grace-window expiry + blacklist, then issues a new token with a fresh `jti`
- **Old `jti` is intentionally NOT revoked** during a normal refresh — preserves multi-tab usability; only logout writes the blacklist
- Rate limit: `120/minute;1000/hour` (NAT/multi-tab tolerant; unlike login's `10/minute` since refresh has no bcrypt cost)

**Frontend silent refresh**:
- Request interceptor pre-emptively refreshes when token has < 5 minutes left (with 0-60s jitter to avoid thundering herd at deployment time)
- Response interceptor catches 401 and single-flights one refresh + retries the original request once
- Concurrent requests share the same in-flight refresh promise

**Cross-tab logout sync**:
- `authStore` listens for the `storage` event; when another tab removes `coderecall_token`, this tab also clears state and routes to `/login`

**Known limitation (Part 2 will fix)**:
- Tokens still live in `localStorage`, exposed to XSS (now reduced to 2h max)
- No HttpOnly Cookie / CSRF yet — planned in C-005 Part 2 (12h, depends on this Part 1 + I-006 e2e harness)

## Default / Legacy User Checklist

`old_user` (id=1) is automatically created to own all data that existed before the authentication system was added.

- [ ] `OLD_USER_INITIAL_PASSWORD` is set to a strong, non-default value before deployment
- [ ] After first login as `old_user`, change the password immediately
- [ ] Consider setting `old_user.is_active = False` if no legacy data needs to be accessed (disables login while preserving data ownership)

**Risk**: The default password `coderecall` is publicly documented. Any instance deployed without changing this password is immediately vulnerable to account takeover.

## Registration Validation

**Current state (known issue M3):** The registration endpoint lacks field constraints. The following are not enforced server-side:

- Password minimum length
- Password maximum length (bcrypt silently truncates at 72 bytes)
- Username character set restrictions

**Mitigation until fixed:** Consider disabling public registration or restricting the `/auth/register` endpoint behind a network-level control in production.

## AI / LLM Security

- [ ] `LLM_API_KEY` is stored only in `backend/.env`, never committed to version control
- [ ] `LLM_ALLOWED_MODELS` is set to an explicit allowlist — prevents model injection from client requests
- [ ] `ENABLE_AI_ANALYSIS=false` by default — opt-in per deployment
- [ ] SSE error responses do not leak raw LLM error messages to the frontend (see known issue M2)
- [ ] URL import providers are restricted to Codeforces and LeetCode only — no arbitrary SSRF

## CORS and Frontend Origin

- `FRONTEND_ORIGIN` sets the single allowed CORS origin
- Wildcards (`*`) are never used in the CORS configuration
- In production, set `FRONTEND_ORIGIN` to your exact frontend URL including scheme and port

## Data Protection

- SQLite database file (`coderecall.db`) should have filesystem permissions restricted to the process user (`chmod 600`)
- `/api/v1/export/v3` produces a full backup including review history — do not expose publicly
- Imported backup files are processed server-side; validate source before importing

## Deployment Security Checklist

Before going live, verify each item:

- [ ] `JWT_SECRET_KEY` is non-default and randomly generated
- [ ] `APP_ENV=production` is set
- [ ] `OLD_USER_INITIAL_PASSWORD` is non-default; `old_user` password changed after first login
- [ ] `FRONTEND_ORIGIN` matches actual frontend URL
- [ ] `LLM_API_KEY` is not committed to version control
- [ ] HTTPS is enforced for all traffic
- [ ] Reverse proxy disables buffering for SSE endpoints (`proxy_buffering off`)
- [ ] SQLite database file permissions are restricted (`chmod 600 backend/coderecall.db`)
- [ ] Registration is restricted or monitored in production
- [ ] All P0/P1 known issues below are addressed

## Known Security Work Items

These issues were identified in a three-model code review (Codex + Gemini + Claude, 2026-04-25). P0/P1 must be resolved before production deployment.

| ID | Severity | File | Issue | Mitigation |
|----|----------|------|-------|-----------|
| C1 | P0 | `alembic/versions/0007_add_user_system.py`, `init_db.py`, `auth_service.py` | `old_user` default password `coderecall` is publicly known | Set `OLD_USER_INITIAL_PASSWORD` before deployment; consider disabling `old_user` login (`is_active=False`) |
| M1 | P0 | `config.py` | `APP_ENV` defaults to `development`, permitting default JWT secret on misconfiguration | Set `APP_ENV=production` explicitly; backend already fail-fasts when `JWT_SECRET_KEY` is default in non-dev/test |
| M2 | P1 | `useAiAnalysisStream.ts` | SSE HTTP error path: `body.detail` may be array (FastAPI 422) or object, causing React render crash | Add type guard: `typeof body.detail === "string" ? body.detail : null` |
| M3 | P1 | `auth.py`, `auth_service.py` | Registration has no field constraints (1-char password accepted; bcrypt silently truncates >72 bytes) | Add `Field(min_length=8, max_length=72)` to `RegisterIn`; sync frontend form rules |
| M4 | P1 | `import_export_service.py` | v3 session dedup uses only 4 fields; same-second sessions with same strategy may merge | Add `ended_at` and `completed_count` to dedup key, or use stable session UUID in payload |
| M-new | P1 | `Dashboard/index.tsx` | `Promise.all` over 5 stat endpoints — any single failure crashes the entire Dashboard | Replace with `Promise.allSettled`; degrade each metric independently |

## Accepted CVEs

Test-only or compensating-control CVEs that are tracked but not auto-remediated. CI passes `--ignore-vuln` for these IDs to `pip-audit`.

| CVE / GHSA | Package | Severity | Fix Version | Why Accepted |
|------------|---------|----------|-------------|--------------|
| GHSA-6w46-j5rx-g56g | pytest 8.4.2 | MODERATE | 9.0.3 | `/tmp/pytest-of-{user}` collision on UNIX. Test-time dependency only; no production exposure. |

> **History**: prior to the I-008 Python 3.11 upgrade (2026-05-01), three additional CVEs were accepted because their fixes required Python ≥ 3.10:
> GHSA-wp53-j4wj-2cfg (python-multipart, HIGH, fix 0.0.22), GHSA-mj87-hwqh-73pj (python-multipart, MODERATE, fix 0.0.26),
> GHSA-mf9w-mj56-hr94 (python-dotenv, MODERATE, fix 1.2.2). All three are now resolved by upgrading to multipart 0.0.27 + dotenv 1.2.2.

## Reporting Security Issues

Please report security vulnerabilities by opening an issue on the project repository and marking it with the `security` label. Do not include exploit details in public issues.
