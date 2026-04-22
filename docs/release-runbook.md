# CodeRecall Release Runbook

This runbook describes the baseline setup, release checks, and reset steps for CodeRecall (码迹).

## Prerequisites

- Python 3.11+
- Node.js 18+
- `uv` or `pip`
- A shell with access to the project root

## Backend Setup

From the project root:

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
.venv/bin/python ../scripts/seed_demo_data.py
```

If `python3.11` is not available as a command, use any Python 3.11+ interpreter:

```bash
python -m venv .venv
```

With `uv`, dependency installation can also be run as:

```bash
uv pip install -r requirements.txt
```

## Frontend Setup

From the project root:

```bash
cd frontend
npm install
npm run build
```

The frontend reads `VITE_API_BASE_URL` when present and otherwise defaults to `http://localhost:8000/api/v1`.

## Development Mode

Start the backend:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Start the frontend in another shell:

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173`. Backend API docs are available at `http://localhost:8000/docs`.

## Production Mode

Build the frontend:

```bash
cd frontend
npm run build
```

Run the backend without reload:

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Serve `frontend/dist` with the deployment web server or static hosting layer. Configure that layer to point API calls to the backend base URL.

## Environment Variables

Backend variables live in `backend/.env`; use `backend/.env.example` as the safe template.

| Variable | Required | Description |
| --- | --- | --- |
| `APP_NAME` | Yes | FastAPI display name and health endpoint service name. |
| `APP_ENV` | Yes | Runtime label such as `development`, `test`, or `production`. |
| `API_V1_PREFIX` | Yes | Prefix for versioned API routes. |
| `BACKEND_HOST` | Yes | Host interface used for local uvicorn commands. |
| `BACKEND_PORT` | Yes | Port used for local uvicorn commands. |
| `FRONTEND_ORIGIN` | Yes | Allowed CORS origin for the browser app. |
| `DATABASE_URL` | Yes | SQLAlchemy database URL, defaulting to local SQLite. |
| `ENABLE_AI_ANALYSIS` | Yes | Enables or disables AI analysis endpoints. |
| `LLM_PROVIDER` | Yes | Provider name for the AI analysis service. |
| `LLM_BASE_URL` | Yes | LLM provider or proxy base URL. |
| `LLM_MODEL` | Yes | Default model for normal AI analysis. |
| `LLM_MODEL_PREMIUM` | No | Optional higher-capability model for premium or demo flows. |
| `LLM_API_KEY` | Yes when AI is enabled | Secret API key for the LLM provider. Never commit a real value. |
| `LLM_ALLOWED_MODELS` | Yes | Comma-separated list of model IDs accepted from client requests. |

Frontend production deployments can set:

| Variable | Required | Description |
| --- | --- | --- |
| `VITE_API_BASE_URL` | No | API base URL used by the built frontend. Defaults to `http://localhost:8000/api/v1`. |

## Reset / Fresh Start

To rebuild local SQLite data from scratch:

```bash
cd backend
rm -f coderecall.db
source .venv/bin/activate
alembic upgrade head
.venv/bin/python ../scripts/seed_demo_data.py
```

The seed script clears and repopulates demo categories, tags, mistakes, and review logs for the configured `DATABASE_URL`.

## Verification Commands

Run the release baseline checks from the project root:

```bash
cd backend && .venv/bin/python -m pytest --tb=short -q
cd frontend && npm run test -- --run
cd frontend && npx tsc --noEmit
cd frontend && npm run build
```

Expected release baseline: pytest and vitest pass, TypeScript reports zero errors, and the frontend build succeeds.
