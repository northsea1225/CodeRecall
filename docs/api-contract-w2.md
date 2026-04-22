# CodeRecall API Contract W2

> W2 Review 契约独立维护，不覆盖 `docs/api-contract-w1.md`。

## ReviewResult Enum

实际字面量：

```json
["again", "hard", "good", "easy"]
```

## Error Format

业务错误统一返回：

```json
{
  "code": "review_session_not_found",
  "message": "Review Session not found.",
  "detail": {
    "review_session_id": 999
  }
}
```

FastAPI / Pydantic 参数校验错误保持默认结构：

```json
{
  "detail": [
    {
      "type": "enum",
      "loc": ["body", "user_result"],
      "msg": "Input should be 'again', 'hard', 'good' or 'easy'",
      "input": "mastered",
      "ctx": {
        "expected": "'again', 'hard', 'good' or 'easy'"
      }
    }
  ]
}
```

## Mistake Schema

W2 的 `MistakeOut` 会携带 review 进度字段，其中：

- `review_count` 表示该错题跨所有 review session 的累计总复习次数
- 当前单个 session 内已完成多少题，请看 `ReviewSession.completed_count`，不要把两者混用

## Review Session

### `POST /api/v1/review/sessions`

开始新的 Review session，当前仅支持 `random`。

Request

```json
{
  "strategy": "random",
  "limit": 10
}
```

Response `201 Created`

```json
{
  "id": 1,
  "strategy": "random",
  "started_at": "2026-04-25T08:00:00Z",
  "total_count": 10,
  "completed_count": 0,
  "next_item": {
    "mistake_id": 12,
    "title": "两数之和遗漏补数判断",
    "stem_markdown": "给定数组 nums 和 target。",
    "language": "python",
    "difficulty": 2,
    "category_name": "哈希表",
    "tag_names": ["哈希", "边界条件"],
    "shown_at": "2026-04-25T08:00:01Z"
  }
}
```

Response `201 Created`（当前无可复习题）

```json
{
  "id": 2,
  "strategy": "random",
  "started_at": "2026-04-25T08:10:00Z",
  "total_count": 0,
  "completed_count": 0,
  "next_item": null
}
```

`curl`

```bash
curl -X POST http://localhost:8000/api/v1/review/sessions \
  -H "Content-Type: application/json" \
  -d '{"strategy":"random","limit":10}'
```

### `GET /api/v1/review/sessions/{session_id}/next`

返回当前 session 的下一题。`next_item: null` 表示会话完成或本次无题。

Response `200 OK`

```json
{
  "next_item": {
    "mistake_id": 13,
    "title": "滑动窗口收缩条件错位",
    "stem_markdown": "给定字符串 s 和 t。",
    "language": "javascript",
    "difficulty": 3,
    "category_name": "滑动窗口",
    "tag_names": ["窗口"],
    "shown_at": "2026-04-25T08:02:00Z"
  },
  "progress": {
    "completed": 1,
    "total": 10
  }
}
```

Response `200 OK`（已完成）

```json
{
  "next_item": null,
  "progress": {
    "completed": 10,
    "total": 10
  }
}
```

Response `404 Not Found`

```json
{
  "code": "review_session_not_found",
  "message": "Review Session not found.",
  "detail": {
    "review_session_id": 999
  }
}
```

`curl`

```bash
curl http://localhost:8000/api/v1/review/sessions/1/next
```

### `POST /api/v1/review/sessions/{session_id}/submit`

提交本题结果。W2 Day 3 仅写 `review_logs`，并同步更新 `session.completed_count`。同一 `(session_id, mistake_id)` 重复提交时返回已有 log，不重复写入。

Request

```json
{
  "mistake_id": 13,
  "user_result": "good",
  "time_spent_ms": 42000,
  "note": "第二次就想起来了"
}
```

Response `200 OK`

```json
{
  "id": 5,
  "mistake_id": 13,
  "session_id": 1,
  "review_mode": "random",
  "user_result": "good",
  "shown_at": "2026-04-25T08:02:42Z",
  "answered_at": "2026-04-25T08:02:42Z",
  "note": "第二次就想起来了",
  "progress": {
    "completed": 2,
    "total": 10
  }
}
```

Response `200 OK`（重复提交，幂等返回已有记录）

```json
{
  "id": 5,
  "mistake_id": 13,
  "session_id": 1,
  "review_mode": "random",
  "user_result": "good",
  "shown_at": "2026-04-25T08:02:42Z",
  "answered_at": "2026-04-25T08:02:42Z",
  "note": "第二次就想起来了",
  "progress": {
    "completed": 2,
    "total": 10
  }
}
```

Response `422 Unprocessable Entity`（题目不在当前 session 队列）

```json
{
  "code": "mistake_not_in_session",
  "message": "Mistake is not part of this review session.",
  "detail": {
    "session_id": 1,
    "mistake_id": 999
  }
}
```

Response `422 Unprocessable Entity`（`user_result` 非法）

```json
{
  "detail": [
    {
      "type": "enum",
      "loc": ["body", "user_result"],
      "msg": "Input should be 'again', 'hard', 'good' or 'easy'",
      "input": "mastered",
      "ctx": {
        "expected": "'again', 'hard', 'good' or 'easy'"
      }
    }
  ]
}
```

`curl`

```bash
curl -X POST http://localhost:8000/api/v1/review/sessions/1/submit \
  -H "Content-Type: application/json" \
  -d '{"mistake_id":13,"user_result":"good","time_spent_ms":42000,"note":"第二次就想起来了"}'
```

### `GET /api/v1/review/sessions/{session_id}/summary`

完成后读取统计。

Response `200 OK`

```json
{
  "total_count": 10,
  "completed_count": 10,
  "result_counts": {
    "again": 2,
    "hard": 1,
    "good": 5,
    "easy": 2
  },
  "duration_ms": 240000
}
```

Response `404 Not Found`

```json
{
  "code": "review_session_not_found",
  "message": "Review Session not found.",
  "detail": {
    "review_session_id": 999
  }
}
```

`curl`

```bash
curl http://localhost:8000/api/v1/review/sessions/1/summary
```

### `GET /api/v1/review/capability`

Day 3 固定返回 AI 分析不可用，Day 4 再接 feature flag。

Response `200 OK`

```json
{
  "ai_analysis_enabled": false
}
```

`curl`

```bash
curl http://localhost:8000/api/v1/review/capability
```

## Review Item Reveal

### `GET /api/v1/review/items/{mistake_id}/reveal`

显示答案时再拉完整内容，避免题面接口泄露答案字段。

Response `200 OK`

```json
{
  "mistake_id": 13,
  "title": "滑动窗口收缩条件错位",
  "stem_markdown": "给定字符串 s 和 t。",
  "wrong_answer_markdown": "left += 1",
  "correct_answer_markdown": "while matched == need: ...",
  "error_reason_markdown": "窗口收缩条件错了。",
  "language": "javascript",
  "difficulty": 3,
  "category_name": "滑动窗口",
  "tag_names": ["窗口"]
}
```

Response `404 Not Found`

```json
{
  "code": "mistake_not_found",
  "message": "Mistake not found.",
  "detail": {
    "mistake_id": 999
  }
}
```

`curl`

```bash
curl http://localhost:8000/api/v1/review/items/13/reveal
```
