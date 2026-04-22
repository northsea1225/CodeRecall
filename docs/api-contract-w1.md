# CodeRecall W1 API Contract

> 范围仅覆盖 W1 Day 1 约定：`mistakes`、`categories`、`tags`、`import/export`，不包含搜索、Review、SM-2、统计或 AI 逻辑。

## 统一约定

- Base URL：`http://localhost:8000/api/v1`
- Content-Type：`application/json`
- 时间字段：ISO 8601 UTC 字符串
- 列表接口默认按 `created_at desc`

## 统一错误格式

```json
{
  "code": "mistake_not_found",
  "message": "Mistake not found.",
  "detail": {
    "mistake_id": 42
  }
}
```

## 数据对象

### Category

```json
{
  "id": 1,
  "name": "动态规划",
  "description": "DP / 状态转移类题目",
  "created_at": "2026-04-18T08:00:00Z",
  "updated_at": "2026-04-18T08:00:00Z"
}
```

### Tag

```json
{
  "id": 1,
  "name": "边界条件",
  "created_at": "2026-04-18T08:00:00Z",
  "updated_at": "2026-04-18T08:00:00Z"
}
```

### Mistake

```json
{
  "id": 101,
  "title": "两数之和遗漏重复元素边界",
  "stem_markdown": "给定数组 `nums` 和目标值 `target`。",
  "wrong_answer_markdown": "```python\nfor i in range(len(nums)):\n    if nums[i] + nums[i + 1] == target:\n        return [i, i + 1]\n```",
  "correct_answer_markdown": "```python\nseen = {}\nfor i, value in enumerate(nums):\n    if target - value in seen:\n        return [seen[target - value], i]\n    seen[value] = i\n```",
  "error_reason_markdown": "没有处理任意位置配对，只判断了相邻元素。",
  "language": "python",
  "difficulty": 2,
  "source": "LeetCode",
  "status": "new",
  "category": {
    "id": 1,
    "name": "哈希表",
    "description": "查找与映射"
  },
  "tags": [
    {
      "id": 1,
      "name": "边界条件"
    },
    {
      "id": 2,
      "name": "数据结构选择"
    }
  ],
  "created_at": "2026-04-18T08:00:00Z",
  "updated_at": "2026-04-18T08:00:00Z"
}
```

## Mistakes CRUD

### `GET /mistakes`

#### Response `200`

```json
{
  "items": [
    {
      "id": 101,
      "title": "两数之和遗漏重复元素边界",
      "stem_markdown": "给定数组 `nums` 和目标值 `target`。",
      "wrong_answer_markdown": "错误代码片段",
      "correct_answer_markdown": "正确代码片段",
      "error_reason_markdown": "没有处理任意位置配对。",
      "language": "python",
      "difficulty": 2,
      "source": "LeetCode",
      "status": "new",
      "category": {
        "id": 1,
        "name": "哈希表",
        "description": "查找与映射"
      },
      "tags": [
        {
          "id": 1,
          "name": "边界条件"
        }
      ],
      "created_at": "2026-04-18T08:00:00Z",
      "updated_at": "2026-04-18T08:00:00Z"
    }
  ],
  "total": 1
}
```

### `POST /mistakes`

#### Request

```json
{
  "title": "两数之和遗漏重复元素边界",
  "stem_markdown": "给定数组 `nums` 和目标值 `target`。",
  "wrong_answer_markdown": "错误代码片段",
  "correct_answer_markdown": "正确代码片段",
  "error_reason_markdown": "没有处理任意位置配对。",
  "language": "python",
  "difficulty": 2,
  "source": "LeetCode",
  "status": "new",
  "category_id": 1,
  "tag_ids": [1, 2]
}
```

#### Response `201`

```json
{
  "id": 101,
  "title": "两数之和遗漏重复元素边界",
  "stem_markdown": "给定数组 `nums` 和目标值 `target`。",
  "wrong_answer_markdown": "错误代码片段",
  "correct_answer_markdown": "正确代码片段",
  "error_reason_markdown": "没有处理任意位置配对。",
  "language": "python",
  "difficulty": 2,
  "source": "LeetCode",
  "status": "new",
  "category": {
    "id": 1,
    "name": "哈希表",
    "description": "查找与映射"
  },
  "tags": [
    {
      "id": 1,
      "name": "边界条件"
    },
    {
      "id": 2,
      "name": "数据结构选择"
    }
  ],
  "created_at": "2026-04-18T08:00:00Z",
  "updated_at": "2026-04-18T08:00:00Z"
}
```

### `GET /mistakes/{id}`

#### Response `200`

```json
{
  "id": 101,
  "title": "两数之和遗漏重复元素边界",
  "stem_markdown": "给定数组 `nums` 和目标值 `target`。",
  "wrong_answer_markdown": "错误代码片段",
  "correct_answer_markdown": "正确代码片段",
  "error_reason_markdown": "没有处理任意位置配对。",
  "language": "python",
  "difficulty": 2,
  "source": "LeetCode",
  "status": "new",
  "category": {
    "id": 1,
    "name": "哈希表",
    "description": "查找与映射"
  },
  "tags": [
    {
      "id": 1,
      "name": "边界条件"
    }
  ],
  "created_at": "2026-04-18T08:00:00Z",
  "updated_at": "2026-04-18T08:00:00Z"
}
```

### `PATCH /mistakes/{id}`

#### Request

```json
{
  "title": "两数之和：重复元素与边界遗漏",
  "error_reason_markdown": "忽略了任意位置的补数匹配。",
  "difficulty": 3,
  "category_id": 3,
  "tag_ids": [1, 3]
}
```

#### Response `200`

```json
{
  "id": 101,
  "title": "两数之和：重复元素与边界遗漏",
  "stem_markdown": "给定数组 `nums` 和目标值 `target`。",
  "wrong_answer_markdown": "错误代码片段",
  "correct_answer_markdown": "正确代码片段",
  "error_reason_markdown": "忽略了任意位置的补数匹配。",
  "language": "python",
  "difficulty": 3,
  "source": "LeetCode",
  "status": "new",
  "category": {
    "id": 3,
    "name": "数组",
    "description": "数组与双指针"
  },
  "tags": [
    {
      "id": 1,
      "name": "边界条件"
    },
    {
      "id": 3,
      "name": "哈希表"
    }
  ],
  "created_at": "2026-04-18T08:00:00Z",
  "updated_at": "2026-04-18T09:00:00Z"
}
```

### `DELETE /mistakes/{id}`

#### Response `200`

```json
{
  "id": 101,
  "deleted": true
}
```

## Categories CRUD

### `GET /categories`

#### Response `200`

```json
{
  "items": [
    {
      "id": 1,
      "name": "动态规划",
      "description": "DP / 状态转移类题目",
      "created_at": "2026-04-18T08:00:00Z",
      "updated_at": "2026-04-18T08:00:00Z"
    }
  ],
  "total": 1
}
```

### `POST /categories`

#### Request

```json
{
  "name": "动态规划",
  "description": "DP / 状态转移类题目"
}
```

#### Response `201`

```json
{
  "id": 1,
  "name": "动态规划",
  "description": "DP / 状态转移类题目",
  "created_at": "2026-04-18T08:00:00Z",
  "updated_at": "2026-04-18T08:00:00Z"
}
```

### `GET /categories/{id}`

#### Response `200`

```json
{
  "id": 1,
  "name": "动态规划",
  "description": "DP / 状态转移类题目",
  "created_at": "2026-04-18T08:00:00Z",
  "updated_at": "2026-04-18T08:00:00Z"
}
```

### `PATCH /categories/{id}`

#### Request

```json
{
  "name": "动态规划 DP",
  "description": "适合状态转移和记忆化搜索的问题"
}
```

#### Response `200`

```json
{
  "id": 1,
  "name": "动态规划 DP",
  "description": "适合状态转移和记忆化搜索的问题",
  "created_at": "2026-04-18T08:00:00Z",
  "updated_at": "2026-04-18T09:00:00Z"
}
```

### `DELETE /categories/{id}`

#### Response `200`

```json
{
  "id": 1,
  "deleted": true
}
```

## Tags CRUD

### `GET /tags`

#### Response `200`

```json
{
  "items": [
    {
      "id": 1,
      "name": "边界条件",
      "created_at": "2026-04-18T08:00:00Z",
      "updated_at": "2026-04-18T08:00:00Z"
    }
  ],
  "total": 1
}
```

### `POST /tags`

#### Request

```json
{
  "name": "边界条件"
}
```

#### Response `201`

```json
{
  "id": 1,
  "name": "边界条件",
  "created_at": "2026-04-18T08:00:00Z",
  "updated_at": "2026-04-18T08:00:00Z"
}
```

### `GET /tags/{id}`

#### Response `200`

```json
{
  "id": 1,
  "name": "边界条件",
  "created_at": "2026-04-18T08:00:00Z",
  "updated_at": "2026-04-18T08:00:00Z"
}
```

### `PATCH /tags/{id}`

#### Request

```json
{
  "name": "边界条件检查"
}
```

#### Response `200`

```json
{
  "id": 1,
  "name": "边界条件检查",
  "created_at": "2026-04-18T08:00:00Z",
  "updated_at": "2026-04-18T09:00:00Z"
}
```

### `DELETE /tags/{id}`

#### Response `200`

```json
{
  "id": 1,
  "deleted": true
}
```

## Import / Export

### `POST /import`

#### Request

```json
{
  "version": "v1",
  "categories": [
    {
      "name": "哈希表",
      "description": "查找与映射"
    }
  ],
  "tags": [
    {
      "name": "边界条件"
    }
  ],
  "mistakes": [
    {
      "title": "两数之和遗漏重复元素边界",
      "stem_markdown": "给定数组 `nums` 和目标值 `target`。",
      "wrong_answer_markdown": "错误代码片段",
      "correct_answer_markdown": "正确代码片段",
      "error_reason_markdown": "没有处理任意位置配对。",
      "language": "python",
      "difficulty": 2,
      "source": "LeetCode",
      "status": "new",
      "category_name": "哈希表",
      "tag_names": ["边界条件"]
    }
  ]
}
```

#### Response `200`

```json
{
  "version": "v1",
  "imported": {
    "categories": 1,
    "tags": 1,
    "mistakes": 1
  },
  "skipped": [
    {
      "entity": "mistake",
      "identifier": "两数之和遗漏重复元素边界",
      "reason": "already_exists"
    }
  ]
}
```

### `POST /export`

#### Request

```json
{
  "version": "v1"
}
```

#### Response `200`

```json
{
  "version": "v1",
  "exported_at": "2026-04-18T08:00:00Z",
  "categories": [
    {
      "name": "哈希表",
      "description": "查找与映射"
    }
  ],
  "tags": [
    {
      "name": "边界条件"
    }
  ],
  "mistakes": [
    {
      "title": "两数之和遗漏重复元素边界",
      "stem_markdown": "给定数组 `nums` 和目标值 `target`。",
      "wrong_answer_markdown": "错误代码片段",
      "correct_answer_markdown": "正确代码片段",
      "error_reason_markdown": "没有处理任意位置配对。",
      "language": "python",
      "difficulty": 2,
      "source": "LeetCode",
      "status": "new",
      "category_name": "哈希表",
      "tag_names": ["边界条件"]
    }
  ]
}
```
