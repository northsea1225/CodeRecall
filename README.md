# CodeRecall / 码错本

![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)
![Node 18+](https://img.shields.io/badge/Node-18%2B-green.svg)
![pytest](https://img.shields.io/badge/pytest-229%20passed-success.svg)
![vitest](https://img.shields.io/badge/vitest-45%20passed-success.svg)

**CodeRecall / 码错本** is an intelligent, spaced-repetition programming mistake notebook for OI/ACM/LeetCode competitors. Core differentiators: 6-stage dynamic AI coaching (adapts to your review history, not generic replies) + SM-2 forgetting-curve scheduling + one-click LeetCode/Codeforces import.

Core loop: **Import problem → Record mistake → SM-2 scheduled review → 6-stage dynamic AI deep analysis**

## ✨ Features

- **Spaced Repetition (SM-2):** Optimized review scheduling for long-term retention.
- **6-Stage AI Coaching:** Dynamic prompts adapt to your review stage (`new_mistake` / `early_review` / `repeated_weakness` / `lapsed` / `oscillator` / `maintenance`).
- **JWT User Auth & Data Isolation:** Secure per-user data with Bearer token authentication; access tokens auto-refresh silently with single-flight + 5-minute pre-expiry; logout writes the token's `jti` to a server-side revocation list.
- **Streak Dashboard:** Continuous review streak, heatmap, trend charts, algorithm radar.
- **Immersive Dark Room Review:** Full-screen distraction-free review mode (`/review/immersive`).
- **CF / LeetCode URL Import:** One-click problem statement import from Codeforces and LeetCode (CN/EN).
- **schema_v3 Import/Export:** Full backup including review history, UUID cross-device dedup, backward-compatible with v1/v2.
- **Rich Code Editing:** Monaco editor with syntax highlighting; Markdown + LaTeX (KaTeX) rendering.
- **Categorization & Tags:** Organize mistakes by language, algorithm category, and custom tags.

## 🏗️ Architecture

```text
+-------------------+     REST API & SSE      +-------------------+
|   Frontend (SPA)  | <---------------------> |   Backend (API)   |
|                   |                         |                   |
| React 18          |                         | FastAPI           |
| TypeScript        |                         | SQLAlchemy        |
| Vite              |                         | SQLite            |
| Ant Design 5      |                         | Alembic           |
| react-router-dom  |                         | JWT Auth          |
| Zustand 5         |                         | SSE AI            |
+-------------------+                         | SM-2 Engine       |
                                              +-------------------+
```

## 🚀 Quick Start

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install --require-hashes -r requirements.txt
cp .env.example .env             # edit .env: set JWT_SECRET_KEY and OLD_USER_INITIAL_PASSWORD
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. API docs: `http://localhost:8000/docs`.

## 📦 Updating Backend Dependencies

Backend dependencies are pinned with hashes via [`pip-tools`](https://pip-tools.readthedocs.io/). The flow:

1. Edit `backend/requirements.in` (human-maintained version constraints).
2. Recompile to regenerate `backend/requirements.txt`:
   ```bash
   cd backend
   pip install pip-tools
   pip-compile --generate-hashes --resolver=backtracking requirements.in -o requirements.txt
   ```
3. Verify in a clean venv:
   ```bash
   pip install --require-hashes -r requirements.txt
   pytest tests/ -q                                                    # 229 passed
   pip-audit --strict --requirement requirements.txt \
     --ignore-vuln GHSA-6w46-j5rx-g56g
   ```

`requirements.txt` is generated — **do not edit it by hand**. The remaining accepted CVE (pytest, test-only) is documented in [`SECURITY.md`](SECURITY.md#accepted-cves).

## ⚙️ Environment Variables

Create `backend/.env` from `backend/.env.example`.

### Core

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_ENV` | Runtime label: `development`, `test`, `production` | `development` |
| `DATABASE_URL` | SQLAlchemy connection string | `sqlite:///./coderecall.db` |
| `FRONTEND_ORIGIN` | Allowed CORS origin | `http://localhost:5173` |

### Auth (required in production)

| Variable | Description | Default |
|----------|-------------|---------|
| `JWT_SECRET_KEY` | HS256 signing secret — **must change in production** | `change-me-in-production` |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime (minutes); silent refresh keeps sessions alive | `120` (2 hours) |
| `ACCESS_TOKEN_REFRESH_GRACE_SECONDS` | Leeway for `/auth/refresh` to tolerate clock skew | `120` |
| `TOKEN_BLACKLIST_CLEANUP_INTERVAL_SECONDS` | Throttle for lazy cleanup of revoked-token table | `600` |
| `OLD_USER_INITIAL_PASSWORD` | Initial password for legacy-data owner account | `coderecall` |

### AI (optional)

| Variable | Description | Default |
|----------|-------------|---------|
| `ENABLE_AI_ANALYSIS` | Enable AI endpoints | `false` |
| `LLM_PROVIDER` | Provider identifier | `deepseek` |
| `LLM_MODEL` | Default analysis model | `deepseek-v4-pro` |
| `LLM_MODEL_PREMIUM` | Premium analysis model | `deepseek-v4-pro` |
| `LLM_QUICK_MODEL` | Fast model (variant generation) | `deepseek-v4-flash` |
| `LLM_API_KEY` | Provider API key — never commit | `` |
| `LLM_BASE_URL` | Provider base URL | `https://api.deepseek.com/v1` |
| `LLM_ALLOWED_MODELS` | Comma-separated allowlist | `deepseek-v4-pro,deepseek-v4-flash` |

## 🔌 API Endpoints

All routes are at `/api/v1`, including auth (`/api/v1/auth/*`).

**Live docs**: <http://localhost:8000/docs> (Swagger UI) or <http://localhost:8000/redoc>.
**Static reference**: [`docs/openapi.json`](docs/openapi.json) — auto-generated by `scripts/gen-docs.sh`; do not hand-edit. The `openapi-sync` GitHub Actions workflow blocks PRs whose checked-in JSON drifts from the live FastAPI schema.

| Route | Description |
|-------|-------------|
| `POST /api/v1/auth/token` | Login (form-encoded, rate-limited 10/min) |
| `POST /api/v1/auth/register` | Register new user (JSON, rate-limited 3/hour) |
| `POST /api/v1/auth/refresh` | Refresh access token (rate-limited 120/min;1000/hour) |
| `POST /api/v1/auth/logout` | Revoke current token's jti |
| `GET /api/v1/auth/me` | Current user info |
| `GET /api/v1/mistakes` | List mistakes (paginated, filterable) |
| `POST /api/v1/mistakes` | Create mistake |
| `GET /api/v1/review/sessions/{id}/next` | Next due mistake for review |
| `POST /api/v1/review/sessions/{id}/submit` | Submit review rating |
| `GET /api/v1/stats/overview` | Dashboard KPIs |
| `GET /api/v1/ai/analyze/stream` | SSE AI analysis stream |
| `POST /api/v1/ai/generate-variant/{id}` | AI variant problem |
| `GET /api/v1/export/v3` | Full backup (schema_v3) |
| `POST /api/v1/import/v3` | Restore from schema_v3 |
| `POST /api/v1/import/problem-url/preview` | CF / LeetCode URL import |

### Quick auth examples

```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"secure-pass-123"}'
# Returns: {"access_token":"...", "token_type":"bearer", "user_id":2, "username":"alice"}

# Login (form-encoded)
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=alice&password=secure-pass-123'
```

## 🛠️ Development

### Backend

```bash
# Run all tests (from backend/)
.venv/bin/python -m pytest -q          # expected: 229 passed

# Format / lint
black app tests
flake8 app tests
```

### Frontend

```bash
npm test -- --run          # expected: 45 passed (10 files)
npm run type-check
npm run build
```

## 🔒 Security Notice

**Before any real deployment:**

1. Set `JWT_SECRET_KEY` to a random secret (`openssl rand -hex 32`).
2. Set `OLD_USER_INITIAL_PASSWORD` to a strong password and immediately change it after first login.
3. Set `APP_ENV=production` — the backend will refuse to start if the default JWT secret is used outside `development`/`test`.

See [`SECURITY.md`](SECURITY.md) for the full production security checklist.

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes
4. Open a Pull Request
