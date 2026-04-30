# CodeRecall Release Runbook

This runbook describes setup, release checks, security configuration, and reset steps for CodeRecall (码错本).

## Prerequisites

- Python 3.9.6
- Node.js 18+
- A shell with access to the project root

## Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
```

## Security Setup (Required Before Any Real Use)

Edit `backend/.env` and configure:

```bash
# Production environment label — triggers JWT secret validation
APP_ENV=production

# Generate a strong secret:  openssl rand -hex 32
JWT_SECRET_KEY=<your-64-char-hex-secret>

# Change from the publicly known default "coderecall"
OLD_USER_INITIAL_PASSWORD=<strong-password>

# Your frontend origin (no trailing slash)
FRONTEND_ORIGIN=https://your-domain.com
```

**Mandatory checks:**
- `JWT_SECRET_KEY` MUST be set to a non-default value. The backend raises `RuntimeError` on startup if the default value is used outside `development`/`test`.
- `OLD_USER_INITIAL_PASSWORD` MUST be changed. The default `coderecall` is publicly known and constitutes a backdoor. After first login as `old_user`, change the password immediately via the UI or API.
- See [SECURITY.md](../SECURITY.md) for the full production security checklist.

## Frontend Setup

```bash
cd frontend
npm install
npm run build
```

The frontend reads `VITE_API_BASE_URL` at build time (defaults to `http://localhost:8000/api/v1`).

## Development Mode

```bash
# Terminal 1 — backend
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — frontend
cd frontend && npm run dev
```

Open `http://localhost:5173`. Backend API docs: `http://localhost:8000/docs`.

## Production Mode

```bash
# Build frontend
cd frontend && VITE_API_BASE_URL=https://api.your-domain.com/api/v1 npm run build

# Start backend (no --reload)
cd backend && source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Serve `frontend/dist` as static files. Configure your reverse proxy to:
- Serve `frontend/dist` for all non-API paths (SPA fallback to `index.html`)
- Proxy `/api/v1/*` and `/auth/*` to backend port 8000
- **Disable proxy buffering for SSE** (`proxy_buffering off` in nginx; long connection timeout ≥ 120s)

## Database Migration on Startup

Since the C-002+H-001 fix, the backend lifespan hook **always** invokes `alembic upgrade head` on startup. The behavior on migration failure depends on whether the database is empty or already initialized:

| State | Migration result | Outcome |
| --- | --- | --- |
| Empty DB (SQLite file missing, or no `alembic_version` table) | success | Schema upgraded to head; `old_user` ensured |
| Empty DB | failure | Falls back to `Base.metadata.create_all` + warning log; app still starts |
| Existing DB (SQLite file exists, or `alembic_version` table present) | success | Schema upgraded to head |
| Existing DB | failure | **Application fails to start** (RuntimeError). No silent `create_all` — that would corrupt schema by skipping migration semantics |

Operational consequences:

- A manual `alembic upgrade head` step is **no longer required** before launching the backend; the application handles it on boot. The pre-launch step is kept in this runbook for operators who prefer to validate migrations explicitly.
- Before any production deploy that ships new migrations: **back up the database** (`cp coderecall.db coderecall.db.$(date +%Y%m%d-%H%M%S).bak` for SQLite; `pg_dump` for Postgres) and run a full upgrade in staging first.
- If `uvicorn --workers > 1`, prefer `--workers 1` or gunicorn so only one worker performs the upgrade. SQLite has no advisory lock; concurrent migration is unsupported.
- Migration failure logs land at `ERROR` level for existing DBs (containing the exception chain) and `WARNING` level for empty DBs (containing the fallback notice).

## Environment Variables

Backend variables live in `backend/.env`; use `backend/.env.example` as the template.

| Variable | Required | Description |
| --- | --- | --- |
| `APP_NAME` | Yes | FastAPI display name |
| `APP_ENV` | Yes | `development` / `test` / `production` |
| `API_V1_PREFIX` | Yes | Versioned route prefix (`/api/v1`) |
| `BACKEND_HOST` | Yes | uvicorn bind host |
| `BACKEND_PORT` | Yes | uvicorn bind port |
| `FRONTEND_ORIGIN` | Yes | Allowed CORS origin |
| `DATABASE_URL` | Yes | SQLAlchemy URL (SQLite default) |
| `JWT_SECRET_KEY` | Yes | HS256 signing secret — **change in production** |
| `JWT_ALGORITHM` | Yes | JWT algorithm (default `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Yes | Token lifetime (default `10080` = 7 days) |
| `OLD_USER_INITIAL_PASSWORD` | Yes | Legacy owner account password — **change immediately** |
| `ENABLE_AI_ANALYSIS` | Yes | Enable AI endpoints (`false` by default) |
| `LLM_PROVIDER` | Yes | AI provider identifier |
| `LLM_BASE_URL` | Yes | Provider API base URL |
| `LLM_MODEL` | Yes | Default analysis model |
| `LLM_MODEL_PREMIUM` | No | Premium analysis model |
| `LLM_QUICK_MODEL` | No | Fast model for variant generation |
| `LLM_API_KEY` | Yes (AI) | Provider API key — never commit |
| `LLM_ALLOWED_MODELS` | Yes | Comma-separated model allowlist |

Frontend:

| Variable | Required | Description |
| --- | --- | --- |
| `VITE_API_BASE_URL` | No | API base URL (build-time). Defaults to `http://localhost:8000/api/v1` |

## Verification Commands

```bash
# Backend tests (expected: 184 passed)
cd backend && .venv/bin/python -m pytest --tb=short -q

# Frontend tests (expected: 40 passed)
cd frontend && npm run test -- --run

# TypeScript check
cd frontend && npx tsc --noEmit

# Frontend build
cd frontend && npm run build

# Security smoke test — unauthenticated request must return 401
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/mistakes
# Expected: 401
```

## Reset / Fresh Start

```bash
cd backend
rm -f coderecall.db
source .venv/bin/activate
alembic upgrade head
```

## Known Release Blockers

The following P0/P1 issues must be resolved before production deployment. See [SECURITY.md](../SECURITY.md) for details.

| ID | Severity | Summary |
| --- | --- | --- |
| C1 | P0 | `old_user` default password `coderecall` is a publicly known backdoor |
| M1 | P0 | `APP_ENV` defaults to `development`, permits default JWT secret on misconfig |
| M2 | P1 | SSE error path `body.detail` type guard broken (React crash on 422) |
| M3 | P1 | Registration endpoint has no field length/character constraints |
| M4 | P1 | v3 session dedup condition too weak (same-second sessions merge) |
| M-new | P1 | Dashboard `Promise.all` crashes entire page if any single stat endpoint fails |
