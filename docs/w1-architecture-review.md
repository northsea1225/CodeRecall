# W1 EOD 架构 Sanity Check（Claude 唯一一次审阅）

> 审阅范围：backend ORM / Alembic / API / services + frontend types / stores / api client / Monaco 封装
> 审阅时间：2026-04-18（W1 Day 5 EOD）
> 审阅结论：**✅ Ready for W2，但有 4 条阻塞项建议在 W2 Day 1 之前修掉**

---

## 🎯 总体判断

**质量超预期**。对比 W1 开工时的计划，数据模型已经预留了 SM-2 全部字段（ease_factor/interval_days/repetition/next_review_at），review_logs 表记录 old/new 前后值 — 这意味着 W3 做 SM-2 算法时**不用改 schema**，直接写 service 即可。这是 W1 最有价值的提前投资。

服务层有真正的抽象（service → repository → ORM 三层），错误处理通过 `raise_api_error` 统一格式，FK 级联规则设置正确，前端 zustand 分三个 store（mistake/draft/ui）边界清晰。意外收获：Codex 写了 3 个测试文件（form/api/mistakeStore），超出 W1 范围。

---

## 🚨 阻塞问题（W2 Day 1 前必修）

### BL-001 · 搜索关键词未接后端
- **现象**：`frontend/src/stores/mistakeStore.ts:12` 有 `keyword` 字段，但 `fetchList()` 没传给 service，且 `backend/app/api/routes/mistakes.py:21` 的 list endpoint 不接受 `keyword` 参数
- **影响**：W2 T02 "搜索" 是 W2 起手第一件事，不修就卡住
- **修复**：后端 `list_mistakes` 加 `keyword` 参数，在 `mistake_repo` 里对 `title/stem/wrong/correct/reason` 五字段做 `LIKE %keyword%`；前端把 `filters.keyword` 透传到 query
- **责任人**：Codex W2 Day 1

### BL-002 · Mistake.status 允许前端直接 PATCH
- **现象**：`backend/app/schemas/mistake.py:43` `MistakeUpdate.status` 可被任意修改；`backend/app/services/mistake_service.py:125` 直接写入
- **影响**：W3 SM-2 会根据复习结果驱动 status 状态机（new→learning→reviewing→mastered）。如果前端能手改，SM-2 规则会被破坏
- **修复**：从 `MistakeUpdate` 里移除 `status` 字段；W3 通过 review 接口驱动
- **责任人**：Codex W2 Day 1

### BL-003 · review_logs.user_result 是 String(50) 而非 Enum
- **现象**：`backend/app/models/review.py:51` 用 `String(50)` 存 `again/hard/good/easy`
- **影响**：W2 结尾开始写 SM-2 时，user_result 会变成热点字段，没有枚举约束会出脏数据
- **修复**：改为 SqlEnum(ReviewResult, native_enum=False)，加 Alembic 0002 迁移（空表改列安全）
- **责任人**：Codex W2 Day 1 或 W2 Day 结束 SM-2 开工前

### BL-004 · TD-003 未修：import 契约 skipped 语义不一致
- **现象**：`docs/api-contract-w1.md` 写 `skipped` 是计数，`backend/app/schemas/import_export.py:58` 返回 `list[ImportSkip]`
- **影响**：W2 如果要批量导入页，前端类型/契约不一致会返工
- **修复**：改契约文档对齐运行时实现（更便宜）
- **责任人**：Codex W2 Day 1（5 分钟）

---

## ⚠️ 高风险建议（W2 过程中处理）

### HR-001 · axios baseURL 硬编码
- `frontend/src/services/api.ts:41` 写死 `http://localhost:8000/api/v1`
- 不影响开发，但 W4 演示视频录制前要改成 `import.meta.env.VITE_API_BASE_URL`，加 `.env.development`

### HR-002 · JSON 导入导出无向前兼容
- `backend/app/services/import_export_service.py:104` 对 `version != "v1"` 硬抛 400
- W2+ 若 ImportMistake 字段增加，旧 v1 文件导不回来。建议：未知字段忽略、新字段用默认值，保持 v1 兼容
- 只有在 W2 真的要扩展 import 字段时才处理

### HR-003 · Mistake 表混合"内容"与"学习进度"
- 7 个字段（ease_factor / interval_days / repetition / next_review_at / review_count / last_reviewed_at / status）是"学习进度"，其余是"错题内容"
- 单人场景无问题。**做对了的地方**：`export_data()` 没导出这些进度字段（`import_export_service.py:71` 的 mistakes 列表），说明内容/进度分离的意识已经有了
- W4 如果想做"分享错题集"，需要拆 `mistake_progress` 表。**现在不改**

### HR-004 · Mistake status 枚举变更需全链路同步
- Pydantic enum → ORM SqlEnum → frontend union type 三处硬绑
- 加新状态值需同时改三处，加 Alembic 迁移。建议写到 `docs/handoff-w1-to-w2.md` 的"扩展时注意"清单

---

## 📎 可延后优化（记录即可）

| # | 位置 | 问题 | 修复成本 |
|---|---|---|---|
| DO-001 | `frontend/src/components/common/CodeEditor/index.tsx` | Monaco 首次加载 300ms 空白，无 loading fallback | 5min，W2 后期 |
| DO-002 | `backend/app/api/routes/categories.py` + `tags.py` | 列表无分页 | 中等，大规模导入后再说 |
| DO-003 | `frontend/src/stores/mistakeStore.ts:86` | `setFilter` 的 page 重置逻辑可读性差 | 5min 重构 |
| DO-004 | `backend/app/services/import_export_service.py:241` | `get_or_create_names` 名字误导（实际只 normalize） | 重命名 `normalize_tag_names_set` |
| DO-005 | Pydantic ↔ TS 类型手动维护 | 可用 openapi-ts 自动生成 | 大改造，W2+ 考虑 |

---

## ✅ 设计优秀点（避免 W2 破坏）

这些是 W1 沉淀下来的**正确选择**，W2 开发中不要无意识改掉：

1. **ImportMistake 用 `category_name` / `tag_names`（按名字，不按 id）** — `backend/app/schemas/import_export.py:14` 跨库迁移才可行，保留
2. **FK 级联规则**：mistakes→review_logs CASCADE（删错题清历史）、categories→mistakes RESTRICT（有引用不让删 ✓ taxonomy_service 409 处理过）、mistake_tags CASCADE（自动清理中间表）— 三种级联各自合理
3. **复合索引 `status+next_review_at`** — `backend/app/models/mistake.py:30` 直接支撑"到期优先"查询，W3 SM-2 会很快
4. **`ease_factor=2.5` / `interval_days=0` / `repetition=0` 默认值** — 符合 SM-2 初始值标准
5. **ApiClientError 保留 code/detail/status** — `frontend/src/services/api.ts:9` 前端能区分业务错误（如 `category_name_conflict` 409）和网络错误
6. **service → repository → ORM 三层** — `backend/app/services/mistake_service.py` 业务逻辑和 SQL 分离，W2+ 好测
7. **zustand 分三个 store** — `mistake/draft/ui` 边界清晰，不是一个全局大 store
8. **`MistakeRepository._base_query()`** — 导出页复用 base query，避免重复 eager load 写法

---

## 🔜 W2 起手清单（打包给 Codex）

建议 Codex W2 Day 1 第一条任务（30 分钟）：

```
1. 修 BL-004：改 docs/api-contract-w1.md 的 import response skipped 字段
2. 修 BL-002：MistakeUpdate 去掉 status
3. 修 BL-001：后端 list_mistakes 加 keyword 参数 + LIKE 多字段
4. 前端：mistakeStore.fetchList 接 keyword 到 mistakeService.listMistakes
5. 修 BL-003：review_logs.user_result 改 enum + Alembic 0002 迁移
6. smoke：跑一次 curl + tsc + build 三件套
```

搞定后 W2 正式主线：Review 流程页、随机抽题、答案核对、review_logs 写入。

---

## 📊 审阅消耗

- Claude 读取文件：约 16 个核心文件
- 发现问题：4 阻塞 + 4 高风险 + 5 可延后 = 13 条
- 按承诺，**W1 Claude 仅此一次审阅**，下次登场是 W2 末 SM-2 + AI 接入前
