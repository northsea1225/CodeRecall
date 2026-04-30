# Codex 全栈审阅报告 — CodeRecall（2026-04-29）

## 0. 执行摘要
- **总体评分**: C（测试全绿且主链路可用，但运行时契约、数据边界和性能债务已经开始互相放大）
- **总问题数**: Critical 0 · High 2 · Medium 8 · Low 5
- **Top 5 风险**（按严重度排序，列文件:行）
  - `backend/app/db/init_db.py:36`：Alembic 失败被吞掉并回退 `create_all()`，会把真实迁移故障伪装成“启动成功”
  - `docs/api-contract-current.md:4`、`README.md:100`、`docs/deployment-guide.md:13`：公开文档与真实路由/响应结构严重漂移
  - `backend/app/services/import_export_service.py:67`、`backend/app/services/stats_service.py:79`、`backend/app/services/review/__init__.py:37`：user-scoped service 仍保留 `user_id=None`
  - `backend/app/services/review/__init__.py:88`：`GET /review/...` 读接口会写 `completed_count` / `ended_at`
  - `backend/app/services/stats_service.py:79`：统计接口仍在全量拉表后做 Python 内存聚合
- **审阅者视角**：最有价值的发现不是单点 bug，而是“运行时真相”与“外部契约”正在分叉。最典型的两个信号是：一方面 review 的 `GET` 接口在悄悄写库，另一方面迁移失败又会被自动兜底掩盖；这类问题很难被常规 happy-path 测试发现，但会在上线后制造最难排查的状态漂移。

## 1. 维度评分总览

| 维度 | 得分 | 关键发现 |
|------|------|----------|
| 安全 | C | `authStore` 本地状态可被全量注入；user-scoped service 仍保留 `user_id=None` 后门路径；token 仍在 `localStorage` |
| 质量 | C | 前后端校验不一致；taxonomy 缺少长度约束；多处硬编码文案绕过 i18n |
| 架构 | C | review 读接口带副作用；service/repository 边界不稳；迁移失败兜底策略会掩盖系统状态 |
| 性能 | C | stats 全量拉表；前端构建 chunk/worker 明显超阈值；动态 import 因路由耦合失效 |
| UX | C | Dashboard 关键列表仍不可导航；review 完成 toast 仍可能产生未处理 rejection；多处文案未国际化 |
| 文档 | D | API、代理路径、返回结构、开发命令与现状多处不一致 |
| 测试 | B | 后端 160 / 前端 32 全绿，但关键隔离/导入测试绕过 Alembic，前端缺少页面级与 E2E 覆盖 |

## 2. Critical 问题（上线阻塞 / 数据泄露 / 安全漏洞）

无 Critical 问题。

## 3. High 问题（本周修复）

### [H-001] Alembic 失败被自动吞掉并回退到 `create_all()`
- **维度**: 架构 / 稳定性
- **文件**: `backend/app/db/init_db.py:36`
- **问题描述**: `initialize_database()` 对 `command.upgrade(..., "head")` 做了宽泛的 `except Exception`，随后直接 `logger.warning(...)` 并执行 `_create_all(target_url)`。这会把“迁移失败”降级成“继续启动”，尤其在已有库升级失败时，应用可能运行在旧 schema 上。
  ```py
  try:
      command.upgrade(_build_alembic_config(target_url), "head")
  except Exception as exc:
      logger.warning("Alembic migration failed, falling back to create_all: %s", exc)
      _create_all(target_url)
  ```
- **影响**: 真实 schema 漂移、缺索引、缺约束或列缺失都可能被掩盖；最坏情况下表现为“应用启动成功但数据行为异常”。
- **复现路径**: 让任意 Alembic migration 抛异常（例如 revision 语法错、已有库状态不匹配），调用 `initialize_database()`；代码会记录 warning 后继续执行。
- **修复建议**: 仅在“确定是全新空库且 migration 基础设施不可用”时才允许 fallback；对已有数据库一律 fail-fast。
  ```py
  try:
      command.upgrade(...)
  except Exception:
      if should_bootstrap_empty_db(target_url):
          _create_all(target_url)
      else:
          raise
  ```
- **预估工时**: 2 小时

### [H-002] 公开 API / 部署文档与真实运行契约严重漂移
- **维度**: 文档 / 交付
- **文件**: `README.md:100`, `docs/api-contract-current.md:4`, `docs/api-contract-current.md:26`, `docs/deployment-guide.md:13`, `backend/app/api/routes/auth.py:43`, `backend/app/api/routes/review.py:26`
- **问题描述**: 文档把认证路由写成 `/auth/*`，而运行时代码实际挂在 `/api/v1/auth/*`；文档示例还把 `register` 响应写成 `201 Created + {id, username}`，实际代码返回 `200 + access_token/username/user_id`。README 中的 review 端点 `GET /api/v1/review/next` / `POST /api/v1/review/submit` 也已经不存在。
- **影响**: 新客户端、curl smoke、反向代理、第三方集成会按错误契约接入，直接得到 404 或响应字段不匹配。
- **复现路径**: 按 `docs/api-contract-current.md:429-438` 或 `README.md:104-110` 的 curl 示例调用即可；真实测试使用的是 `/api/v1/auth/*`（`backend/tests/test_cross_user_isolation.py:56-60`）。
- **修复建议**: 以 FastAPI OpenAPI 为单一事实源，重新生成 auth/review/import-export 文档；把 README、部署文档、runbook 的示例命令统一到 `/api/v1/auth/*` 与当前 response schema。
- **预估工时**: 4 小时

## 4. Medium 问题（本迭代修复）

### [M-001] `initializeAuth()` 将任意本地 JSON 全量并入 Zustand 状态
- **维度**: 安全
- **文件**: `frontend/src/stores/authStore.ts:35`
- **问题描述**: 代码对 `localStorage` 里的对象只做了 `token/userId` 存在性判断，随后直接 `set(parsed)`。任何额外字段都会被并入 auth store。
  ```ts
  if (typeof exp === "number" && exp * 1000 > Date.now()) {
    set(parsed);
    return;
  }
  ```
- **影响**: 被篡改的本地状态可注入非预期字段，制造 UI 级权限/身份混乱，且会放大任何 XSS 或浏览器扩展篡改的影响面。
- **复现路径**: 手动写入 `localStorage.coderecall_token = {"token":"...","userId":1,"username":"a","role":"admin"}`，刷新后该对象会整体写入 store。
- **修复建议**: 只白名单回填 `token` / `username` / `userId`，并校验类型。
  ```ts
  set({
    token: typeof parsed.token === "string" ? parsed.token : null,
    username: typeof parsed.username === "string" ? parsed.username : null,
    userId: typeof parsed.userId === "number" ? parsed.userId : null,
  });
  ```
- **预估工时**: 1 小时

### [M-002] user-scoped service 仍保留 `user_id=None` 越权调用面
- **维度**: 安全 / 架构
- **文件**: `backend/app/services/import_export_service.py:67`, `backend/app/services/stats_service.py:79`, `backend/app/services/review/__init__.py:37`, `backend/app/services/review/selector.py:19`, `backend/app/services/review/recorder.py:14`, `backend/app/services/review/progress_updater.py:31`
- **问题描述**: 多个“按用户隔离”的 service 仍把 `user_id` 设计为可选，并在为空时退化成全量查询/写入。
- **影响**: 当前路由层虽然显式传了 `current_user.id`，但脚本、后台任务、REPL、未来管理接口一旦误调这些 service，就会绕过所有者过滤。
- **复现路径**: 在 shell / 脚本里直接调用 `get_overview(db)`、`export_data_v3(db)`、`_get_session(db, session_id)` 等函数，即可进入无 owner filter 分支。
- **修复建议**: 对 user-scoped 函数把 `user_id` 改成必填；确需全局能力时拆出 `*_for_admin()` / `*_global()` 明确命名。
- **预估工时**: 4 小时

### [M-003] Review 的 GET 接口存在隐藏写操作
- **维度**: 架构 / 可维护性
- **文件**: `backend/app/services/review/__init__.py:88`, `backend/app/services/review/__init__.py:97`, `backend/app/services/review/__init__.py:150`, `backend/app/services/review/__init__.py:204`
- **问题描述**: `_progress_for_session()` 会在 GET 过程中 `commit()` `session.completed_count`；`_mark_session_completed_if_needed()` 会在 `get_next_item()` / `get_summary()` 的 GET 请求里写 `ended_at`。
- **影响**: 读接口不再幂等，预取/重试/缓存探测都可能改写 session；后续接入 CDN、APM replay 或前端自动重试时很容易出现“只是读了一次 summary 却把 session 关掉”的隐式状态变更。
- **复现路径**: 完成最后一道题后调用 `GET /api/v1/review/sessions/{id}/summary`，数据库中的 `review_sessions.ended_at` 会在该 GET 内被更新。
- **修复建议**: 把 `completed_count` / `ended_at` 更新移动到 `submit_result()`；GET 只做只读聚合，或引入显式 `POST /review/sessions/{id}/finalize`。
- **预估工时**: 3 小时

### [M-004] 统计接口仍在全量拉表后做 Python 内存聚合
- **维度**: 性能
- **文件**: `backend/app/services/stats_service.py:79`, `backend/app/services/stats_service.py:145`, `backend/app/services/stats_service.py:193`
- **问题描述**: `get_overview()` / `get_trend()` / `get_heatmap()` 都先把 `Mistake` / `ReviewLog` 全量读进内存，再做日期窗口和计数。
- **影响**: 数据量上来后，接口延迟、内存占用和 SQLite I/O 都会线性增长；这是当前后端最明显的性能热点。
- **复现路径**: 阅读实现即可确认 `db.scalars(select(Mistake)...).all()` 与 `db.scalars(select(ReviewLog)...).all()` 的全表读取；`CLAUDE.md` 的 t1 也已标记这一点。
- **修复建议**: 将 streak、7d accuracy、heatmap bucket、trend count 下推 SQL 聚合；补 `(user_id, shown_at)`、`(user_id, next_review_at)` 复合索引。
- **预估工时**: 6 小时

### [M-005] 前端分包被路由耦合打穿，构建产物已明显超阈值
- **维度**: 性能
- **文件**: `frontend/src/services/api.ts:62`, `frontend/src/routes.tsx:1`, `frontend/src/components/common/CodeEditor/CodeEditorInner.tsx:2`
- **问题描述**: 401 拦截器在 `api.ts` 里动态 `import("../routes")`，但 `routes.tsx` 又被 `App.tsx` 静态导入，Vite 明确警告“dynamic import will not move module into another chunk”。同时 Monaco 相关产物很重，本次 `npm run build` 产物中 `ts.worker` 约 7.0 MB、主 chunk `index-C65f2c3S.js` 约 739 kB。
- **影响**: 首屏下载和 editor/review 页面进入成本偏高，弱网和移动端会更明显。
- **复现路径**: 运行 `npm run build`；构建输出已给出 reporter warning 和超大 chunk 提示。
- **修复建议**: 将导航副作用抽到轻量 router bridge，避免 `api.ts` 直接依赖完整 routes；为 Monaco/worker 做 `manualChunks` 或裁剪语言能力。
- **预估工时**: 5 小时

### [M-006] 前后端对标题长度的校验上限不一致
- **维度**: UX / 质量
- **文件**: `frontend/src/pages/MistakeEditor/index.tsx:238`, `backend/app/schemas/mistake_constraints.py:5`
- **问题描述**: 后端 `MAX_TITLE_LEN = 500`，但前端表单 `rules={[{ required: true }, { max: 200 }]}` 只允许 200 字符。
- **影响**: 用户无法在 UI 中输入 API 明明接受的合法数据；未来导入/编辑 201-500 字符标题时也会出现“后端可存、前端不可改”的回环问题。
- **复现路径**: 尝试在编辑器输入 250 字标题，前端直接拒绝；但同样 payload 通过 API 会通过 schema 校验。
- **修复建议**: 统一为同一常量，最好由共享 schema/代码生成驱动前端规则。
- **预估工时**: 1 小时

### [M-007] Category / Tag 缺少长度约束，SQLite 不会替你兜底
- **维度**: 安全 / 质量
- **文件**: `backend/app/schemas/category.py:7`, `backend/app/schemas/tag.py:7`, `backend/app/services/taxonomy_service.py:102`, `backend/app/services/taxonomy_service.py:221`
- **问题描述**: 分类和标签 schema 只声明为裸 `str`，service 只做 `strip()` 非空判断；而 SQLite 对 `String(100)` 不会强制截断。
- **影响**: 超长分类/标签名可进入数据库，进而拖垮表格布局、导出文件、搜索条件和后续迁移。
- **复现路径**: 提交 10k 长度的 `name` 到 `/categories` 或 `/tags`；Pydantic 不会先挡住，SQLite 也不会按 100 截断。
- **修复建议**: 在 schema 上增加 `Field(max_length=100)` / `StringConstraints(max_length=100)`，并为 `description` 增加合理上限。
- **预估工时**: 2 小时

### [M-008] 关键后端测试绕过 Alembic，无法真正保护 0007/0008 迁移
- **维度**: 测试覆盖
- **文件**: `backend/tests/test_cross_user_isolation.py:25`, `backend/tests/test_import_export_v3.py:31`, `backend/tests/test_import_export_v3.py:137`
- **问题描述**: 跨用户隔离测试直接 `Base.metadata.create_all()`；导入导出测试多次使用 `initialize_database(..., force_fallback=True)`。这两类最关键的 regression tests 都没有通过 Alembic head 建库。
- **影响**: `0007` / `0008` 的索引、外键、唯一约束和迁移脚本错误，可能在“160 passed”下悄悄溜走。
- **复现路径**: 阅读 fixture 即可；这些测试压根没走 `alembic upgrade head`。
- **修复建议**: 提供 `alembic_head_engine` fixture，至少让隔离/导入导出两套用例在 migration schema 上各跑一遍。
- **预估工时**: 3 小时

## 5. Low 问题（技术债 / 风格）

### [L-001] streak toast 仍然没有 `.catch()`，网络失败会留下未处理 Promise
- **维度**: UX / 稳定性
- **文件**: `frontend/src/pages/Review/index.tsx:95`
- **问题描述**: `getStatsOverview(...).then(...)` 没有错误收口。
- **影响**: 完成复习时若 stats 接口临时失败，控制台会出现 unhandled rejection，toast 流程也没有降级路径。
- **复现路径**: 让 `/stats/overview` 返回 500，然后完成一轮 review。
- **修复建议**: 末尾补 `.catch(() => {})` 或改成 `void (async () => { try { ... } catch {} })()`
- **预估工时**: 0.5 小时

### [L-002] Dashboard 关键列表仍不可点击，已知导航债务未处理
- **维度**: UX / 可用性
- **文件**: `frontend/src/pages/Dashboard/index.tsx:209`
- **问题描述**: Recent Mistakes 与 Tag Cloud 仅展示文本和标签，没有 `<Link>` / `navigate()`。
- **影响**: 该页最自然的后续动作被截断，尤其是“看见弱点后继续跳转处理”这一主路径不顺。
- **复现路径**: 打开 Dashboard，点击最近错题标题或标签云均无跳转。
- **修复建议**: 最近错题跳 `/mistakes/:id`，标签云跳带筛选的 `/mistakes?tag=...` 或至少跳到列表页。
- **预估工时**: 1 小时

### [L-003] 多处用户文案直接写死，破坏 i18n 完整性
- **维度**: UX / 文档同步
- **文件**: `frontend/src/components/common/ProblemUrlImporter.tsx:21`, `frontend/src/components/review/VariantDrawer.tsx:33`, `frontend/src/pages/MistakeEditor/index.tsx:183`, `frontend/src/components/review/ReviewPageState.tsx:25`
- **问题描述**: URL 导入、变体题抽屉、review 占位页、自动填充 toast 等多个用户可见字符串没有走 `i18n` 资源。
- **影响**: 切到 `en-US` 后页面仍夹杂中文/英文固定文案，语言体验不一致。
- **复现路径**: 将语言切为英文，进入新建错题页 / review 空状态 / variant drawer。
- **修复建议**: 将这些字串收敛进 `zh-CN.ts` / `en-US.ts`，组件统一通过 `t(...)` 渲染。
- **预估工时**: 2 小时

### [L-004] README 指导开发者运行不存在的 `type-check` 脚本
- **维度**: 文档同步
- **文件**: `README.md:133`, `frontend/package.json:6`
- **问题描述**: README 写的是 `npm run type-check`，但 `package.json` 只有 `dev/test/build/preview`。
- **影响**: 新接手者照文档执行会直接失败，降低信任度。
- **复现路径**: 在 `frontend/` 执行 `npm run type-check`。
- **修复建议**: 要么补脚本 `"type-check": "tsc --noEmit"`，要么把 README 改成 `npx tsc --noEmit`。
- **预估工时**: 0.5 小时

### [L-005] Stats 页把调试性的时区偏移直接暴露给终端用户
- **维度**: UX
- **文件**: `frontend/src/pages/Stats/index.tsx:122`
- **问题描述**: 顶部直接渲染 `tz_offset {tzOffsetMinutes}m`。
- **影响**: 对普通用户无业务意义，反而增加界面噪音。
- **复现路径**: 打开 `/stats` 顶部工具栏即可看到。
- **修复建议**: 删除该 Tag，或仅在 debug / dev build 下显示。
- **预估工时**: 0.5 小时

## 6. 改进建议（非问题，但值得做）

### [I-001] 用 OpenAPI 生成对外 API 参考
- 将 `docs/api-contract-current.md`、README 路由表、deployment curl 示例改成从 FastAPI OpenAPI 导出，至少把路径、状态码和 response shape 自动化。

### [I-002] 增补一条真实的端到端回归链
- 覆盖 `register/login -> create mistake -> start review -> submit -> streak toast -> export v3`；当前测试更多是 service/store 级，真实页面与代理契约缺少一条贯通验证。

### [I-003] 前后端共享校验常量
- `MAX_TITLE_LEN`、taxonomy 长度、用户名/密码规则都值得做成共享 schema 或生成产物，避免继续出现 200 vs 500 这类分叉。

## 7. 已知问题验证
> 对照 CLAUDE.md "已知技术债与待修复清单" 中的 P2 / P3 项，确认是否真的存在、是否还有遗漏。

| 编号 | CLAUDE.md 描述 | 你的核实结果 |
|------|----------------|--------------|
| m1 | streak toast fetch 无 `.catch` | **确认**。`frontend/src/pages/Review/index.tsx:95-112` 仍是 `.then(...)` 无兜底 |
| m2 | authStore `set(parsed)` 全量合并 | **确认**。`frontend/src/stores/authStore.ts:43` 仍直接 `set(parsed)` |
| m3 | service `user_id=None` 残留 | **确认**。`stats_service.py`、`import_export_service.py`、`services/review/**` 仍大量保留 |
| t1 | `stats_service` 内存聚合 | **确认**。`backend/app/services/stats_service.py:79-220` 仍全量拉表 |
| t2 | Token 存 `localStorage` | **确认**。`frontend/src/stores/authStore.ts:22` 仍持久化 token；`backend/app/core/config.py:44` 默认 7 天 |
| t3 | Dashboard 列表无导航 | **确认**。`frontend/src/pages/Dashboard/index.tsx:209-235` 仍是纯展示 |

## 8. 审阅元信息
- 审阅模型：codex
- 审阅日期：2026-04-29
- 审阅范围：`backend/app/**`、`backend/alembic/versions/**`、`backend/tests/**`、`frontend/src/**`、`backend/.env.example`、`backend/requirements.txt`、`frontend/package.json`、`backend/alembic.ini`、`CLAUDE.md`、`README.md`、`docs/api-contract-current.md`、`docs/api-contract-w3.md`、`docs/deployment-guide.md`、`docs/release-runbook.md`、`docs/index.md`、`docs/future-extensions.md`
- 你跳过 / 未深入的部分：未逐行深读所有历史设计稿（如 `docs/ui-spec.md`、`docs/components*.md` 等早期规范文档）；未做浏览器手工交互或真实外部 AI provider 调用；结论主要基于源码、测试、构建输出与本地静态验证
