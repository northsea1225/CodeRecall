# CodeRecall 全栈审阅综合报告（2026-04-29 / 重做版）

> **重做说明**：上一版综合报告基于 Claude 通过 omc ask 单轮 advisor 模式产出的摘要级报告（仅 Top 5 + 摘要），缺失大量 issue 细节。本版基于主对话 Claude 用 Read/Glob/Grep 直接扫码后产出的 **Claude 完整版报告（646 行）** + Codex（227 行）+ Gemini（149 行）三份独立报告综合。
>
> **三方独立性**：每份子报告由对应模型独立产出，未参考彼此输出。Claude 完整版在写作时已有意识回避 Codex/Gemini issue 编号与措辞，独立性虽不完美（已读过上一版综合报告），但贡献明确集中在独家发现上。
>
> **共识度图例**：★ 三方共识 / ☆ 双方共识 / ◯ 单方独家
> **来源标注**：C=Claude · X=Codex · G=Gemini

---

## 0. 综合摘要

### 三方独立评分对比（更新版）

| 模型 | 总评 | 问题分布 | 报告体量 |
|------|------|----------|----------|
| **Claude（完整版）** | B- | Critical 4 · High 8 · Medium 13 · Low 6 | 646 行 / 28 KB |
| **Codex** | C | Critical 0 · High 2 · Medium 8 · Low 5 | 227 行 / 19 KB |
| **Gemini** | B | Critical 1 · High 2 · Medium 4 · Low 3 | 149 行 / 11 KB |

**综合判定**：**B-**（核心安全护栏到位，160+32 测试全绿，但有 5 项 Critical 与 9 项 High 在上线前需要决策）。

### 三方报告差异分析

- **Claude 偏重外部攻击面 + 部署陷阱**：4 个独家 Critical/High（auth 限流缺失、已有库不跑迁移、CF SSRF、import OOM、依赖钉版本、schema 漂移、OLD_USER 默认值 footgun）。重点指出"路由严守、service 松弛"反共生模式的量化范围（30+ 函数）。
- **Codex 偏重运行时一致性**：5 个独家发现集中在迁移失败 fallback、文档与 API 漂移、review GET 副作用、构建产物超阈值、关键测试绕过 Alembic。
- **Gemini 偏重前端信任假设**：核心是 localStorage 的信任问题放大 XSS 影响面 + Zustand 状态注入。

三视角互补，没有重大遗漏。Claude 在跨文件因果链与协议一致性上贡献最多新发现；Codex 在系统级运行时一致性上最锋利；Gemini 在前端信任假设上视角清晰。

### 共识 Top 7（按严重度）

| # | 问题 | 共识度 | 来源 / 严重度差异 |
|---|------|--------|-------------------|
| 1 | service 层 `user_id: Optional[int] = None` 残留 30+ 函数 | ★ | C(Critical) X(Medium) G(Medium) — Claude 量化范围扩大 5 倍 |
| 2 | `authStore.set(parsed)` 全量字段注入 Zustand | ★ | C(Critical) X(Medium) G(High) — 严重度判定有分歧 |
| 3 | Token 存 localStorage + 7 天 + 无 revoke | ★ | G(Critical) C(High) X(C 评分但未单列) |
| 4 | `stats_service` 全量加载 + Python 内存聚合 | ★ | G(High) C(High) X(Medium) |
| 5 | streak toast `getStatsOverview` 无 `.catch` | ★ | C(Medium) X(Low) G(Medium) — CLAUDE.md m1 |
| 6 | Dashboard 列表 / Tag Cloud 无可点击导航 | ★ | C(Medium) X(Low) G(Medium) — CLAUDE.md t3 |
| 7 | 前端硬编码中文绕过 i18n（5+ 个组件） | ☆ | C(Medium 含 5 文件清单) X(Low) |

### 三方独家发现汇总（共 18 项）

**Claude 独家（10）**：
- ◯ `/auth/token` + `/auth/register` 无速率限制（升 Critical）
- ◯ **`should_initialize_database()` 让已有库不应用 Alembic 迁移**（NEW Critical — 部署 footgun）
- ◯ `_create_all` vs Alembic schema 不保证一致（NEW High）
- ◯ Codeforces / LeetCode `follow_redirects=True` 防御性 SSRF
- ◯ `/import/v3` 无 payload 体积 / 数组上限 OOM
- ◯ `requirements.txt` 14/17 个直接依赖未钉版本
- ◯ CORS `allow_methods=["*"]` + credentials 配单 origin 部署陷阱
- ◯ 401 拦截器 logout → import → navigate 异步竞态窗口
- ◯ `OLD_USER_INITIAL_PASSWORD` 默认值即 insecure（fail-fast 副作用）
- ◯ localStorage `coderecall_ever_imported_${userId}` logout 不清理

**Codex 独家（5）**：
- ◯ Alembic 迁移失败被 `except Exception` 吞掉并 fallback `create_all`
- ◯ 公开文档（README / api-contract / deployment-guide）与运行时 API 严重漂移
- ◯ Review GET 接口存在隐藏写操作（`completed_count` / `ended_at` 在 GET 路径 commit）
- ◯ 关键测试绕过 Alembic：`test_cross_user_isolation` / `test_import_export_v3` 用 `create_all` 或 `force_fallback=True`
- ◯ Vite 构建产物 `ts.worker` ≈ 7.0 MB / 主 chunk ≈ 739 KB / 分包被路由耦合打穿
- ◯ 前后端 `MAX_TITLE_LEN` 不一致（前端 200 / 后端 500）
- ◯ `Category` / `Tag` schema 缺长度约束
- ◯ README `npm run type-check` 脚本不存在
- ◯ Stats 页 `tz_offset {n}m` 调试 Tag 直接暴露给用户

**Gemini 独家（4）**：
- ◯ `mistakes` 列表 API 返回完整 `stem_markdown`，列表流量爆炸
- ◯ AI SSE 解析时 `try/catch { /* skip */ }` 静默吞噬调试信息
- ◯ JWT 密钥检查 `app_env == "test"` 字符串匹配脆弱
- ◯ 数据导入时 skip 的去重数量无 UI 反馈

---

## 1. Critical 综合清单（5 项）

### [C-001] service / repository 层 `user_id: Optional[int] = None` 残留 30+ 函数 ★
- **维度**：安全 / 架构
- **来源**：Claude C-002 (Critical, 量化 30+ 函数) · Codex M-002 (Medium, 列 6 文件) · Gemini M-001 (Medium)
- **共识度**：★ 三方共识，**严重度判定有分歧**（Claude 升 Critical，理由：CLAUDE.md m3 严重低估）
- **量化文件**（Claude 完整 grep 后）：
  - `taxonomy_service.py` 13 个函数全部 Optional：`:52 :59 :73 :102 :121 :152 :170 :177 :187 :197 :221 :235 :259`
  - `mistake_service.py` 5 个函数：`:38 :70 :77 :111 :159`
  - `stats_service.py` 5 个函数：`:79 :145 :193 :224 :301`
  - `services/review/__init__.py` 9 个函数：`:37 :80 :88 :104 :150 :173 :190 :204 :244`
  - `import_export_service.py` 6 个函数：`:67 :133 :195 :358 :396 :725`
- **问题**：所有 user-scoped 业务函数都允许漏传 user_id 退化为全局查询；当前路由层都正确传 `current_user.id`，但任何 cron / management script / Python REPL 都能立即跨租户访问。
- **修复建议**：
  ```python
  # before
  def list_tags(db: Session, user_id: Optional[int] = None) -> list[Tag]: ...
  # after
  def list_tags(db: Session, *, user_id: int) -> list[Tag]: ...
  def list_tags_for_admin(db: Session) -> list[Tag]: ...  # 全局能力独立命名
  ```
- **预估工时**：5-7 小时（30+ 函数 + 调用方 + 测试），分批：review → stats → mistakes → taxonomy → import_export

### [C-002] `should_initialize_database()` 让已有库不自动应用 Alembic 迁移 ◯ Claude 独家 (NEW)
- **维度**：架构 / 部署 / 数据
- **来源**：Claude C-003 独家
- **文件**：`backend/app/db/init_db.py:59-72` + `backend/app/main.py:14-18`
- **问题**：lifespan 只在 `should_initialize_database()` 为 True 时跑迁移；但该函数对已有 sqlite 文件直接 `return not db_path.exists()` ⇒ False。**结果：部署升级时新 schema 完全不会被应用，必须运维手动 `alembic upgrade head`，且这一步在 release-runbook 没明示。**
  ```python
  # init_db.py:59-72
  def should_initialize_database(...) -> bool:
      ...
      return not db_path.exists()  # 已有库 → False → 不进 initialize
  ```
- **影响**：
  - 部署升级写完 0009 / 0010 migration 后**重启后端完全无效**
  - 与 Codex H-001（Alembic 失败被吞）**是不同问题**：H-001 是失败处理，C-002 是根本不跑
  - 用户已有生产环境跑 0008，未来加新 schema 会踩这个坑
- **修复建议**：lifespan 改成总是 upgrade 到 head，已有库失败必须 fail-fast：
  ```python
  @asynccontextmanager
  async def lifespan(_: FastAPI):
      try:
          command.upgrade(_build_alembic_config(settings.database_url), "head")
      except Exception:
          if should_initialize_database():  # 仅空库允许 fallback
              _create_all(settings.database_url)
          else:
              raise  # 已有库失败必须 fail-fast
      _ensure_old_user(settings.database_url)
      yield
  ```
  并在 `release-runbook.md` 加明示。
- **预估工时**：4 小时

### [C-003] `/auth/token` 与 `/auth/register` 无速率限制 ◯ Claude 独家
- **维度**：安全
- **来源**：Claude C-001 · Gemini I-002 提及但未单列
- **文件**：`backend/app/api/routes/auth.py:57-71`、`backend/app/main.py:21-31`
- **问题**：grep 整个项目无 rate limit / slowapi / fastapi-limiter / 中间件级 throttling。bcrypt 慢哈希（约 100 次/秒）虽提供基础成本，但攻击者可对特定高价值用户精准爆破。同时 `/api/v1/ai/analyze/stream` 和 `/import/v3` 也无限流，与 [C-005] 配合可作 DoS。
- **修复建议**：用 slowapi
  ```python
  @router.post("/token")
  @limiter.limit("10/minute; 100/hour")
  def login_route(request: Request, ...): ...

  @router.post("/register")
  @limiter.limit("3/hour; 10/day")
  def register_route(request: Request, ...): ...
  ```
- **预估工时**：3 小时

### [C-004] `authStore.initializeAuth()` `set(parsed)` 任意字段注入 ★
- **维度**：安全 / 架构
- **来源**：Claude C-004 (Critical) · Codex M-001 (Medium) · Gemini H-002 (High)
- **共识度**：★ 三方共识（严重度判定 Critical/High/Medium 都有）
- **文件**：`frontend/src/stores/authStore.ts:43`
- **问题**：localStorage JSON 反序列化结果只校验 `parsed?.token && parsed?.userId` 存在，整个对象 `set(parsed)` 进 Zustand。配合 [C-005] localStorage 信任问题，是 attack chain 放大器。
- **修复建议**：精确字段解构
  ```ts
  set({
      token: typeof parsed.token === "string" ? parsed.token : null,
      username: typeof parsed.username === "string" ? parsed.username : null,
      userId: typeof parsed.userId === "number" ? parsed.userId : null,
  });
  ```
- **预估工时**：0.5 小时（CLAUDE.md 已知 m2，1 行修复）

### [C-005] Token 存 localStorage + 7 天有效期 + 无 revoke ★
- **维度**：安全
- **来源**：Gemini C-001 (Critical) · Claude H-006 (High) · Codex 评分 C 但未单列
- **文件**：`frontend/src/stores/authStore.ts:22`、`backend/app/core/config.py:44`
- **问题**：JWT 存 localStorage（任何 XSS 可读），有效期 7 天 (`access_token_expire_minutes=10080`)，无 refresh token，无 token revocation。
- **修复建议**（短/长两阶段）：
  - **短期（8 小时）**：access_token 30-120 分钟 + 加 token_jti 黑名单表 + axios 自动 silent refresh
  - **长期（24 小时）**：HttpOnly Cookie + refresh_token + CSRF 双 token + 前端不再自管 token
- **预估工时**：短期 8 小时 / 长期 24 小时

---

## 2. High 综合清单（9 项）

### [H-001] Alembic 迁移失败被 `except Exception` 吞掉 fallback `create_all` ◯ Codex 独家
- **来源**：Codex H-001
- **文件**：`backend/app/db/init_db.py:42-46`
- **注意**：与 [C-002] 不同问题。这条是"迁移失败的处理"，C-002 是"根本不跑"。两者一起改才能闭环。
- **修复建议**：参见 [C-002] 一并修复。
- **工时**：含在 [C-002] 4 小时内

### [H-002] 公开文档与运行时 API 严重漂移 ◯ Codex 独家
- **来源**：Codex H-002 · Claude M-011
- **文件**：`README.md:100`、`docs/api-contract-current.md:4` / `:26`、`docs/deployment-guide.md:13`
- **问题**：auth 路由文档 `/auth/*` 实际 `/api/v1/auth/*`；register 响应 schema 不一致；review 端点已删除文档还在。
- **修复**：FastAPI OpenAPI 单一事实源，redocly 渲染对外文档。
- **工时**：4 小时

### [H-003] LeetCode/CF provider `follow_redirects=True` 防御性 SSRF ◯ Claude 独家
- **来源**：Claude H-001
- **文件**：`backend/app/services/problem_import_service.py:30-34`
- **问题**：当前用 `_PROVIDERS_BY_HOST` 白名单了 host，但 redirect 后的 URL 不再检查。CF/LeetCode 子域 takeover 或 DNS rebinding 配合可触发 SSRF（理论性，但收紧成本极低）。
- **修复**：`follow_redirects=False` + 手动验证 Location 头白名单
- **工时**：2 小时

### [H-004] `/import/v3` 无 payload 体积 / 数组上限 → OOM ◯ Claude 独家
- **来源**：Claude H-002
- **文件**：`backend/app/schemas/import_export.py:144-147`
- **问题**：所有 list 字段 `Field(default_factory=list)` 无 `max_length`，main.py 也无 body size 中间件。单 POST 100 MB JSON → 内存解析 → list[ExportMistake] 实例化 → OOM。配合 [C-003] 无限流可作 DoS。
- **修复**：Pydantic `Field(max_length=10000/100000)` + Starlette body size middleware
- **工时**：3 小时

### [H-005] `requirements.txt` 14/17 个依赖未钉版本 ◯ Claude 独家
- **来源**：Claude H-003
- **文件**：`backend/requirements.txt`
- **问题**：实测仅 `eval_type_backport==0.3.1` 与 `bcrypt==4.0.1` 钉死，其他 15 个直接依赖（fastapi/uvicorn/sqlalchemy/alembic/pydantic/...）全部不带版本。
- **修复**：`uv pip compile requirements.in` 全量钉版本 + hash；CI 加 `pip-audit`
- **工时**：1.5 小时

### [H-006] `stats_service.py` 全量拉表 + Python 内存聚合 ★
- **来源**：Gemini H-001 · Claude H-004 · Codex M-004（CLAUDE.md t1）
- **文件**：`stats_service.py:79 :89-90 :145 :155-156 :193 :200 :235 :310`
- **问题**：5 个函数全部 `db.scalars(...).all()` 拉表后 Python 循环聚合。
- **修复**：count 用 `func.count()`；heatmap 用 `GROUP BY func.date()`；streak 用递归 CTE 或单次 SQL；补 `(user_id, shown_at)` / `(user_id, next_review_at)` 复合索引。
- **工时**：6-8 小时

### [H-007] Review GET 接口隐藏写库（HTTP 语义违反） ☆
- **来源**：Codex M-003 · Claude H-005（升 High）
- **文件**：`services/review/__init__.py:88-92` `:97-100` `:150` `:204`
- **问题**：`_progress_for_session` 与 `_mark_session_completed_if_needed` 在 GET 路径里 `db.commit()`。违反 RFC 7231 §4.2.1 安全方法语义。浏览器预取 / Service Worker / CDN 探测 / APM replay 都可能改写 session。
- **修复**：把写操作移到 `submit_result()` (POST) 或拆 `POST /sessions/{id}/finalize`
- **工时**：3 小时

### [H-008] 关键测试绕过 Alembic（无法保护 0007/0008 迁移） ☆
- **来源**：Codex M-008 · Claude H-007（升 High）
- **文件**：`backend/tests/test_cross_user_isolation.py:25` · `test_import_export_v3.py:31` `:137`
- **问题**：跨用户隔离 / v3 导入导出测试用 `Base.metadata.create_all()` 或 `force_fallback=True` 直接 SQLAlchemy 建表，跳过 Alembic 0007/0008。**结果**：migration 脚本本身的索引、外键、唯一约束错误在 160 passed 下溜走。
- **修复**：提供 `alembic_head_engine` fixture，关键测试至少跑一遍 alembic schema。
- **工时**：3 小时

### [H-009] `_create_all` 与 Alembic 产生的 schema 不保证一致 ◯ Claude 独家
- **来源**：Claude H-008
- **文件**：`backend/app/db/init_db.py:29-31` · `alembic/versions/0007_*` · `0008_uuid_composite_unique.py`
- **问题**：`Base.metadata.create_all()` 只按 Model `__table_args__` 建表，但 0007/0008 包含 `op.create_index(unique=True)` / `op.add_column` / `op.create_foreign_key` 等手写操作。如果 Model 定义不完整声明，create_all 与 alembic head 的 schema **不一致**。
- **影响**：测试用 create_all + 生产用 alembic upgrade，两条路径分叉风险倍增；与 [C-002] 共振放大。
- **修复**：检查 Model `__table_args__` 是否完整声明 0007/0008 全部约束；或废除 `_create_all`，统一只用 Alembic（含测试）。
- **工时**：2 小时（含 schema diff 验证）

---

## 3. Medium 综合清单（13 项）

| ID | 来源 | 问题 | 文件:行 | 工时 |
|----|------|------|---------|------|
| M-001 | C◯ | CORS `allow_methods=["*"]` + credentials 单 origin 部署陷阱 | `main.py:23-29` | 1h |
| M-002 | X+C ☆ | api.ts 动态 import("../routes") 让 Vite 分包失效（含 Monaco 7MB 超阈值） | `services/api.ts:62`、`routes.tsx`、`CodeEditor/CodeEditorInner.tsx:2` | 5h |
| M-003 | C◯ | 401 拦截器 logout → import → navigate 异步竞态闪屏 | `services/api.ts:59-64` | 与 M-002 合并 |
| M-004 | X+C ☆ | Category/Tag schema 缺 `name` 长度约束 | `schemas/category.py:7`、`schemas/tag.py:7` | 1h |
| M-005 | ★ 三方 | Dashboard 列表 / Tag Cloud 无可点击导航（CLAUDE.md t3） | `Dashboard/index.tsx:209-235` | 1h |
| M-006 | G+C ☆ | `list_mistakes` 返回完整 stem_markdown 列表流量爆炸 | `routes/mistakes.py:34`、`schemas/mistake.py` | 2h |
| M-007 | ★ 三方 | streak toast `getStatsOverview` 无 `.catch`（CLAUDE.md m1） | `pages/Review/index.tsx:95-112` | 0.2h |
| M-008 | X+C ☆ | 5+ 个组件硬编码中文绕过 i18n | `ProblemUrlImporter.tsx:21`、`VariantDrawer.tsx:33`、`MistakeEditor/index.tsx:183`、`ReviewPageState.tsx:25`、`OnboardingPage.tsx` | 2h |
| M-009 | C◯ | `OLD_USER_INITIAL_PASSWORD` 默认值 `"coderecall"` 即在 insecure set 中 → 首次启动必失败 | `core/config.py:18-23 :45 :96-100` | 1h |
| M-010 | X+C ☆ | 前后端 `MAX_TITLE_LEN` 不一致（前端 200 / 后端 500） | `MistakeEditor/index.tsx:238`、`schemas/mistake_constraints.py:5` | 1h |
| M-011 | X+C ☆ | Stats 页 `tz_offset {n}m` 调试 Tag 直接暴露给用户 | `pages/Stats/index.tsx:122` | 0.3h |
| M-012 | G+C ☆ | AI SSE 解析 `try/catch { /* skip */ }` 静默吞噬调试信息 | `useAiAnalysisStream.ts:109 :122 :147` | 0.5h |
| M-013 | C◯ | localStorage `coderecall_ever_imported_${userId}` logout 不清理污染下一用户 | `MistakeList/index.tsx:208-213` | 0.5h |

---

## 4. Low 综合清单（7 项）

| ID | 来源 | 问题 | 文件:行 | 工时 |
|----|------|------|---------|------|
| L-001 | X+C ☆ | README `npm run type-check` 脚本不存在 | `README.md:133`、`frontend/package.json:6` | 0.3h |
| L-002 | C◯ | `errors.py` `Optional[Any]` / `dict[str, Any]` 错误结构未严格 schema 化 | `api/errors.py:6 :18` | 1h |
| L-003 | C◯ | `_ensure_old_user` 每次启动开新 engine + Session，未复用 SessionLocal | `db/init_db.py:51-56` | 0.5h |
| L-004 | C◯ | `useAiAnalysisStream.ts:72` `as unknown` 是 src/ 唯一 unknown 强转，可改 Zod 验证 | `useAiAnalysisStream.ts:72` | 1h |
| L-005 | C◯ | v3 import dedup 读全部 existing UUIDs 进内存，大库会慢 | `import_export_service.py` | 1h |
| L-006 | G◯ | 重复导入 skip 数无 UI 反馈 | `pages/ImportExport` | 1h |
| L-007 | G◯ | JWT secret 检查 `app_env=="test"` 字符串匹配脆弱 | `core/config.py:72-87` | 1h |

---

## 5. 改进建议（7 项，非问题）

| ID | 来源 | 说明 |
|----|------|------|
| I-001 | X+C | OpenAPI auto-gen 替代手写 api-contract-current.md |
| I-002 | X+C | Playwright e2e 覆盖 register → review → export v3 全链路 |
| I-003 | X+C | 前后端共享校验常量（codegen 驱动） |
| I-004 | G | PWA / Service Worker（配合移动端） |
| I-005 | G+C | rate limiting（auth + AI + import）→ 见 [C-003] |
| I-006 | G | Playwright e2e |
| I-007 | C | CI 加 bandit / pip-audit / npm audit / chunk size 检查 |

---

## 6. 修复优先级矩阵（前 15 项推荐执行顺序）

按"严重度 × 工时 × 共识度"加权排序：

| 顺序 | ID | 严重度 | 工时 | 共识 | 推荐时机 |
|------|-----|--------|------|------|----------|
| 1 | M-007 | M | 0.2h | ★ | 立即（已知 m1，1 行） |
| 2 | C-004 | C | 0.5h | ★ | 立即（已知 m2，1 行） |
| 3 | M-013 | M | 0.5h | ◯ | 立即（logout 清 localStorage 1 行） |
| 4 | M-009 | M | 1h | ◯ | 本周（OLD_USER 默认值改空） |
| 5 | M-011 | M | 0.3h | ☆ | 本周（删除 tz_offset Tag） |
| 6 | H-005 | H | 1.5h | ◯ | 本周（钉版本） |
| 7 | C-003 | C | 3h | ◯ | 本周（auth 限流） |
| 8 | H-003 | H | 2h | ◯ | 本周（CF SSRF） |
| 9 | H-004 | H | 3h | ◯ | 本周（/import OOM） |
| 10 | C-002 + H-001 | C+H | 4h | ◯+◯ | 本周（lifespan 改 + Alembic fail-fast 一并修） |
| 11 | C-001 | C | 5-7h | ★ | 本迭代（user_id 必填，分批改 30+ 函数） |
| 12 | H-007 | H | 3h | ☆ | 本迭代（review GET 副作用） |
| 13 | H-002 | H | 4h | ◯ | 本迭代（文档对齐 OpenAPI） |
| 14 | H-006 | H | 6-8h | ★ | 本迭代（stats 下推 SQL + 索引） |
| 15 | C-005 | C | 8h(短)/24h(长) | ★ | 双月（HttpOnly Cookie 改造） |

**累计估算**：
- 立即（30 分钟）：1.2 小时（3 个 1 行修复）
- 本周（5 工作日）：约 14 小时（M-009 / M-011 / H-005 / C-003 / H-003 / H-004 / C-002+H-001）
- 本迭代（10 工作日）：约 18-22 小时（C-001 / H-007 / H-002 / H-006）
- 双月：8-24 小时（C-005 + 改进项）
- **累计 41-58 小时**（不含全部 Medium/Low/改进）

加上全部 Medium（约 16 小时）+ Low（5.8 小时）= 总计 **约 63-80 小时**。

---

## 7. 三方报告差异分析与盲区

### 评分差异根因

- **Codex 给 C** 的核心理由：发现"运行时真相 vs 外部契约"分叉（迁移 fallback / GET 副作用 / 文档漂移 / 构建产物超阈值）。这些是单点测试通过但系统性脆弱的信号，扣分严苛。
- **Gemini 给 B** 的核心理由：核心安全已修复 + 测试覆盖率好，但前端信任假设（localStorage + set(parsed)）放大 XSS 影响面是显眼减分项。
- **Claude 给 B-** 的核心理由：发现 4 个独立未在 CLAUDE.md 记录的 Critical/High（限流、已有库不迁移、CF SSRF、import OOM），同时识别出 user_id=None 实际范围（30+）远超 m3 估计。

**综合 B-** 的判定逻辑：项目核心业务和测试是站得住的，整体仍在可上线区间，但上线前必须把 5 个 Critical（特别是 [C-001] [C-002] [C-003]）+ 4 个 High（[H-001] [H-003] [H-004] [H-008]）处理完。

### 三方共同盲区（建议后续做）

- 没人系统跑 `bandit` / `pip-audit` / `npm audit` 静态扫描
- 没人验证生产配置（CSP / HSTS / X-Frame-Options 缺失）
- 没人测前端 Markdown 渲染器对 XSS payload 的过滤（KaTeX / markdown-it 配置）
- 没人测 SQLite WAL / 连接池配置（生产 lock 风险）
- 没人压测 stats 接口在 10K+ ReviewLog 下的延迟
- 没人做浏览器手工 e2e
- 没人验证真实 LLM provider 调用错误处理

→ 这些是 v2 审阅可以补做的扫描项。

---

## 8. 推荐执行计划

### 立即（30 分钟）— 3 个 1 行修复
- ✅ M-007：streak toast `.catch(() => {})`
- ✅ C-004：authStore 精确字段解构
- ✅ M-013：logout 清理 `coderecall_ever_imported_${userId}`

### 本周（5 工作日 / ~14 小时）— 安全护栏
- M-009：OLD_USER 默认值改空（避免 fail-fast footgun）
- M-011：删除 Stats 页 tz_offset 调试 Tag
- H-005：requirements.txt 钉版本
- C-003：加 slowapi 限流（auth + ai + import）
- H-003：CF/LeetCode 关闭 follow_redirects
- H-004：/import/v3 加 body size + 数组长度
- C-002 + H-001：lifespan 改成总跑 alembic upgrade，已有库失败 fail-fast，**这一项最关键**

### 本迭代（10 工作日 / ~22 小时）— 结构性问题
- C-001：service `user_id` 改必填（30+ 函数，分批 review → stats → mistakes → taxonomy → import_export）
- H-007：review GET 去除写操作
- H-002：文档对齐 FastAPI OpenAPI
- H-006：stats 下推 SQL + 复合索引
- M-001 ~ M-013：Medium 全包

### 双月（与体验升级一起）
- C-005：HttpOnly Cookie 改造（短期 silent refresh + 长期 cookie based）
- I-001 ~ I-007：改进项

---

## 9. 报告元信息

- **综合者**：Claude（主对话）
- **综合日期**：2026-04-30
- **来源报告**:
  - `claude-report.md`（**Claude 完整版**，主对话用 Read/Glob/Grep 直接扫码后产出，646 行 / 28 KB；上一版仅摘要的归档为 `claude-report-summary-only.md`）
  - `codex-report.md`（Codex 通过 omc ask 产出，227 行 / 19 KB，含构建产物实测）
  - `gemini-report.md`（Gemini 通过 omc ask 产出，149 行 / 11 KB，UX/前端视角强）
- **三方独立性说明**：每份子报告独立产出。Claude 完整版在已读过 final-report.md 上一版的情况下产出，独立性不完美但贡献集中在 [C-001] 量化范围 / [C-002] 已有库不迁移 / [H-009] schema 漂移 / [M-001] CORS 部署陷阱 / [M-003] 401 竞态 / [M-009] OLD_USER footgun / [M-013] localStorage 残留 这几个独家发现。
- **未做事项**：
  - 未运行 bandit / pip-audit / npm audit
  - 未做浏览器手工 e2e
  - 未压测 SQLite 大数据量
  - 未测真实 LLM provider 调用
- **报告产出物路径**：`/Users/hfish/Claude_chat/协同码力/docs/audit/2026-04-29/`
  - `_prompt.md` 共享审阅指令
  - `claude-report.md` Claude 完整审阅报告（**当前**）
  - `claude-report-summary-only.md` Claude 摘要版（归档，参考用）
  - `codex-report.md` Codex 独立报告
  - `gemini-report.md` Gemini 独立报告
  - `final-report.md` 本综合报告（**当前重做版**）

---

## 附录 A — 三方独立 Top 5 对比表

| 排名 | Claude | Codex | Gemini |
|------|--------|-------|--------|
| 1 | **已有库不应用 Alembic 迁移**（C-003 NEW） | Alembic 失败被吞 + fallback（H-001） | Token 存 localStorage（C-001） |
| 2 | auth 无速率限制（C-001） | 文档与 API 严重漂移（H-002） | stats 内存聚合（H-001） |
| 3 | service user_id=None（30+ 函数, C-002） | service user_id=None（M-002） | authStore 状态注入（H-002） |
| 4 | CF SSRF（H-001） | review GET 写库（M-003） | service user_id=None（M-001） |
| 5 | /import/v3 OOM（H-002） | stats 内存聚合（M-004） | Dashboard 无导航（M-002） |

→ Claude 偏重**外部攻击面 + 部署陷阱**（限流/SSRF/payload/供应链/迁移）；Codex 偏重**运行时一致性**（迁移/GET/文档/构建）；Gemini 偏重**前端信任假设**（localStorage/状态注入）。三视角互补，没有重大遗漏。

## 附录 B — 与 CLAUDE.md 已知技术债的对照

| 编号 | CLAUDE.md 描述 | 三方核实 | 综合判定 | 在本报告中的位置 |
|------|----------------|----------|----------|------------------|
| m1 | streak toast 无 .catch | 三方确认 | Medium | M-007 |
| m2 | authStore set(parsed) | 三方确认 | **Critical（升级）** | C-004 |
| m3 | service user_id=None 残留 | 三方确认 | **Critical（升级 + 量化 30+）** | C-001 |
| t1 | stats_service 内存聚合 | 三方确认 | High | H-006 |
| t2 | Token 存 localStorage | 三方确认 | **Critical（升级）** | C-005 |
| t3 | Dashboard 列表无导航 | 三方确认 | Medium | M-005 |
| t4 | Register 前端长度校验 | — | ✅ 已修复（不复现） | — |

CLAUDE.md 当前 P2/P3 的 6 项技术债，三方都确认存在；其中 m2 / m3 / t2 三项的实际严重度被 CLAUDE.md 明显低估，建议升级。
