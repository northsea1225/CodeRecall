# Deployment Guide

This guide covers production deployment of CodeRecall / 码错本.

## Architecture

```
Browser
  │
  ▼
Reverse Proxy (nginx / Caddy)
  ├── /* → frontend/dist (static SPA)
  └── /api/v1/* , /auth/* → Backend :8000
                                │
                                ▼
                         FastAPI (uvicorn)
                                │
                                ▼
                          SQLite database
                                │
                         (optional) LLM API
```

## Requirements

| Component | Version |
|-----------|---------|
| Python | 3.9.6 |
| Node.js | 18+ |
| SQLite | 3.x (bundled with Python) |
| Reverse proxy | nginx ≥ 1.18 or Caddy 2 (SSE requires buffering disabled) |

## Backend Environment

Copy and edit `backend/.env.example`:

```bash
cp backend/.env.example backend/.env
```

Minimum production configuration:

```bash
APP_ENV=production
JWT_SECRET_KEY=$(openssl rand -hex 32)
OLD_USER_INITIAL_PASSWORD=<strong-random-password>
FRONTEND_ORIGIN=https://your-domain.com
DATABASE_URL=sqlite:////absolute/path/to/coderecall.db

# AI (optional — leave ENABLE_AI_ANALYSIS=false if not needed)
ENABLE_AI_ANALYSIS=false
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-v4-pro
LLM_MODEL_PREMIUM=deepseek-v4-pro
LLM_QUICK_MODEL=deepseek-v4-flash
LLM_API_KEY=<your-api-key>
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_ALLOWED_MODELS=deepseek-v4-pro,deepseek-v4-flash
```

## Backend Build & Start

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

For production, use a process manager (systemd, supervisor):

```ini
# /etc/systemd/system/coderecall.service
[Unit]
Description=CodeRecall Backend
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/coderecall/backend
EnvironmentFile=/opt/coderecall/backend/.env
ExecStart=/opt/coderecall/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

## Frontend Build

```bash
cd frontend
npm install
VITE_API_BASE_URL=https://your-domain.com/api/v1 npm run build
```

Output is in `frontend/dist/`. Serve this directory as static files.

## Reverse Proxy

### nginx

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    # Static SPA
    root /opt/coderecall/frontend/dist;
    index index.html;

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location ~ ^/(api/v1|auth)/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # SSE: disable buffering and set long timeout
        proxy_buffering off;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        chunked_transfer_encoding on;
    }
}
```

### Caddy

```
your-domain.com {
    handle /api/v1/* {
        reverse_proxy 127.0.0.1:8000 {
            flush_interval -1
        }
    }
    handle /auth/* {
        reverse_proxy 127.0.0.1:8000 {
            flush_interval -1
        }
    }
    handle {
        root * /opt/coderecall/frontend/dist
        try_files {path} /index.html
        file_server
    }
}
```

**Note:** `proxy_buffering off` (nginx) / `flush_interval -1` (Caddy) is required for AI SSE streaming to work correctly.

## Database & Backups

### File-level backup

```bash
# Stop or pause writes, then:
cp backend/coderecall.db backups/coderecall-$(date +%Y%m%d).db
```

### Application-level backup (recommended)

```bash
# Export full backup via API (requires authentication)
curl -H "Authorization: Bearer <token>" \
     https://your-domain.com/api/v1/export/v3 \
     -o backup-$(date +%Y%m%d).json
```

The `/export/v3` backup includes all mistakes, categories, tags, review sessions, and review logs. It is the recommended backup format for cross-device migration.

### Restore

```bash
curl -X POST \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d @backup-20260425.json \
     https://your-domain.com/api/v1/import/v3
```

### Database permissions

```bash
chmod 600 backend/coderecall.db
chown www-data:www-data backend/coderecall.db
```

## Initial User & Auth

After first deployment:

1. The backend automatically creates `old_user` (id=1) with the password set in `OLD_USER_INITIAL_PASSWORD`.
2. Log in as `old_user` and immediately change the password.
3. Register additional user accounts via `POST /auth/register`.

**Security note:** If `old_user` holds no data you need to preserve, consider setting `is_active=False` in the database to disable login while keeping data ownership.

## AI Configuration

AI analysis is disabled by default (`ENABLE_AI_ANALYSIS=false`). To enable:

1. Set `ENABLE_AI_ANALYSIS=true` in `.env`
2. Set `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_ALLOWED_MODELS`
3. Restart the backend
4. Verify SSE works:

```bash
curl -N -H "Authorization: Bearer <token>" \
     "https://your-domain.com/api/v1/ai/analyze/stream?mistake_id=1"
# Should stream: data: {"type":"chunk","content":"..."}
```

## Verification

```bash
# Health check (no auth required)
curl https://your-domain.com/health
# Expected: {"status":"ok","service":"CodeRecall API"}

# Auth check
TOKEN=$(curl -s -X POST https://your-domain.com/auth/token \
  -d "username=old_user&password=<your-password>" | jq -r .access_token)
curl -H "Authorization: Bearer $TOKEN" https://your-domain.com/auth/me

# Unauthenticated request must return 401
curl -s -o /dev/null -w "%{http_code}" https://your-domain.com/api/v1/mistakes
# Expected: 401

# Export v3 smoke test
curl -H "Authorization: Bearer $TOKEN" \
     https://your-domain.com/api/v1/export/v3 | jq .schema_version
# Expected: "v3"
```

## Rollback

```bash
# 1. Stop backend
systemctl stop coderecall

# 2. Restore database backup
cp backups/coderecall-<date>.db backend/coderecall.db

# 3. Downgrade Alembic (if schema changed)
cd backend && source .venv/bin/activate
alembic downgrade <previous-revision>

# 4. Restore previous frontend dist
# (keep a copy of frontend/dist before each deploy)

# 5. Restart
systemctl start coderecall
```

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Backend raises `RuntimeError` on startup | `JWT_SECRET_KEY` is default in production | Set `JWT_SECRET_KEY` to a random value |
| `401 Unauthorized` on all API calls | Token missing or expired | Re-login; check `ACCESS_TOKEN_EXPIRE_MINUTES` |
| CORS errors in browser | `FRONTEND_ORIGIN` mismatch | Match exact scheme, host, and port |
| AI SSE output cuts off immediately | Reverse proxy buffering enabled | Add `proxy_buffering off` to nginx config |
| AI endpoint returns 503 | `ENABLE_AI_ANALYSIS=false` or bad `LLM_API_KEY` | Check `.env` settings |
| SQLite `OperationalError: unable to open database` | Wrong path or permissions | Check `DATABASE_URL` and file permissions |
