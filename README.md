# CodeRecall / 码错本

![Python 3.9.6](https://img.shields.io/badge/Python-3.9.6-blue.svg)
![Node 18+](https://img.shields.io/badge/Node-18%2B-green.svg)
![pytest](https://img.shields.io/badge/pytest-165%20passed-success.svg)
![vitest](https://img.shields.io/badge/vitest-32%20passed-success.svg)

**CodeRecall / 码错本** is an intelligent, spaced-repetition programming mistake notebook for OI/ACM/LeetCode competitors. Core differentiators: 6-stage dynamic AI coaching (adapts to your review history, not generic replies) + SM-2 forgetting-curve scheduling + one-click LeetCode/Codeforces import.

Core loop: **Import problem → Record mistake → SM-2 scheduled review → 6-stage dynamic AI deep analysis**

## ✨ Features

- **Spaced Repetition (SM-2):** Optimized review scheduling for long-term retention.
- **6-Stage AI Coaching:** Dynamic prompts adapt to your review stage (`new_mistake` / `early_review` / `repeated_weakness` / `lapsed` / `oscillator` / `maintenance`).
- **JWT User Auth & Data Isolation:** Secure per-user data with Bearer token authentication.
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
   pytest tests/ -q                                                    # 165 passed
   pip-audit --strict --requirement requirements.txt \
     --ignore-vuln GHSA-wp53-j4wj-2cfg --ignore-vuln GHSA-mj87-hwqh-73pj \
     --ignore-vuln GHSA-mf9w-mj56-hr94 --ignore-vuln GHSA-6w46-j5rx-g56g
   ```

`requirements.txt` is generated — **do not edit it by hand**. Accepted CVEs (Python 3.9 constraint) are documented in [`SECURITY.md`](SECURITY.md#accepted-cves-python-39-constraint).

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
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime (minutes) | `10080` (7 days) |
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

All versioned routes are at `/api/v1`. Auth routes at `/auth/*`. Full reference: [`docs/api-contract-current.md`](docs/api-contract-current.md).

| Route | Description |
|-------|-------------|
| `POST /auth/token` | Login (form-encoded) |
| `POST /auth/register` | Register new user |
| `GET /auth/me` | Current user info |
| `GET /api/v1/mistakes` | List mistakes (paginated, filterable) |
| `POST /api/v1/mistakes` | Create mistake |
| `GET /api/v1/review/next` | Next due mistake for review |
| `POST /api/v1/review/submit` | Submit review rating |
| `GET /api/v1/stats/overview` | Dashboard KPIs |
| `GET /api/v1/ai/analyze/stream` | SSE AI analysis stream |
| `POST /api/v1/ai/generate-variant/{id}` | AI variant problem |
| `GET /api/v1/export/v3` | Full backup (schema_v3) |
| `POST /api/v1/import/v3` | Restore from schema_v3 |
| `POST /api/v1/import/problem-url/preview` | CF / LeetCode URL import |

## 🛠️ Development

### Backend

```bash
# Run all tests (from backend/)
.venv/bin/python -m pytest -q          # expected: 165 passed

# Format / lint
black app tests
flake8 app tests
```

### Frontend

```bash
npm test -- --run          # expected: 32 passed (8 files)
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
