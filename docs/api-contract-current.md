# API Contract — Current

> This document is the authoritative reference for all current CodeRecall API endpoints.
> All versioned business routes are at `/api/v1`. Authentication routes are at `/auth`.
> Last updated: 2026-04-25 (reflects Alembic head 0008, auth Phase B complete)

## Conventions

- **Format**: JSON request/response bodies (except `/auth/token` which is `application/x-www-form-urlencoded`)
- **Dates**: ISO 8601 UTC (`2026-04-25T08:00:00Z`) or date strings (`2026-04-25`)
- **Pagination**: `page` (1-based) and `page_size` query parameters; response includes `total`, `page`, `page_size`, `items`
- **Authentication**: `Authorization: Bearer <token>` header required on all `/api/v1/*` routes
- **Errors**:
  ```json
  { "detail": "Error message" }
  ```
  Validation errors (422):
  ```json
  { "detail": [{ "type": "...", "loc": ["body", "field"], "msg": "..." }] }
  ```

---

## Auth

### `POST /auth/token`

Login. Body is `application/x-www-form-urlencoded`.

```
username=old_user&password=coderecall
```

Response `200 OK`:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

### `POST /auth/register`

Register a new user. Body is JSON.

```json
{ "username": "alice", "password": "strongpassword" }
```

Response `201 Created`:

```json
{ "id": 2, "username": "alice" }
```

### `GET /auth/me`

Returns the currently authenticated user.

Response `200 OK`:

```json
{ "id": 1, "username": "old_user" }
```

---

## Mistakes

All routes require `Authorization: Bearer <token>`. Data is scoped to the current user.

### `GET /api/v1/mistakes`

List mistakes with pagination and filtering.

Query parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number (1-based) |
| `page_size` | int | 20 | Items per page |
| `category_id` | int | — | Filter by category |
| `language` | string | — | Filter by programming language |
| `keyword` | string | — | Full-text search on title and content |
| `status` | string | — | `new` / `learning` / `reviewing` / `mastered` |

Response `200 OK`:

```json
{
  "total": 42,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "id": 1,
      "uuid": "550e8400-e29b-41d4-a716-446655440000",
      "title": "滑动窗口边界错位",
      "language": "cpp",
      "status": "reviewing",
      "category_id": 3,
      "category_name": "滑动窗口",
      "tags": ["贪心", "双指针"],
      "next_review_at": "2026-04-26T08:00:00Z",
      "created_at": "2026-04-20T10:00:00Z",
      "updated_at": "2026-04-25T14:00:00Z"
    }
  ]
}
```

### `POST /api/v1/mistakes`

Create a mistake.

```json
{
  "title": "线段树区间更新越界",
  "language": "cpp",
  "problem_statement": "...",
  "error_reason": "pushdown 时未判断叶节点",
  "correct_solution": "...",
  "code_diff": "...",
  "category_id": 5,
  "tag_ids": [1, 3]
}
```

Response `201 Created`: full mistake object.

### `GET /api/v1/mistakes/{id}`

Get mistake details including review log summary.

### `PUT /api/v1/mistakes/{id}`

Update mistake fields. Same body schema as POST (all fields optional).

### `DELETE /api/v1/mistakes/{id}`

Soft-delete (archive) a mistake. Response `204 No Content`.

---

## Categories

### `GET /api/v1/categories`

List all categories for the current user.

### `POST /api/v1/categories`

```json
{ "name": "动态规划" }
```

### `PUT /api/v1/categories/{id}`

### `DELETE /api/v1/categories/{id}`

---

## Tags

### `GET /api/v1/tags`

### `POST /api/v1/tags`

```json
{ "name": "背包DP" }
```

### `PUT /api/v1/tags/{id}`

### `DELETE /api/v1/tags/{id}`

---

## Review

### `POST /api/v1/review/sessions`

Start a new review session.

```json
{ "strategy": "due_first", "limit": 20 }
```

`strategy` values: `due_first` / `random` / `spaced_repetition`

Response `201 Created`:

```json
{ "session_id": "abc123", "total_items": 8 }
```

### `GET /api/v1/review/next`

Get the next item in the current session.

Response `200 OK`:

```json
{
  "mistake_id": 5,
  "title": "Dijkstra 负边处理",
  "language": "cpp",
  "problem_statement": "...",
  "position": 3,
  "total": 8
}
```

### `POST /api/v1/review/submit`

Submit a rating for the current item.

```json
{ "result": "good" }
```

`result` values: `again` / `hard` / `good` / `easy`

### `GET /api/v1/review/summary`

Get session summary (available after all items reviewed).

### `GET /api/v1/review/due-count`

```json
{ "due_today": 12 }
```

### `POST /api/v1/review/reveal`

Mark current item as revealed (for tracking purposes).

### `GET /api/v1/review/capability`

Get current review capability summary.

---

## Stats

All stats endpoints require authentication and are scoped to the current user.

### `GET /api/v1/stats/overview`

Query: `days` (default 7), `tz_offset_minutes` (default 0)

Response `200 OK`:

```json
{
  "as_of": "2026-04-25T09:30:00Z",
  "total_mistakes": 128,
  "active_mistakes": 121,
  "mastered_count": 34,
  "due_today": 12,
  "reviewed_today": 7,
  "reviewed_7d": 46,
  "avg_accuracy_7d": 0.72,
  "avg_ease_factor": 2.18,
  "streak_days": 5
}
```

### `GET /api/v1/stats/trend`

Query: `days` (default 30), `bucket` (default `day`), `tz_offset_minutes` (default 0)

### `GET /api/v1/stats/heatmap`

Query: `days` (default 90), `tz_offset_minutes` (default 0)

### `GET /api/v1/stats/top-weak`

Query: `limit` (default 5), `days` (default 30)

Returns the weakest mistakes ranked by `weak_score`.

### `GET /api/v1/stats/tag-radar`

Returns per-tag accuracy data for the algorithm capability radar chart.

---

## AI

AI endpoints require `ENABLE_AI_ANALYSIS=true` in backend config.

### `GET /api/v1/ai/analyze/stream`

SSE stream for AI deep analysis of a mistake.

Query: `mistake_id` (required)

SSE event format:

```
data: {"type": "chunk", "content": "分析文字..."}
data: {"type": "chunk", "content": "更多文字..."}
data: {"type": "done"}
```

Error event:

```
event: error
data: {"message": "Error description"}
```

Keepalive (sent every ~15s to prevent proxy timeout):

```
event: keepalive
data: {}
```

### `POST /api/v1/ai/generate-variant/{mistake_id}`

Generate a variant problem for practice. Returns JSON (not SSE).

Response `200 OK`:

```json
{
  "variant_title": "变体题标题",
  "variant_statement": "题面...",
  "hint": "提示...",
  "difficulty_note": "难度说明..."
}
```

---

## Import / Export

### Legacy (v1/v2)

#### `GET /api/v1/export`

Export mistakes, categories, and tags (no review history).

#### `POST /api/v1/import`

Import v1 or v2 format. Body: export JSON.

### Current (v3)

#### `GET /api/v1/export/v3`

Full backup including review sessions and review logs.

Response `200 OK`:

```json
{
  "schema_version": "v3",
  "exported_at": "2026-04-25T08:00:00Z",
  "categories": [...],
  "tags": [...],
  "mistakes": [
    {
      "uuid": "550e8400-...",
      "title": "...",
      "review_sessions": [
        {
          "session_uuid": "...",
          "strategy": "spaced_repetition",
          "started_at": "...",
          "ended_at": "...",
          "review_logs": [...]
        }
      ]
    }
  ]
}
```

#### `POST /api/v1/import/v3`

Import a v3 backup. Three-layer idempotent: sessions, items, and logs are each individually deduped by UUID.

---

## Problem URL Import

### `POST /api/v1/import/problem-url/preview`

Preview and extract a problem statement from a URL.

```json
{ "url": "https://leetcode.cn/problems/two-sum/" }
```

Supported sources: LeetCode (CN + EN), Codeforces (regular contests; Gym/private return a warning).

Response `200 OK`:

```json
{
  "title": "两数之和",
  "statement": "给定一个整数数组...",
  "source": "leetcode_cn",
  "difficulty": "Easy",
  "warning": null
}
```

Error types: `unsupported_provider` / `fetch_failed` / `parse_failed`

---

## Auth & User Isolation Notes

- Every `/api/v1/*` endpoint filters data by `current_user.id` — users cannot access each other's data.
- UUID deduplication for import is per-user (composite unique index on `(user_id, uuid)`).
- The `old_user` (id=1) owns all data created before authentication was added.

---

## curl Smoke Examples

```bash
# 1. Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"strongpass123"}'

# 2. Login
TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \
  -d "username=alice&password=strongpass123" | jq -r .access_token)

# 3. Current user
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/auth/me

# 4. Create mistake
curl -X POST http://localhost:8000/api/v1/mistakes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","language":"cpp","error_reason":"off-by-one"}'

# 5. Start review session
curl -X POST http://localhost:8000/api/v1/review/sessions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"strategy":"due_first","limit":10}'

# 6. Export v3 backup
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/v1/export/v3 -o backup.json
```
