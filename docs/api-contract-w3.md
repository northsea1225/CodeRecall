# CodeRecall API Contract W3

> W3 新增 Stats 契约，覆盖 `/api/v1/stats/*` 四个只读接口。

## Error Format

业务错误统一返回：

```json
{
  "code": "http_error",
  "message": "Request failed.",
  "detail": {}
}
```

参数校验错误返回：

```json
{
  "code": "validation_error",
  "message": "Request validation failed.",
  "detail": [
    {
      "type": "greater_than_equal",
      "loc": ["query", "days"],
      "msg": "Input should be greater than or equal to 1",
      "input": 0,
      "ctx": {
        "ge": 1
      }
    }
  ]
}
```

## `GET /api/v1/stats/overview`

Query

- `days`：默认 `7`
- `tz_offset_minutes`：默认 `0`

Response `200 OK`

```json
{
  "as_of": "2026-05-02T09:30:00Z",
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

`curl`

```bash
curl "http://localhost:8000/api/v1/stats/overview?days=7&tz_offset_minutes=480"
```

Schema

```json
{
  "as_of": "datetime",
  "total_mistakes": "int",
  "active_mistakes": "int",
  "mastered_count": "int",
  "due_today": "int",
  "reviewed_today": "int",
  "reviewed_7d": "int",
  "avg_accuracy_7d": "float",
  "avg_ease_factor": "float",
  "streak_days": "int"
}
```

## `GET /api/v1/stats/trend`

Query

- `days`：默认 `30`
- `bucket`：默认 `"day"`，W3 仅支持 `day`
- `tz_offset_minutes`：默认 `0`

Response `200 OK`

```json
{
  "range": {
    "from": "2026-04-07",
    "to": "2026-05-06",
    "bucket": "day"
  },
  "items": [
    {
      "date": "2026-05-01",
      "created_count": 2,
      "review_count": 8,
      "again_count": 2,
      "hard_count": 1,
      "good_count": 4,
      "easy_count": 1
    }
  ]
}
```

`curl`

```bash
curl "http://localhost:8000/api/v1/stats/trend?days=30&bucket=day&tz_offset_minutes=480"
```

Schema

```json
{
  "range": {
    "from": "date",
    "to": "date",
    "bucket": "\"day\""
  },
  "items": [
    {
      "date": "date",
      "created_count": "int",
      "review_count": "int",
      "again_count": "int",
      "hard_count": "int",
      "good_count": "int",
      "easy_count": "int"
    }
  ]
}
```

## `GET /api/v1/stats/heatmap`

Query

- `days`：默认 `90`
- `tz_offset_minutes`：默认 `0`

Response `200 OK`

```json
{
  "range": {
    "from": "2026-02-07",
    "to": "2026-05-06"
  },
  "max_count": 9,
  "cells": [
    {
      "date": "2026-05-01",
      "count": 6,
      "level": 3
    }
  ]
}
```

`curl`

```bash
curl "http://localhost:8000/api/v1/stats/heatmap?days=90&tz_offset_minutes=480"
```

Schema

```json
{
  "range": {
    "from": "date",
    "to": "date"
  },
  "max_count": "int",
  "cells": [
    {
      "date": "date",
      "count": "int",
      "level": "int(0-4)"
    }
  ]
}
```

## `GET /api/v1/stats/top-weak`

Query

- `limit`：默认 `5`
- `days`：默认 `30`

Response `200 OK`

```json
{
  "items": [
    {
      "mistake_id": 42,
      "title": "滑动窗口边界错位",
      "language": "javascript",
      "category_name": "滑动窗口",
      "status": "reviewing",
      "review_count": 5,
      "last_result": "again",
      "again_count": 2,
      "hard_count": 1,
      "next_review_at": "2026-05-01T08:00:00Z",
      "overdue_days": 1,
      "weak_score": 8.5
    }
  ]
}
```

## Import / Export

### `POST /api/v1/export`

Response `200 OK`

导出响应包含 `schema_version: "v2"`，同时保留 `version: "v1"` 作为接口主版本字段。

```json
{
  "version": "v1",
  "schema_version": "v2",
  "exported_at": "2026-04-20T08:00:00Z",
  "categories": [],
  "tags": [],
  "mistakes": []
}
```

### `POST /api/v1/import`

导入兼容两类文件：

- v1：无 `schema_version` 字段的旧导出文件。
- v2：包含 `schema_version: "v2"` 的新导出文件。

`version` 当前仍要求为 `"v1"`；`schema_version` 缺省时按 v1 兼容格式处理。

`curl`

```bash
curl "http://localhost:8000/api/v1/stats/top-weak?limit=5&days=30"
```

Schema

```json
{
  "items": [
    {
      "mistake_id": "int",
      "title": "string",
      "language": "string",
      "category_name": "string",
      "status": "\"new\" | \"learning\" | \"reviewing\" | \"mastered\"",
      "review_count": "int",
      "last_result": "\"again\" | \"hard\" | \"good\" | \"easy\" | null",
      "again_count": "int",
      "hard_count": "int",
      "next_review_at": "datetime | null",
      "overdue_days": "int",
      "weak_score": "float"
    }
  ]
}
```
