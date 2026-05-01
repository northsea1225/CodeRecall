# 码错本 (CodeRecall) — 项目交接文档

> 新对话直接读此文件，跳过所有背景询问，立即进入执行模式。
> ⚠️ **角色约束**：Claude 只做方案讨论和协调，不擅自执行代码修改——必须获得用户明确授权后才能派发任务（详见文末协作规范）。

---

## 项目简介

**码错本**：面向 OI/ACM/LeetCode 选手的智能编程错题本。核心差异化：6 阶段动态 AI 教练（根据复习历史判断状态，非通用回复）+ SM-2 遗忘曲线调度 + LeetCode 一键导入。
核心循环：**导入题目 → 记录错误 → SM-2 间隔重复调度复习 → 6 阶段动态 AI 深度分析**。

- 项目路径：`/Users/hfish/Claude_chat/协同码力/`
- GitHub：`https://github.com/northsea1225/CodeRecall`
- 后端：FastAPI + SQLAlchemy + SQLite，Python 3.9.6（本地 venv at `backend/.venv`）
- 前端：React 18 + TypeScript + Vite + Ant Design 5 + react-router-dom 7.1.x + Zustand 5
- 测试：后端 **197 passed**（pytest），前端 **40 passed**（vitest）
- 已安装依赖：`passlib[bcrypt]` 1.7.4、`PyJWT` 2.12.1、`bcrypt==4.0.1`（pinned for passlib 兼容）
- AI 模型：`deepseek-v4-pro`（主/高级）、`deepseek-v4-flash`（快速），配置在 `backend/.env`

---

## 启动服务

```bash
# 后端（端口 8000）
cd /Users/hfish/Claude_chat/协同码力/backend
source .venv/bin/activate
uvicorn app.main:app --reload

# 前端（端口 5173）
cd /Users/hfish/Claude_chat/协同码力/frontend
npm run dev

# 后端测试（必须激活 venv，不要用裸 python -m pytest）
cd /Users/hfish/Claude_chat/协同码力/backend
.venv/bin/python -m pytest backend/tests/ -q

# 前端测试
cd /Users/hfish/Claude_chat/协同码力/frontend
npm test -- --run
```

API 文档：`http://localhost:8000/docs`

---

## 当前焦点

**Audit-fixes Phase 3 完成（6/6 高优先级 + 关键基础设施） → 仅剩 M/L 收尾项**（2026-05-01 更新）。

- 审阅产出：`docs/audit/2026-04-29/`（三方独立报告 Claude/Codex/Gemini + 综合 final-report.md）
- 修复计划：`.claude/plan/audit-fixes.md`（41 个 issue × 4 个 Phase × 81h 工时，含 Codex 交叉验证合并决议）
- **API 单一事实源**：`docs/openapi.json`（自动生成，CI gate 防漂移）；本地用 `bash scripts/gen-docs.sh` 重新生成
- **执行模式**：用户在 Phase 2 起授权 Claude 亲自执行（直接 Edit/Write，不派 Codex/team），每次实施前仍呈报具体改动 + 等待确认。**新会话续做时建议重新和用户确认是否延续此例外**

当前状态：backend **197 passed** · frontend **40 passed** · type-check 退出 0 · Alembic head: **0009**

### Phase 1 已交付（5 个一行修复）

走 `dc4d6df`（test 补强）+ `979effb` 包含的内联修复，详见 plan §C-004/M-007/M-009/M-011/M-013。

### Phase 2 完成（6/6）

| Issue | Commit | 备注 |
|-------|--------|------|
| H-005 pin deps with hashes | `539b3c7` | requirements.in/.txt + .gitignore |
| C-003 + I-005 IP 限流 | `46482ef` | slowapi 0.1.9 + RATE_LIMIT_ENABLED env |
| H-003 SSRF 防护 | `fbc8339` | providers/base.py safe_request helper |
| H-004 /import payload 上限 | `394c871` | BodySizeLimitMiddleware 50MB |
| L-001 + M-002 + M-003 router bridge | `1eed8c5` | utils/routerBridge.ts + npm run type-check |
| C-002 + H-001 lifespan 重写 | `9187264` | initialize_database 已有库 fail-fast；env.py 保护 root handlers |

### Phase 3 完成（6/6 高优先级）

| Issue | Commit | 备注 |
|-------|--------|------|
| H-008 alembic_head_engine fixture | `9afd2db` | conftest fixture + 3 cases；解锁后续 |
| H-009 schema parity | `cdd6747` | 5 个 user_id FK 加显式 name；test_schema_parity 兜底 |
| C-001 user_id 必填（5 批） | `b201c9e` `46d9eb3` `c2013ad` `1c598b1` `2c02547` | 47 函数 keyword-only；3 fuse tests + 测试 helper 修正 |
| H-007 review GET 去写 | `5779e58` | _progress_for_session 改纯读 + 删 _mark_session_completed_if_needed |
| H-006 stats SQL push-down | `0cac770` | 5 函数 SQL 聚合 + alembic 0009（3 复合索引）+ heatmap 顺手修 |
| H-002 + I-001 OpenAPI 单一源 | `534a5db` | scripts/gen-docs.sh + docs/openapi.json + GitHub Actions gate；删除 api-contract-current.md；修 4 处 `/auth/*` 错描述 |

### Phase 3 剩余（M/L 项，约 13.5h，无依赖）

| Issue | 工时 | 性质 | plan § |
|-------|------|------|--------|
| M-001 CORS 配置紧化 | ~1h | 后端 config | §882 |
| M-004 Category/Tag schema 长度约束 | ~1h | 后端 schema | §920 |
| M-006 list_mistakes 拆 MistakeListOut | ~2h | 后端+前端协调 | §946 |
| M-008 i18n 5+ 组件 | ~2h | 前端 | §979 |
| M-010 MAX_TITLE_LEN 200 vs 500 同步 | ~0.5h | ORM/schema/前端三方对齐 | §983 |
| M-012 + L-004 useAiAnalysisStream 改进 | ~1h | 前端 | §1003 |
| L-002 errors.py Optional[Any] schema 化 | ~1h | 后端 | §1020 |
| L-003 _ensure_old_user 复用 SessionLocal | ~0.5h | 后端 | §1041 |
| L-005 v3 import dedup 内存读 UUID | ~1.5h | 后端 | §1007 |
| L-007 JWT secret check 强类型 | ~1h | 后端 | §1056 |

### Phase 4 双月（约 30h，未启动）

C-005 Token 安全改造 / I-006 Playwright e2e / I-004 PWA / I-007 CI 扫描 / I-008 Python 3.9→3.11。

### 新会话续做指引

1. 读 `.claude/plan/audit-fixes.md` 找具体 issue 的 8 段方案（Files / Implementation / Tests / Edge cases / Dependencies / Risks / Acceptance / Effort）
2. 按 Phase 2/3 既有协作模式：调研 → 呈报方案 → 等"做"/"可以" → 落地 → 跑测试 → 提交
3. 测试基准：每次提交前 `APP_ENV=test backend/.venv/bin/python -m pytest backend/tests/ -q` 应当 197+ passed（视新增测试而定）
4. OpenAPI 同步：任何 backend 路由 / Pydantic schema 变更后跑 `bash scripts/gen-docs.sh` 重新生成 `docs/openapi.json`，否则 CI gate 会卡 PR

> Month 1（用户认证 Phase A+B + schema_v3 + CF 导入）已于 2026-04-24 全部交付。
> Month 2（Streak 打卡 + 暗房复习模式 + SSE 认证修复）已于 2026-04-25 交付。
> P0 安全修复（old_user 密码后门 + JWT fail-fast）已于 2026-04-26 完成。
> P1 稳定性修复（M2/M3/M4/M5/M-new）已于 2026-04-26 完成。
> **全栈大规模审阅（三方独立 + 综合）**已于 2026-04-29 完成。
> **Audit-fixes 计划（41 issue / 81h）**已于 2026-04-30 产出。
> **Phase 2 完成 6/6** + **Phase 3 完成 6/6 高优先级** 于 2026-05-01。

---

## 已完成功能（当前状态）

### 核心功能 ✅
- 错题 CRUD（题目、错因、正确答案、代码 diff）
- SM-2 间隔重复算法（后端已实现）；前端默认策略为 `due_first` / `random`，选择 `spaced_repetition` 策略时才触发 SM-2 间隔更新
- 复习记录完整追踪（ReviewLog 表）
- 统计看板：KPI 卡片、趋势图、热力图、薄弱题表、**算法能力雷达图**
- 导入/导出 v2 + **schema_v3 全量备份**（含 review_sessions/review_logs，UUID 跨设备去重）
  - `GET /api/v1/export/v3`、`POST /api/v1/import/v3`
  - UUID 大小写统一（`.lower()`）防 SQLite unique index bypass
  - session_id 跨设备 remap；旧路由 backward compat 保持不变
- **LaTeX 公式渲染**：KaTeX，支持 `$...$` 和 `$$...$$`
- **键盘快捷键**：复习页 `1/2/3/4` 评分，空格翻牌
- 所有业务 API 挂载在 `/api/v1`；`/health` 为根路径系统检查接口（不带前缀）

### AI 分析 ✅
- **6 阶段 ReviewStage 感知提示词**（`backend/app/services/prompt_templates.py`）
  - 6 个阶段：`new_mistake` / `early_review` / `repeated_weakness` / `lapsed` / `oscillator` / `maintenance`
  - 核心函数：`_compute_review_stage()`、`_is_oscillator()`、`_is_lapsed()`
  - XML 结构化输入 + `html.escape()` 防注入；各语言专属 hint
- `build_mistake_prompt_input()` 提取 review_logs 5 个字段（已修复 `user_result` 字段名 bug）
- `ai.py` 路由：`selectinload(Mistake.review_logs)` 已加
- **AI 变体题生成**：`POST /api/v1/ai/generate-variant/{mistake_id}`，普通 JSON 响应（非 SSE），前端 `VariantDrawer`
- **AI 字段长度校验**：Pydantic `Annotated` 类型，集中在 `mistake_constraints.py`
- **AI model 空守卫**：`analyze_stream` / `generate_variant` 两端均加 `if not resolved_model: raise AiAnalysisError`
- **前端 SSE 流**：`useAiAnalysisStream.ts` 使用 `fetch + ReadableStream + AbortController`，注入 Bearer token，支持 `event: error` 专路；多行 `data:` 累积（`dataLines.join("\n")`）+ CRLF 正则兼容已实现；HTTP 错误路径 `body.detail` 类型守卫为 `unknown`（2026-04-26）

### 用户认证系统 ✅（Phase A + B，2026-04-24 完成）
- 注册 / 登录 / JWT 认证全链路
- FastAPI：`POST /api/v1/auth/token`、`POST /api/v1/auth/register`（字段约束：用户名 3–100 字符 `^[A-Za-z0-9_]+$`，密码 8–72 字节，前后端双层校验）、`GET /api/v1/auth/me`
- JWT 签发/验证（PyJWT 2.12.1），密码哈希（passlib[bcrypt]，bcrypt==4.0.1 pinned），有效期默认 10080 分钟（7天）
- 前端 `authStore`（Zustand）：`login()` / `logout()` / `initializeAuth()`（JWT exp 校验，防闪屏）
- 前端 `AuthGuard`（react-router-dom 7.1.x Outlet 嵌套路由模式）
- 401 拦截：`router.navigate('/login', { replace: true })`（`frontend/src/services/api.ts`）
- `old_user`（id=1）持有所有迁移前数据；P0 修复后密码改由 `OLD_USER_INITIAL_PASSWORD` 环境变量控制，默认值在生产环境 fail-fast（见 `auth_service.py:ensure_default_old_user`）
- **Phase B**：service 层全面 user_id 隔离，per-user UUID 唯一索引（migration 0008），8 个跨用户隔离测试通过
- **安全加固**：JWT 默认密钥在非 dev/test 环境 → `RuntimeError` fail-fast；AI 路由移除 `isinstance` fail-open

### 录入体验 ✅
- **LeetCode URL 题面预览**：`POST /api/v1/import/problem-url/preview`，httpx + LeetCode GraphQL + markdownify，支持中英文站
- **CF URL 题面导入**：provider 模式（`providers/codeforces.py`），CF API + 页面 HTML 解析，MathJax 公式处理，rating → difficulty 映射；Gym/private 返回 warning
- **首次使用引导页（OnboardingPage）**：空题库全屏展示，含 URL 导入 + Demo 数据一键载入
  - 触发入口：`MistakeList/index.tsx:208-213`，条件：`pagination.total === 0 && !localStorage.getItem("coderecall_ever_imported_${userId}") && hasFetched && isUnfiltered`
  - Demo：4 道经典 C++ 错题（线段树/背包DP/Dijkstra/int溢出），位于 `frontend/src/data/demoImportPayload.json`
  - `mistakeStore.ts` 含 `hasFetched: boolean` 防首次加载闪屏
  - `authStore` 通过 Zustand subscribe 触发 `mistakeStore.reset()`（token 消失时），解决 ESM 循环依赖

### Month 2 体验增强 ✅（2026-04-25 完成）
- **Streak 打卡激励**：Dashboard 4 列网格（`dashboard-metric-grid`），Streak 卡片橙/绿分级色；复习完成 toast（7/30 天里程碑，localStorage 同天去重 key `cr-streak-toast:${userId}:${date}`）；Dashboard 使用 `Promise.allSettled` 并行拉取 5 个接口，各指标独立降级（`mistakesApiOk` 门控防空态误判，2026-04-26）
- **暗房复习模式**：`/review/immersive` 全屏无侧边栏（AuthGuard 内、AppLayout 外），`max-width: 900px`，退出按钮 `position: fixed; top: 16px; right: 16px`，移动端（≤ 768px）不显示入口（注：这不等于完整移动端适配，移动端适配仍在 Month 2 待做）
- **logout 状态清理**：logout 清空 `reviewStore` + `draftStore`；`main.tsx` side-effect import 确保 `mistakeStore` subscribe 在启动时注册
- **v3 导入三层幂等**：session / item / log 分别去重，session dedup 含 6 字段（started_at / strategy / ended_at / total_count / completed_count / user_id，2026-04-26）
- **i18n**：zh-CN + en-US 新增 `dashboard.streakDays`、`review.streakToast`、`review.streakMilestone7/30`、`review.enterImmersive`、`review.exitImmersive`

### 主题 & 品牌 ✅
- Light/Dark 模式完整支持，CSS 变量双主题（`tokens.css` 双套 `--app-sider-*`）
- `frontend/public/logo.png`：蓝色圆角 `</>` 图标 + 红色闪电徽标

---

## 路由速查

### 前端路由（`frontend/src/routes.tsx`）

| 路径 | 说明 | 权限 |
|------|------|------|
| `/login` | 登录页 | 公开 |
| `/register` | 注册页 | 公开 |
| `/` | 重定向到 `/dashboard` | AuthGuard |
| `/dashboard` | 数据看板 | AuthGuard + AppLayout |
| `/mistakes` | 错题列表 / OnboardingPage | AuthGuard + AppLayout |
| `/mistakes/new` | 新建错题 | AuthGuard + AppLayout |
| `/mistakes/:id` | 错题详情 | AuthGuard + AppLayout |
| `/mistakes/:id/edit` | 编辑错题 | AuthGuard + AppLayout |
| `/review` | 复习模式入口 | AuthGuard + AppLayout |
| `/review/immersive` | 暗房复习（全屏，无侧边栏） | AuthGuard，AppLayout 外 |
| `/stats` | 统计看板 | AuthGuard + AppLayout |
| `/import-export` | 导入/导出 | AuthGuard + AppLayout |

### 后端 API（`backend/app/api/routes/`）

所有业务路由前缀 `/api/v1`；`/health` 不带前缀。

| Router | 前缀 | 说明 |
|--------|------|------|
| auth | `/auth` | token / register / me |
| mistakes | `/mistakes` | CRUD + 归档 |
| categories | `/categories` | 分类 CRUD |
| tags | `/tags` | 标签 CRUD |
| review | `/review` | 开始/提交/结束复习 session |
| stats | `/stats` | overview / trend / heatmap / tag-radar |
| ai | `/ai` | SSE 分析流 / 变体题生成 |
| import_export | `/import`、`/export` | v2 + v3 导入导出 |
| problem_import | `/import/problem-url` | LeetCode / CF URL 预览导入 |

---

## 关键文件速查

### 后端

| 文件 | 作用 |
|------|------|
| `backend/app/main.py` | FastAPI 应用入口，CORS，路由注册，`/health` |
| `backend/app/core/config.py` | Settings（pydantic-settings），JWT fail-fast 逻辑 |
| `backend/app/api/deps.py` | `get_current_user` FastAPI 依赖 |
| `backend/app/api/routes/auth.py` | POST /api/v1/auth/token, POST /api/v1/auth/register, GET /api/v1/auth/me |
| `backend/app/models/user.py` | User ORM 模型 |
| `backend/app/services/auth_service.py` | verify_password / hash_password / create_access_token / decode_access_token / create_user / ensure_default_old_user |
| `backend/app/services/prompt_templates.py` | AI 提示词核心，ReviewStage 枚举，所有 _compute_* 函数 |
| `backend/app/services/ai_analysis_service.py` | AI 流式请求，`build_mistake_prompt_input()`，model 空守卫 |
| `backend/app/api/routes/ai.py` | SSE 端点，review_logs eager load，变体题端点 |
| `backend/app/schemas/mistake_constraints.py` | 字段长度约束 Annotated 类型 |
| `backend/app/api/routes/problem_import.py` | LeetCode / CF URL 导入路由 |
| `backend/app/services/problem_import_service.py` | URL 导入解析核心 |
| `backend/app/services/providers/leetcode.py` | LeetCode URL 解析 provider |
| `backend/app/services/providers/codeforces.py` | CF URL 解析 provider（API + HTML + MathJax） |
| `backend/app/api/routes/import_export.py` | 导入/导出路由（v2 + v3），旧路由 backward compat |
| `backend/app/schemas/import_export.py` | 导入/导出 schema（含 ExportResponseV3 / ImportPayloadV3） |
| `backend/app/services/import_export_service.py` | 导入/导出服务（含 export_data_v3 / import_data_v3，三层幂等去重） |
| `backend/app/services/taxonomy_service.py` | 分类/标签 CRUD 服务 |
| `backend/app/services/stats_service.py` | 统计聚合（当前内存聚合，见技术债 t1） |
| `backend/app/services/review/__init__.py` | 复习 session 核心服务 |
| `backend/app/db/init_db.py` | 数据库初始化，Alembic 迁移，`_ensure_old_user` |
| `backend/alembic/versions/0007_add_user_system.py` | users 表 + user_id FK + old_user 迁移 + 复合唯一约束 |
| `backend/alembic/versions/0008_uuid_composite_unique.py` | uuid 唯一索引从全局改为 per-user（ix_mistakes_user_uuid），当前 Alembic head |
| `backend/tests/test_cross_user_isolation.py` | 跨用户数据隔离回归测试（8 个用例） |
| `backend/tests/test_import_export_v3.py` | schema_v3 导入导出专项测试（8 个用例） |
| `backend/tests/test_prompt_templates.py` | ReviewStage / prompt 模板专项测试 |

### 前端

| 文件 | 作用 |
|------|------|
| `frontend/src/main.tsx` | 应用入口，`initializeAuth()`，`import "./stores/mistakeStore"` side-effect |
| `frontend/src/App.tsx` | ConfigProvider，Ant Design 主题，ThemeProvider |
| `frontend/src/routes.tsx` | 路由定义 + 侧边栏 JSX，AuthGuard，lazy import |
| `frontend/src/hooks/useAiAnalysisStream.ts` | AI SSE 流（fetch + ReadableStream），Bearer token，event:error 解析 |
| `frontend/src/stores/authStore.ts` | JWT token 管理；logout 清理 reviewStore/draftStore；`initializeAuth()` exp 校验 |
| `frontend/src/stores/mistakeStore.ts` | 错题列表状态，含 `hasFetched`；subscribe 监听 auth token 清空 |
| `frontend/src/stores/reviewStore.ts` | 复习 session 状态（sessionId / currentItem / progress / completed 等） |
| `frontend/src/stores/draftStore.ts` | 错题草稿缓存（含 `clearAll()`） |
| `frontend/src/stores/uiStore.ts` | 全局 UI 状态（Toast，Theme，Sider collapse 等） |
| `frontend/src/services/api.ts` | axios 实例，无全局 Content-Type；request 拦截注 Bearer；response 拦截 401→logout→/login |
| `frontend/src/services/authService.ts` | `login()`（URLSearchParams form-encoded）、`register()`（JSON）、`getMe()` |
| `frontend/src/pages/Login/index.tsx` | 登录页 |
| `frontend/src/pages/Register/index.tsx` | 注册页，成功后 navigate("/mistakes") |
| `frontend/src/pages/Dashboard/index.tsx` | 数据看板，含 Streak 卡片，`Promise.allSettled` 并行拉取 5 接口，`mistakesApiOk` 防空态误判 |
| `frontend/src/pages/MistakeList/index.tsx` | 错题列表页，OnboardingPage 触发入口（:208-213） |
| `frontend/src/pages/MistakeList/OnboardingPage.tsx` | 首次使用引导页 |
| `frontend/src/pages/MistakeEditor/index.tsx` | 错题编辑器页（新建/编辑） |
| `frontend/src/pages/Review/index.tsx` | 复习主页，键盘快捷键，`immersive` prop，streak toast |
| `frontend/src/pages/Review/ImmersiveReviewPage.tsx` | 暗房模式全视口 shell（~10 行） |
| `frontend/src/pages/Stats/index.tsx` | 统计页（趋势图、热力图、雷达图） |
| `frontend/src/pages/ImportExport/index.tsx` | 导入/导出页 |
| `frontend/src/components/common/ProblemUrlImporter.tsx` | URL 导入组件，支持 `autoFocus` |
| `frontend/src/components/common/MarkdownRenderer.tsx` | Markdown + LaTeX 渲染 |
| `frontend/src/components/review/VariantDrawer.tsx` | AI 变体题抽屉 |
| `frontend/src/components/stats/RadarTagChart.tsx` | 算法能力雷达图 |
| `frontend/src/data/demoImportPayload.json` | 4 道 Demo C++ 错题 |
| `frontend/src/styles/tokens.css` | 设计令牌，双主题 CSS 变量 |
| `frontend/src/styles/global.css` | 全局样式，布局规则，暗房/Dashboard 专属 class |
| `frontend/src/i18n/resources/zh-CN.ts` | 中文 i18n |
| `frontend/src/i18n/resources/en-US.ts` | 英文 i18n |

---

## 路线图（Month 1-3）

### Release Blockers（上线前必须完成）

| ID | 说明 | 优先级 | 状态 |
|----|------|--------|------|
| C1 | old_user 默认密码后门 | P0 | ✅ 2026-04-26 |
| M1 | JWT 默认密钥在 development 环境放行 | P0 | ✅ 2026-04-26 |
| M2 | SSE HTTP 错误路径 body.detail 类型守卫 | P1 | ✅ 2026-04-26 |
| M3 | 注册接口无字段约束 | P1 | ✅ 2026-04-26 |
| M4 | v3 session 去重条件太弱 | P1 | ✅ 2026-04-26 |
| M-new | Dashboard Promise.all 全或无崩溃 | P1 | ✅ 2026-04-26 |
| M5 | SSE 多行 data: 只保留最后一行 | P1 | ✅ 2026-04-26 |

### 全栈大规模审阅 + audit-fixes 计划（2026-04-29 / 04-30）

**审阅产出**（三方独立 + 综合）：
- `docs/audit/2026-04-29/claude-report.md`（646 行 / 4 Critical / 8 High / 13 Medium / 6 Low）
- `docs/audit/2026-04-29/codex-report.md`（227 行）
- `docs/audit/2026-04-29/gemini-report.md`（149 行）
- `docs/audit/2026-04-29/final-report.md`（427 行综合）
- `docs/audit/2026-04-29/codex-backend-fix-plan.md`（490 行 codex 后端方案存档）

**修复计划**：`.claude/plan/audit-fixes.md`（1237 行，含 Codex 交叉验证合并决议）

| Phase | 范围 | 工时 | 关键交付 |
|-------|------|------|----------|
| Phase 1 | 立即（< 2h） | 2.5h | C-004 / M-007 / M-009 / M-011 / M-013（5 个 1 行修复） |
| Phase 2 | 本周（5d） | 14h | H-005 钉版本 / C-003 限流 / H-003 SSRF / H-004 OOM / **C-002+H-001 lifespan 重写** / M-002+M-003 router bridge / L-001 |
| Phase 3 | 本迭代（10d） | 35h | H-008 alembic fixture / H-009 schema audit / **C-001 user_id 必填 5 批** / H-007 review GET / H-002+I-001 OpenAPI / H-006 stats SQL |
| Phase 4 | 双月 | 30h | C-005 Token 改造 / I-006 Playwright / I-004 PWA / I-007 CI 扫描 |

**关键发现**（CLAUDE.md 当前 P2/P3 严重度被低估）：
- m2 `authStore.set(parsed)` → **升 Critical**（C-004，已是 attack chain 放大器）
- m3 `service user_id=None` → **升 Critical + 量化 30+ 函数**（C-001，5 个 service 文件全军覆没）
- t2 Token localStorage → **升 Critical**（C-005，7 天有效期 + 无 revoke）
- 新发现：auth 无速率限制、已有库不跑 Alembic、CF SSRF、/import OOM、ORM `String(255)` vs schema 500 vs 前端 200 三方不一致

### Month 1 — 降阻力 + 数据安全 + 用户系统

| 任务 | 工时 | 状态 |
|------|------|------|
| 空状态引导（Demo 数据 + URL 输入框） | 0.5天 | ✅ 已完成 |
| 全量备份/导出（schema_v3，含 review_logs / UUID） | 3天 | ✅ 已完成 |
| CF URL 导入（provider 模式，CF API + HTML 解析） | 4天 | ✅ 已完成 |
| 本地用户认证系统 Phase A（注册/登录/JWT/AuthGuard） | 6天 | ✅ 已完成（2026-04-24） |
| 本地用户认证系统 Phase B（service 层 user_id 隔离 + 安全加固） | 4-5天 | ✅ 已完成（2026-04-24） |

### Month 2 — 快速体验增强 + 手机端

| 任务 | 工时 | 状态 | 备注 |
|------|------|------|------|
| Streak 连续打卡激励 | 1天 | ✅ 已完成（2026-04-25） | Dashboard 卡片 + 复习完成 toast |
| 沉浸式暗房复习模式（隐藏侧边栏，全屏） | 1天 | ✅ 已完成（2026-04-25） | `/review/immersive` 独立路由 |
| 手机端适配（复习模式优先，纯 CSS） | 3-4天 | ⬜ 待做 | 暗房入口仅在 ≤768px 隐藏，不等于完整适配；复习页+统计页优先 |

### Month 3 — 生态 + 体验深化

| 任务 | 工时 | 状态 | 备注 |
|------|------|------|------|
| Anki 导出（genanki，HTML 字段，稳定 GUID） | 2天 | ⬜ 待做 | GUID 建议用 user_id+uuid 命名空间 |
| 高级搜索（比赛来源、错因、掌握度多维筛选） | 2天 | ⬜ 待做 | |
| AI 分析分享卡片 | 2-3天 | ⬜ 待做 | |

### Month 4-6 — 护城河

- 赛后聚合洞察报告（多题 AI 分析汇总）
- 错题集公开分享（Deck Share）
- 浏览器插件（CF/LeetCode 页面一键收录）

---

## 代码规范备忘

- 不写无意义注释，不写多行 docstring
- 后端测试：`unittest.TestCase` 和 pytest 函数风格混用；数据库相关测试用真实 SQLite，不 mock DB（允许 `unittest.mock` patch 外部 API）
- 后端命令必须用 `backend/.venv/bin/python` 或先 `source backend/.venv/bin/activate`，不要用系统 `python`
- CSS 变量优先，不硬编码颜色值
- 新增业务路由必须加 `Depends(get_current_user)`，并向 service 层显式传 `user_id`
- 禁止新增 `user_id: int | None = None` 的业务 service 默认参数；需要全局/admin 查询时用独立函数并在函数名中体现（如 `get_all_for_admin`）
- Alembic 当前 head 为 `0008`；新增 migration 前先运行 `alembic heads` 确认链路

---

## 协作规范（强制执行）

> Claude 在此项目中的角色是**方案讨论者和协调者**，不是代码执行者。
> 完整流程：讨论 → 呈报方案 → 用户确认 → 派发执行 → 复核结果。

### 核心约束

1. **讨论**：Claude 联合 Codex / Gemini（CCG）进行分析，**只输出**分析报告和备选方案，不触发任何写文件动作
2. **呈报方案**：Claude 将最终实施计划（涉及文件、改动点、影响范围）清晰呈报给用户，**主动停下来**等待确认
3. **用户确认**：只有收到明确授权指令（如"可以执行"、"让 Codex 改"、"按这个方案做"）才能继续；一般讨论、认可思路**不等于**授权
4. **派发执行**：获得授权后，Claude 才调用 Codex / team 执行代码落地；执行 agent 只改授权范围内的文件
5. **复核**：Codex / team 完成后，Claude 必须回收结果 → 汇报改动点 → 验证结果（运行测试）→ 说明剩余风险

### 标准工具

- **CCG**（`/ccg`）：Claude + Codex + Gemini 三方并行分析，用于方案设计和技术评估
- **`/team`**：派发多文件并行执行任务给 Codex/executor agent

### 临时例外（2026-04-30 起 · 仅限 audit-fixes 计划）

> 用户已授权 Claude 亲自执行 `.claude/plan/audit-fixes.md` 中的 41 项修复，可直接使用 Edit/Write 工具修改项目代码（无需派发 Codex/team）。
>
> **保留约束**：
> 1. 每次实施前**仍需呈报**具体改动文件 + diff 摘要，等待用户"可以"或"做"再下笔
> 2. 每个 issue / phase 完成后**必须运行测试**（pytest + vitest）验证零回归
> 3. 多 issue 改动**按 ordering rules 分批 PR**，不许打包成一个
> 4. 例外**仅适用于 audit-fixes.md 计划内的 issue**；plan 范围外的改动仍走"讨论 → 呈报 → 用户授权 → 派发"原流程
>
> 本例外随 audit-fixes 全部完成自动失效；如需延续到下一批工作请重新授权。

### 禁止行为

- ❌ 讨论出方案后不汇报，直接让 Codex 写文件
- ❌ 用户要求"分析/查看"，却自动应用了修改建议
- ❌ 预判用户意图，在收到"执行"指令前就提前派发写文件 prompt
- ❌ Claude 自己直接使用 Edit / Write 工具修改项目代码文件（`~/.claude/**`、`.omc/**`、`CLAUDE.md` 除外）

### 执行前固定话术

> "我已完成方案设计，准备修改以下文件：[列表]。请确认是否让 Codex 执行？"

---

## 已知技术债与待修复清单

> 来源：Codex + Gemini + Claude 三方代码审查（2026-04-25）。**P0/P1 已于 2026-04-26 全部修复。**

### P0 — ✅ 已完成（2026-04-26）

| ID | 问题概要 |
|----|---------|
| C1 | `old_user` 默认密码后门 → 由 `OLD_USER_INITIAL_PASSWORD` 控制，生产环境 fail-fast |
| M1 | JWT 默认密钥 development 放行 → secret 为默认值且非 `APP_ENV=test` 时一律 fail-fast |

### P1 — ✅ 已完成（2026-04-26）

| ID | 问题概要 |
|----|---------|
| M2 | SSE body.detail 类型守卫 → `unknown` + `typeof` 检查 |
| M3 | 注册接口无字段约束 → 前后端双层：用户名 3–100 / `^[A-Za-z0-9_]+$`，密码 8–72 字节 |
| M4 | v3 session 去重 4 字段 → 扩展至 6 字段（+ended_at, +completed_count） |
| M-new | Dashboard Promise.all 全崩 → Promise.allSettled，各指标独立降级，mistakesApiOk 防空态 |
| M5 | SSE 多行 data: 只保最后行 → dataLines 数组累积 + CRLF 正则兼容 |

### P2 — 迭代内

| ID | 文件:行 | 问题 | 修复方向 |
|----|---------|------|---------|
| m1 | `Review/index.tsx:98` | streak toast fetch 无 `.catch`，网络失败产生 unhandled rejection | 末尾加 `.catch(() => {})` |
| m2 | `authStore.ts:43` | `set(parsed)` 将整个 localStorage 对象合并进 Zustand state，外部篡改可注入字段 | 改为 `set({ token: parsed.token, username: parsed.username, userId: parsed.userId })` |
| m3 | `import_export_service.py`、`stats_service.py`、`services/review/__init__.py:37/104/150/190/244`、`selector.py:19/53`、`recorder.py:22`、`progress_updater.py:31` | `user_id: int \| None = None` 默认值残留，路由外误调用有越权风险 | 改为必填参数；admin/全局查询用独立函数命名区分 |

### P3 — 技术债（结构性，不阻塞上线）

| ID | 文件:行 | 问题 | 修复方向 |
|----|---------|------|---------|
| t1 | `stats_service.py:89/133/155` | 全量 ReviewLog 加载到 Python 内存聚合，数据增长后性能劣化 | 将 streak/count/bucket 聚合下推 SQL；加 `(user_id, shown_at)` 复合索引 |
| t2 | `authStore.ts:22` | Token 存 localStorage，XSS 时爆炸半径大；有效期 7 天无 revocation | 评估换 HttpOnly Cookie + refresh token；至少缩短 `access_token_expire_minutes` |
| t3 | `Dashboard/index.tsx` | Recent Mistakes 列表和 Tag Cloud 无可点击导航 | 加 `<Link>` 或 `onClick` 跳转到对应筛选视图 |
| t4 | `Register/index.tsx` | ~~前端表单缺少长度校验~~ | ✅ M3 修复时已同步（2026-04-26） |
