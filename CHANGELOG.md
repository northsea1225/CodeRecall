# Changelog

All notable changes to CodeRecall are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Security (P0/P1 — must fix before production)
- **C1**: `old_user` default password `coderecall` is a publicly known backdoor
- **M1**: `APP_ENV` defaults to `development`, allowing default JWT secret on misconfiguration
- **M2**: SSE HTTP error path `body.detail` type guard broken (React crash on FastAPI 422)
- **M3**: Registration endpoint has no field length or character set constraints
- **M4**: v3 session dedup condition too weak (same-second same-strategy sessions may merge)
- **M-new**: Dashboard `Promise.all` crashes entire page if any single stat endpoint fails

---

## [0.2.0] - 2026-04-25

### Added
- **JWT user authentication** (Phase A + B): register / login / `GET /auth/me`, JWT signing (PyJWT 2.12.1), password hashing (passlib[bcrypt], bcrypt 4.0.1 pinned)
- **Per-user data isolation**: all business service layer functions scoped to `user_id`; per-user UUID unique index (migration 0008)
- **schema_v3 import/export**: full backup including `review_sessions` and `review_logs`; UUID-based cross-device dedup; `GET /export/v3` and `POST /import/v3`; three-layer idempotent import (session / item / log)
- **Codeforces URL import**: provider pattern (`providers/codeforces.py`); CF API + HTML parsing; MathJax formula handling; rating → difficulty mapping
- **Streak dashboard**: continuous review streak card (orange/green tiered color); review-completion toast at 7/30-day milestones; `streak_days` field in stats overview
- **Immersive dark room review mode**: `/review/immersive` full-screen route (outside AppLayout); `max-width: 900px`; fixed exit button
- **AI variant problem generation**: `POST /api/v1/ai/generate-variant/{id}` (JSON, not SSE); frontend `VariantDrawer`
- **Onboarding page**: full-screen first-use guide when mistake library is empty; URL importer + one-click demo data (4 classic C++ problems)
- **Algorithm capability radar chart**: `GET /api/v1/stats/tag-radar`; rendered with recharts in Stats page
- **Frontend SSE migration**: `useAiAnalysisStream.ts` rewritten with `fetch + ReadableStream + AbortController`; injects Bearer token; `event: error` dedicated path
- **Keyboard shortcuts in review**: `1/2/3/4` for SM-2 rating, `Space` to reveal answer
- **LaTeX rendering**: KaTeX for `$...$` and `$$...$$` in Markdown content
- **i18n additions**: `dashboard.streakDays`, `review.streakToast`, `review.streakMilestone7/30`, `review.enterImmersive`, `review.exitImmersive` (zh-CN + en-US)

### Changed
- All business API routes now require `Authorization: Bearer <token>` header
- Import/export v3 includes full review history (v1/v2 routes remain backward-compatible)
- `authStore` logout now clears `reviewStore` and `draftStore`
- Dashboard fetches 5 stat endpoints in parallel (`Promise.all`)
- AI routes: `selectinload(Mistake.review_logs)` added to eager-load review history for stage computation

### Security
- JWT fail-fast: backend raises `RuntimeError` on startup if `JWT_SECRET_KEY` is default outside `development`/`test`
- AI routes: removed `isinstance` fail-open pattern
- AI field length validation: Pydantic `Annotated` constraints in `mistake_constraints.py`

### Tests
- Backend: **160 passed** (including 8 cross-user isolation tests, 8 schema_v3 import/export tests)
- Frontend: **32 passed** (8 files)
- Alembic head: `0008`

---

## [0.1.0] - 2026-04-22

### Added
- **Mistake CRUD**: title, problem statement, error reason, correct solution, code diff (Monaco editor)
- **Categories and Tags**: hierarchical categorization with custom tags
- **SM-2 spaced repetition engine**: interval scheduling based on rating (again / hard / good / easy)
- **Review session tracking**: `ReviewSession` and `ReviewLog` models with full history
- **6-stage AI coaching**: `new_mistake` / `early_review` / `repeated_weakness` / `lapsed` / `oscillator` / `maintenance` stages; XML-structured prompts with `html.escape()` injection prevention
- **AI SSE analysis stream**: `GET /api/v1/ai/analyze/stream`; DeepSeek streaming integration
- **Dashboard statistics**: KPI cards, 30-day trend chart, activity heatmap, weak-area table
- **Import/Export v1/v2**: JSON backup/restore with category and tag preservation
- **LeetCode URL import**: `POST /api/v1/import/problem-url/preview`; httpx + LeetCode GraphQL + markdownify; CN/EN support
- **Light/Dark theme**: CSS variable tokens (`tokens.css`); full Ant Design 5 theme integration
- **Markdown + LaTeX rendering**: `MarkdownRenderer` component with KaTeX

### Infrastructure
- FastAPI + SQLAlchemy + SQLite + Alembic migrations (0001–0006)
- React 18 + TypeScript + Vite + Ant Design 5 + react-router-dom 7.1.x + Zustand 5
- pytest test suite; vitest frontend tests

---

## Migration Notes

### v1/v2 → v3 export
Old `/export` and `/import` routes remain fully backward-compatible. For new backups, use `/export/v3` to include complete review history.

### No-auth → JWT
All data created before the authentication system was added belongs to `old_user` (id=1). Set `OLD_USER_INITIAL_PASSWORD` before deployment and change the password immediately after first login.
