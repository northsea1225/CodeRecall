# Claude 全栈审阅报告 — CodeRecall（2026-04-29 / 完整版）

> **审阅说明**：本报告是 Claude 视角的**完整版**。原 omc ask claude 通道因单轮 advisor 模式无法落盘完整 issue 列表，仅产出摘要（已归档至 `claude-report-summary-only.md`）；之前两次 Agent lane 因 Calcium-Ion 网关 nil pointer panic 失败。本完整版由主对话 Claude 用 Read/Glob/Grep 工具直接扫描代码后产出。
>
> **Claude 视角的差异化优势**（贯穿全文）：
> 1. 跨文件因果关系追踪（state → UI → API 一致性）
> 2. 协议层一致性（SSE / JWT / Pydantic schema vs TS 类型）
> 3. 抽象合理性（service / store / hook 边界）
> 4. 类型系统漏洞（any / Optional / unknown 滥用）
> 5. 外部攻击面（限流 / SSRF / payload bomb / 供应链）

## 0. 执行摘要

- **总体评分**：B-（核心安全护栏到位，但有 5 项结构性问题需要在上线前认真处理）
- **总问题数**：Critical 4 · High 8 · Medium 13 · Low 6 · 改进 5
- **Top 5 风险**（按严重度排序）：
  1. `[C-003]` `should_initialize_database()` 让已有库**根本不应用 Alembic 迁移** — `backend/app/db/init_db.py:59-72`
  2. `[C-001]` `/auth/token` 与 `/auth/register` 无速率限制 — `backend/app/api/routes/auth.py:57-71`
  3. `[C-002]` service 层 `user_id: Optional[int] = None` 残留 **30+ 个函数**（远超 CLAUDE.md m3 估计）
  4. `[H-001]` CF/LeetCode provider `follow_redirects=True` 防御性 SSRF — `backend/app/services/problem_import_service.py:32`
  5. `[H-002]` `/import/v3` 无 payload 体积 / 数组上限 → 单 POST OOM — `backend/app/schemas/import_export.py:144-147`

- **审阅者视角的最有价值发现**（区别于 Codex / Gemini）：
  - **C-003 已有库不跑迁移**：Codex 注意到 Alembic 失败被吞掉，但忽略了**已有 sqlite 库根本不会进入 initialize 路径**（`should_initialize_database` 直接 `return not db_path.exists()`）。这意味着部署升级时，新 schema 必须由运维**手动**执行 `alembic upgrade head`，而 CLAUDE.md 与 release-runbook 都没明说这一步。这是个比 H-001 (Alembic 失败 fallback) 更隐蔽且更高频的 footgun。
  - **C-002 量化范围**：grep 结果显示残留函数远超 m3 描述的"多个 service 文件"，实际是 `taxonomy_service.py` 的 13 个函数 + `mistake_service.py` 6 个 + `stats_service.py` 6 个 + `review/__init__.py` 9 个 + `import_export_service.py` 6 个，**累计 30+**。CLAUDE.md 把它列为 P2 严重低估。
  - **C-001 速率限制完全缺失**：grep 整个 main.py + auth.py 没有任何 rate limit / slowapi / fastapi-limiter，意味着不只是 auth 暴破，AI 接口、import/v3、registry 都暴露在 DoS 面前。
  - **类型系统漏洞汇总**：前端 `any` / `@ts-ignore` 滥用极少（搜全 src 只有 `useAiAnalysisStream.ts:72` 一处 `as unknown`）— 这是亮点；但后端有 8+ 处 `Optional[Any]` / `dict[str, Any]` 在错误响应路径上，错误结构未被严格 schema 化。

## 1. 维度评分总览

| 维度 | 得分 | 关键发现 |
|------|------|----------|
| 安全 | C+ | 鉴权链路扎实（Phase B 加固完整），但缺速率限制、CF SSRF、payload 体积无上限、CORS allow_credentials + allow_headers=`*` 组合 |
| 质量 | B | 类型注解相对完整；后端错误响应类型化不够；前端硬编码中文 5+ 处绕过 i18n |
| 架构 | C+ | 路由 / service / repository 分层尚清晰，但 service 层"礼貌默认 user_id=None"是反共生模式；review GET 路径有副作用；启动期初始化判断条件过严（已有库不会迁移） |
| 性能 | C | stats_service 全量加载 + Python 内存聚合（已知 t1）；前端构建产物 ts.worker ≈ 7 MB；list_mistakes 返回完整 stem_markdown |
| UX | B- | 错误态/空态完整度高；但 Dashboard 列表无导航（已知 t3）；硬编码中文；移动端断点尚未做 |
| 文档 | C | CLAUDE.md 同步性高；但 README/api-contract/deployment-guide 与运行时存在路径漂移；部署期手动 `alembic upgrade head` 这一关键步骤未在文档明示 |
| 测试 | B- | 后端 160 用例全绿、跨用户隔离覆盖好；但关键测试用 `create_all` 绕过 Alembic（无法保护 0007/0008 迁移）；前端缺 e2e；SSE 解析无 unit test |

## 2. Critical 问题（上线阻塞 / 必须立即处理）

### [C-001] `/auth/token` 与 `/auth/register` 无速率限制

- **维度**：安全
- **文件**：`backend/app/api/routes/auth.py:57-71`、`backend/app/main.py:21-31`
- **问题描述**：grep 整个项目没有任何 rate limit / slowapi / fastapi-limiter / 中间件级 throttling。auth 接口完全暴露在网络上，没有 IP 维度或用户维度的限流。
  ```python
  @router.post("/token", response_model=AuthOut)
  def login_route(form_data: OAuth2PasswordRequestForm = Depends(), ...):
      user = authenticate_user(db, form_data.username, form_data.password)
      if user is None:
          raise_api_error(401, "invalid_credentials", ...)
      return _auth_response(user)
  ```
- **影响**：
  - 在线暴破：bcrypt 慢哈希提供约 100 次/秒 的成本上限，但攻击者可对特定高价值用户精准爆破；30 天内尝试 2.6 亿次密码组合，足以击穿 8 位简单密码。
  - 注册刷量：恶意脚本可在 1 分钟内注册数万账号污染数据库（特别是 old_user 之外的"垃圾用户"会消耗 SQLite 索引存储）。
  - AI 接口刷量：`/api/v1/ai/analyze/stream` 同样无限流，恶意触发会消耗 LLM API 余额。
  - import/v3 配合 H-002 可作 OOM DoS。
- **复现路径**：`for i in {1..1000}; do curl -X POST http://host/api/v1/auth/token -d "username=admin&password=$i"; done` 即可触发完整 1000 次尝试。
- **修复建议**：
  ```python
  # backend/requirements.txt
  slowapi>=0.1.9

  # backend/app/main.py
  from slowapi import Limiter, _rate_limit_exceeded_handler
  from slowapi.errors import RateLimitExceeded
  from slowapi.util import get_remote_address

  limiter = Limiter(key_func=get_remote_address)
  app.state.limiter = limiter
  app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

  # backend/app/api/routes/auth.py
  from slowapi import Limiter
  from app.main import limiter

  @router.post("/token")
  @limiter.limit("10/minute; 100/hour")
  def login_route(request: Request, ...): ...

  @router.post("/register")
  @limiter.limit("3/hour; 10/day")
  def register_route(request: Request, ...): ...
  ```
- **预估工时**：3 小时（含中间件接入 + 测试 + 反向代理 X-Forwarded-For 处理）

### [C-002] service / repository 层 `user_id: Optional[int] = None` 残留 30+ 个函数

- **维度**：安全 / 架构
- **文件**：覆盖 5 个 service 文件 30+ 个函数，举关键证据：
  - `backend/app/services/taxonomy_service.py:52` `list_categories`、`:59` `get_category`、`:73` `list_categories_paginated`、`:102` `create_category`、`:121` `update_category`、`:152` `delete_category`、`:170` `list_tags`、`:177` `get_tag`、`:187` `get_tags_by_names`、`:197` `get_or_create_tags`、`:221` `create_tag`、`:235` `update_tag`、`:259` `delete_tag`（**13 个函数全部 user_id=None**）
  - `backend/app/services/mistake_service.py:38` `list_mistakes`、`:70` `get_mistake`、`:77` `create_mistake`、`:111` `update_mistake`、`:159` `delete_mistake`
  - `backend/app/services/stats_service.py:79` `get_overview`、`:145` `get_trend`、`:193` `get_heatmap`、`:224` `get_top_weak`、`:301` `get_tag_radar`
  - `backend/app/services/review/__init__.py:37` `_get_session`、`:80` `_count_completed`、`:88` `_progress_for_session`、`:104` `start_session`、`:150` `get_next_item`、`:173` `submit_result`、`:190` `get_reveal`、`:204` `get_summary`、`:244` `get_due_count`
  - `backend/app/services/import_export_service.py:67` `export_data`、`:133` `export_mistakes_v2`、`:195` `import_data`、`:358` `import_logs_v3`、`:396` `import_data_v3`、`:725` `export_data_v3`
- **问题描述**：CLAUDE.md m3 把这描述为"多个 service 文件残留"，实际 grep 出来的覆盖面是**所有 user-scoped 业务函数**。当前路由层都正确传 `current_user.id`，但任何内部调用方（cron / management command / Python REPL / 后台任务 / 未来管理面板）只要漏传，就立即变成全用户全局查询。
  ```python
  # taxonomy_service.py:52
  def list_categories(db: Session, user_id: Optional[int] = None) -> list[Category]:
      stmt = select(Category)
      if user_id is not None:
          stmt = stmt.where(Category.user_id == user_id)
      # else: 返回所有用户的 categories!
      return list(db.scalars(stmt).all())
  ```
- **影响**：
  - **静默越权**：写一行 `from app.services.taxonomy_service import list_tags; list_tags(db)` 就能拿到所有用户的标签。
  - **不可被 lint 自动捕获**：默认参数让调用方"看起来正确"，IDE 不会警告。
  - **跨任务污染**：未来加 admin 接口、数据迁移脚本、定时任务时极易引入越权。
- **复现路径**：
  ```python
  # 任意 Python REPL / Jupyter / management script
  from app.db.session import SessionLocal
  from app.services.taxonomy_service import list_tags
  with SessionLocal() as db:
      print(len(list_tags(db)))  # 返回全用户全局标签数，非任一用户
  ```
- **修复建议**：把 `user_id` 改为 keyword-only 必填，需要全局能力的拆出独立命名函数。
  ```python
  # before
  def list_tags(db: Session, user_id: Optional[int] = None) -> list[Tag]: ...

  # after
  def list_tags(db: Session, *, user_id: int) -> list[Tag]: ...
  def list_tags_for_admin(db: Session) -> list[Tag]: ...  # 独立命名
  ```
  路由层调用现在已经传 `user_id=current_user.id`，改造时只需移除 None 默认 + 加 keyword-only `*`。建议分批改：先 review service（最高频）→ stats → mistakes → taxonomy → import_export。
- **预估工时**：5-7 小时（30+ 函数 + 调用点 + 单元测试）

### [C-003] 已有 SQLite 库不会自动应用 Alembic 迁移

- **维度**：架构 / 部署 / 数据
- **文件**：`backend/app/db/init_db.py:59-72`、`backend/app/main.py:14-18`
- **问题描述**：`main.py` 的 lifespan hook 只在 `should_initialize_database()` 为 `True` 时才调用 `initialize_database()`，而 `should_initialize_database()` 对已有 sqlite 文件直接 `return not db_path.exists()` ⇒ False。
  ```python
  # init_db.py:59-72
  def should_initialize_database(database_url: Optional[str] = None) -> bool:
      ...
      database = url.database or ""
      if database in {":memory:", ""}:
          return True
      db_path = Path(database)
      ...
      return not db_path.exists()  # 已有文件返回 False
  ```
  ```python
  # main.py:14-18
  @asynccontextmanager
  async def lifespan(_: FastAPI):
      if should_initialize_database():  # ← 已有库为 False
          initialize_database()         # ← 不调用
      yield
  ```
- **影响**：
  - **部署升级时新 schema 不会被应用**。开发者写完 0009 / 0010 migration 后，重启后端服务**完全无效**，必须手动 `alembic upgrade head`。
  - 这一步在 `CLAUDE.md`、`docs/release-runbook.md`、`README.md` 都**没有明示**。
  - 与 H-001 (Codex 提的 Alembic 失败被吞) 是不同问题：H-001 是迁移失败的处理；C-003 是迁移**根本不跑**。
  - 用户已经在生产环境跑 0008，未来加新表 / 改约束都会踩这个坑。
- **复现路径**：
  1. 删除 `coderecall.db`，启动后端 → 自动 Alembic upgrade
  2. 加一条新 migration（如 `0009_add_index.py`）
  3. 重启后端 → schema 仍是 0008
  4. `alembic current` 显示 0008，但代码已经依赖 0009 的字段
- **修复建议**（两个方向，建议并行）：
  - **代码侧**：把 lifespan 改成总是检查 Alembic head：
    ```python
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        # 任何 sqlite 库（无论是否存在）都先 upgrade 到 head
        url = make_url(settings.database_url)
        if url.get_backend_name() == "sqlite":
            try:
                command.upgrade(_build_alembic_config(settings.database_url), "head")
            except Exception:
                if should_initialize_database():
                    _create_all(settings.database_url)  # 仅空库 fallback
                else:
                    raise  # 已有库失败必须 fail-fast，不能静默降级
            _ensure_old_user(settings.database_url)
        yield
    ```
  - **文档侧**：在 `release-runbook.md` 加 "升级部署：每次拉新版本后必须 `cd backend && alembic upgrade head` 然后重启"。
- **预估工时**：4 小时（代码改造 + 测试 + 文档同步）

### [C-004] `authStore.initializeAuth()` 任意字段注入

- **维度**：安全 / 架构
- **文件**：`frontend/src/stores/authStore.ts:43`
- **问题描述**：localStorage 的 JSON 反序列化结果只校验 `parsed?.token && parsed?.userId` 存在，然后整个对象 `set(parsed)` 进 Zustand。
  ```ts
  if (parsed?.token && parsed?.userId) {
      const parts = parsed.token.split(".");
      if (parts.length === 3) {
          ...
          if (typeof exp === "number" && exp * 1000 > Date.now()) {
              set(parsed);  // ← line 43，整个对象写入
              return;
          }
      }
  }
  ```
- **影响**：
  - **XSS 放大器**：配合 [C-006/Token 存 localStorage] 任何 XSS 入口都可注入额外字段（`role: "admin"`、`isVerified: true`、`teamId: 99`），即使后端 JWT 没赋予对应权限，前端 UI 检查可能据此放权。
  - **类型谎言**：interface AuthState 声明只有 `token / username / userId`，但运行时实际可包含任意字段，TS 类型与运行时不一致。
- **复现路径**：
  ```js
  // 浏览器 console
  localStorage.setItem('coderecall_token', JSON.stringify({
    token: '<合法 JWT>', username: 'a', userId: 1, role: 'admin', _bypass: true
  }));
  location.reload();
  // useAuthStore.getState() 包含 role 与 _bypass 字段
  ```
- **修复建议**：
  ```ts
  if (typeof exp === "number" && exp * 1000 > Date.now()) {
      set({
          token: typeof parsed.token === "string" ? parsed.token : null,
          username: typeof parsed.username === "string" ? parsed.username : null,
          userId: typeof parsed.userId === "number" ? parsed.userId : null,
      });
      return;
  }
  ```
- **预估工时**：0.5 小时（CLAUDE.md 已知 m2，1 行修复）

## 3. High 问题（本周修复）

### [H-001] LeetCode/CF provider 共用 `follow_redirects=True`，防御性 SSRF

- **维度**：安全
- **文件**：`backend/app/services/problem_import_service.py:30-34`
- **问题描述**：URL 预览路径用 `httpx.AsyncClient(follow_redirects=True)`，并把 client 传给所有 provider。当前已用 `_PROVIDERS_BY_HOST` 白名单了 host（leetcode/codeforces），但 redirect 后的 URL 不再被检查。
  ```python
  async with httpx.AsyncClient(
      timeout=httpx.Timeout(15.0, connect=5.0),
      follow_redirects=True,
  ) as client:
      return await provider.fetch_preview(stripped, client)
  ```
- **影响**：
  - 当前不可立即利用（CF/LeetCode 不会主动跳内网）。
  - 但只要 leetcode/codeforces 任一域名被 takeover、CDN 配错、或攻击者控制路径返回 302 到内网（如 `192.168.x.x:8000`、`169.254.169.254` AWS metadata），httpx 自动跟随。
  - DNS rebinding：客户端解析 `codeforces.com` 第一次得到公网 IP，redirect 到 `evil.com` 再 rebind 到内网。
- **复现路径**：理论性，需要控制 codeforces 子域。但防御性收紧成本极低。
- **修复建议**：
  ```python
  # 关闭自动 redirect，手动验证 Location 头
  async with httpx.AsyncClient(
      timeout=httpx.Timeout(15.0, connect=5.0),
      follow_redirects=False,
  ) as client:
      return await provider.fetch_preview(stripped, client)

  # 或者维护 redirect 白名单
  ALLOWED_REDIRECT_HOSTS = {"codeforces.com", "www.codeforces.com",
                            "leetcode.com", "leetcode.cn", "www.leetcode.com"}
  # provider 内手动循环 redirect，每跳验证 host
  ```
- **预估工时**：2 小时

### [H-002] `/import/v3` payload 无体积 / 数组长度上限

- **维度**：安全 / 性能
- **文件**：`backend/app/schemas/import_export.py:144-147`、`backend/app/api/routes/import_export.py`
- **问题描述**：`ImportPayloadV3` 所有 list 字段都用 `Field(default_factory=list)`，没有 `max_length`：
  ```python
  class ImportPayloadV3(BaseModel):
      categories: list[ImportCategory] = Field(default_factory=list)
      tags: list[ImportTag] = Field(default_factory=list)
      mistakes: list[ExportMistakeV3] = Field(default_factory=list)
      review_sessions: list[ExportReviewSession] = Field(default_factory=list)
      review_session_items: list[ExportReviewSessionItem] = Field(default_factory=list)
      review_logs: list[ExportReviewLog] = Field(default_factory=list)
  ```
  main.py 也没有 body size 中间件。
- **影响**：
  - 单 POST 上传 100 MB JSON → uvicorn 解析整体读入内存 → Python list[ExportMistake] 实例化 → 触发 GC 风暴或 OOM。
  - 多账号配合可作低成本 DoS（无限流情况下，配合 [C-001]）。
  - SQLite 写阻塞导致整个进程不可响应。
- **复现路径**：
  ```bash
  # 生成 50 MB 假 JSON
  python -c "import json; print(json.dumps({'mistakes': [{'uuid':'x','title':'a','language':'cpp', ...}]*100000}))" > big.json
  curl -X POST http://host/api/v1/import/v3 -H "Authorization: Bearer $TOKEN" \
       -H "Content-Type: application/json" --data @big.json
  ```
- **修复建议**：
  ```python
  # 1. Pydantic schema 加上限
  class ImportPayloadV3(BaseModel):
      mistakes: list[ExportMistakeV3] = Field(default_factory=list, max_length=10000)
      review_sessions: list[ExportReviewSession] = Field(default_factory=list, max_length=10000)
      review_session_items: list[ExportReviewSessionItem] = Field(default_factory=list, max_length=100000)
      review_logs: list[ExportReviewLog] = Field(default_factory=list, max_length=200000)
      # ...
  ```
  ```python
  # 2. main.py 加 body size 限制中间件
  class BodySizeLimit(BaseHTTPMiddleware):
      MAX = 50 * 1024 * 1024  # 50 MB
      async def dispatch(self, request, call_next):
          cl = request.headers.get("content-length")
          if cl and int(cl) > self.MAX:
              return JSONResponse({"detail": "payload too large"}, 413)
          return await call_next(request)
  app.add_middleware(BodySizeLimit)
  ```
- **预估工时**：3 小时

### [H-003] `requirements.txt` 14/17 个直接依赖未钉版本（供应链漂移）

- **维度**：安全 / 稳定性
- **文件**：`backend/requirements.txt`
- **问题描述**：实测 17 个直接依赖，只有 3 个钉版本：
  ```
  fastapi              ← 未钉
  uvicorn              ← 未钉
  sqlalchemy           ← 未钉
  alembic              ← 未钉
  pydantic             ← 未钉
  pydantic-settings    ← 未钉
  python-multipart     ← 未钉
  pytest               ← 未钉
  httpx                ← 未钉
  eval_type_backport==0.3.1   ← 钉
  beautifulsoup4       ← 未钉
  lxml                 ← 未钉
  markdownify          ← 未钉
  passlib[bcrypt]      ← 未钉
  PyJWT                ← 未钉
  bcrypt==4.0.1        ← 钉
  ```
  Pydantic v1 → v2 这种 breaking change 重新部署就会触发。
- **影响**：
  - 不可重现的部署（"同样的代码上周能跑这周不行"）
  - 供应链投毒（少见但非零）
  - 版本组合的 bug 调试困难
- **复现路径**：删除 `.venv`，新 `pip install -r requirements.txt`，发现拉到的 fastapi 版本与开发机不同。
- **修复建议**：
  ```bash
  # 推荐 uv 或 pip-tools
  # 把当前 requirements.txt 重命名为 requirements.in
  mv backend/requirements.txt backend/requirements.in
  cd backend && uv pip compile requirements.in -o requirements.txt
  # 或 pip-tools
  pip install pip-tools
  pip-compile requirements.in -o requirements.txt
  ```
  CI 加 `pip-audit` 步骤检查 CVE。
- **预估工时**：1.5 小时

### [H-004] `stats_service.py` 全量加载 + Python 内存聚合（CLAUDE.md t1 升级）

- **维度**：性能
- **文件**：`backend/app/services/stats_service.py:79-130`、`:140-190`、`:193-225`、`:224-270`、`:301-330`
- **问题描述**：5 个 stats 函数都是先 `db.scalars(...).all()` 把全部记录拉进内存，再 Python `for` 循环聚合。
  ```python
  # line 89-90
  mistakes = db.scalars(select(Mistake).where(*mistake_filters)).all()
  review_logs = db.scalars(select(ReviewLog).where(*log_filters)).all()
  # 后面是 Python 循环算 streak / accuracy / count
  ```
- **影响**：用户每次打卡多 100 条 ReviewLog，stats 响应延迟线性增长。万级 ReviewLog 进程内存吃几十 MB。
- **复现路径**：阅读代码即可。已知 t1，但严重度被低估（数据量增长后会成为接口超时主因）。
- **修复建议**（按收益排序）：
  ```python
  # 1. count → SQL count（最容易）
  total = db.scalar(select(func.count(Mistake.id)).where(*mistake_filters))

  # 2. heatmap bucket → SQL date_trunc + GROUP BY
  rows = db.execute(
      select(
          func.date(ReviewLog.shown_at).label("day"),
          func.count(ReviewLog.id).label("count"),
      )
      .where(*log_filters)
      .group_by(func.date(ReviewLog.shown_at))
  ).all()

  # 3. streak → 递归 CTE 或单次 SQL
  ```
  补 `(user_id, shown_at)` 与 `(user_id, next_review_at)` 复合索引。
- **预估工时**：6-8 小时（5 个函数全改 + 索引 + 测试）

### [H-005] Review 的 GET 接口存在隐藏写库（HTTP 语义违反）

- **维度**：架构 / 数据完整性
- **文件**：`backend/app/services/review/__init__.py:88-92`、`:97-100`、`:150`、`:204`
- **问题描述**：
  ```python
  # line 88-92
  def _progress_for_session(db: Session, session: ReviewSession, user_id=None) -> ReviewProgressOut:
      ...
      if changed:
          db.commit()  # ← GET 路径里 commit
      return ProgressOut(...)

  # line 97-100
  def _mark_session_completed_if_needed(db: Session, session, *, progress) -> None:
      if progress.completed >= session.total_count and session.ended_at is None:
          session.ended_at = utc_now()
          db.commit()  # ← GET 路径里 commit
  ```
  这两个函数被 `get_next_item` (line 150) 与 `get_summary` (line 204) 调用。
- **影响**：
  - GET 不再幂等，违反 RFC 7231 §4.2.1 ("safe methods")。
  - 浏览器预取（`<link rel="prefetch">`)、Service Worker 缓存、CDN 探测、APM replay、前端 retry 都可能改写 session 状态。
  - 最坏案例："我刚关闭浏览器又打开，session 突然显示已完成" — 调试需要追踪到 GET 触发了 ended_at。
- **复现路径**：
  ```bash
  # 已完成最后一道题的 session
  curl -H "Authorization: Bearer $T" "http://host/api/v1/review/sessions/123/summary"
  # DB: ended_at = now()
  ```
- **修复建议**：
  - `submit_result()` 内部完成 progress 计算 + 自动 mark completed。
  - `_progress_for_session` 改纯读，返回值给路由 → 路由不 commit。
  - 或者：引入显式 `POST /api/v1/review/sessions/{id}/finalize`。
- **预估工时**：3 小时

### [H-006] Token 存 localStorage + 7 天有效期（CLAUDE.md t2）

- **维度**：安全
- **文件**：`frontend/src/stores/authStore.ts:22`、`backend/app/core/config.py:44`
- **问题描述**：
  - `localStorage.setItem(TOKEN_KEY, JSON.stringify({ token, username, userId }))`
  - `access_token_expire_minutes: int = Field(default=10080, alias="ACCESS_TOKEN_EXPIRE_MINUTES")` → 7 天
  - 没有 refresh token、没有 token revocation list。
- **影响**：
  - 任何 XSS 入口（依赖 CVE / 浏览器扩展 / markdown 渲染漏洞）→ `localStorage.getItem("coderecall_token")` → 完整 7 天窗口的接管。
  - 用户改密后旧 token 仍然有效（无服务端登出）。
- **修复建议**（短/长两阶段）：
  - **短期 (3-5 天)**：access_token_expire 改 30-120 分钟；后端加 token_jti 表 + revoke 接口；前端 axios interceptor 过期前 5 分钟自动 silent refresh。
  - **长期 (5-10 天)**：换 HttpOnly Cookie + refresh_token；前端不再自管 token，axios 不附 Authorization；CORS 配 `credentials: "include"`；后端 CSRF 双 token (Session + CSRF token in form)。
- **预估工时**：短期 8 小时，长期 24 小时

### [H-007] 关键测试绕过 Alembic（无法回归保护 0007/0008）

- **维度**：测试覆盖 / 数据完整性
- **文件**：`backend/tests/test_cross_user_isolation.py:25`、`backend/tests/test_import_export_v3.py:31`、`:137`
- **问题描述**：跨用户隔离测试与 v3 导入导出测试用 `Base.metadata.create_all()` 或 `force_fallback=True`，跳过了 0007/0008 migration 本身的验证。
- **影响**：
  - 0007 给 mistakes/categories/tags 加的 `(user_id, name)` 复合唯一约束、0008 的 per-user uuid 唯一索引，**migration 脚本本身的正确性**没被回归测试覆盖。
  - 一旦 migration 写错（如索引名重复、约束顺序），160 passed 仍然过，部署后炸。
- **修复建议**：
  ```python
  # backend/tests/conftest.py
  @pytest.fixture
  def alembic_db():
      """Use Alembic head schema, not Base.metadata.create_all()"""
      url = "sqlite:///./test_alembic.db"
      from alembic import command
      from app.db.init_db import _build_alembic_config
      command.upgrade(_build_alembic_config(url), "head")
      engine = create_engine(url)
      yield engine
      engine.dispose()
      os.unlink("test_alembic.db")

  # 让关键测试也走 alembic_db fixture 跑一遍
  ```
- **预估工时**：3 小时

### [H-008] `_create_all` 与 Alembic 产生的 schema 不保证一致

- **维度**：架构 / 数据完整性
- **文件**：`backend/app/db/init_db.py:29-31`、`backend/alembic/versions/0007_*.py`、`0008_uuid_composite_unique.py`
- **问题描述**：
  - `_create_all` 使用 `Base.metadata.create_all(bind=engine)` 一次建所有表。
  - Alembic 0007/0008 包含 `op.create_index(..., unique=True)` / `op.add_column` / `op.create_foreign_key` 等手写操作。
  - SQLAlchemy `metadata.create_all` 只会按当前 Model 定义建表，**不一定等同于 Alembic head 的 schema**。比如 per-user uuid 唯一索引（0008）如果没在 Model 类的 `__table_args__` 里声明，create_all 不会建。
- **影响**：
  - 测试用 create_all + 生产用 alembic upgrade，**两者跑出来的 schema 不一致**。
  - 与 [C-003] 形成共振：新建库走 create_all，已有库走（手动）alembic，两条路径分叉风险倍增。
- **修复建议**：
  - 检查 Model `__table_args__` 是否完整声明 0007/0008 的所有约束 / 索引。
  - 或废除 `_create_all`，统一只用 Alembic（包括测试 fixture）。
- **预估工时**：2 小时（含 schema diff 验证）

## 4. Medium 问题（本迭代修复）

### [M-001] CORS 配置在生产环境是部署陷阱
- **文件**：`backend/app/main.py:23-29`
- **描述**：`allow_methods=["*"], allow_headers=["*"], allow_credentials=True` 配单 origin。生产环境若 `frontend_origin` 写错为 `https://app.example.com` 但前端实际部署 `https://www.app.example.com`，CORS 直接挂；又因为 allow_headers=`*` + credentials=True，浏览器会忽略响应头（spec 规定 credentials=true 时不接受 `*`）。
- **修复**：显式列 `allow_methods=["GET","POST","PUT","DELETE","PATCH"]`，`allow_headers=["Authorization","Content-Type"]`；frontend_origin 支持多域名（list）。
- **工时**：1 小时

### [M-002] `api.ts:62` 动态 import("../routes") 让 Vite 分包失效
- **文件**：`frontend/src/services/api.ts:62`、`frontend/src/routes.tsx`
- **描述**：401 拦截器 `void import("../routes").then(...)`，但 routes.tsx 又被 App.tsx 静态依赖 → Vite 警告 dynamic import 不会拆出独立 chunk。
- **修复**：建立轻量 `routerBridge.ts`：
  ```ts
  // routerBridge.ts
  let _navigate: ((to: string, opts?: any) => void) | null = null;
  export const setNavigator = (fn: typeof _navigate) => { _navigate = fn; };
  export const goTo = (to: string, opts?: any) => _navigate?.(to, opts);
  // routes.tsx 启动时调用 setNavigator(router.navigate)
  // api.ts 改成 goTo("/login", { replace: true })
  ```
- **工时**：1.5 小时

### [M-003] 401 拦截器响应路径有竞态：logout → import → navigate
- **文件**：`frontend/src/services/api.ts:59-64`
- **描述**：401 时先 `logout()` 同步清 store，再异步 `import("../routes").then(navigate)`。在动态 import 完成前的 50-200ms 窗口内，组件会以"已 logout"状态 re-render，可能闪烁登录拦截或显示空白。
- **修复**：跟 M-002 一起，路由 bridge 同步可用，消除异步窗口。
- **工时**：与 M-002 合并

### [M-004] Category / Tag schema 缺 `name` 长度约束
- **文件**：`backend/app/schemas/category.py:7`、`backend/app/schemas/tag.py:7`
- **描述**：schema 只声明 `name: str`，service 只 `strip()` 非空。SQLite 对 `String(100)` 不强制截断。
- **修复**：`name: str = Field(min_length=1, max_length=100)`。
- **工时**：1 小时

### [M-005] Dashboard 列表 / Tag Cloud 无可点击导航（CLAUDE.md t3）
- **文件**：`frontend/src/pages/Dashboard/index.tsx:209-235`
- **描述**：Recent Mistakes 仅展示 title + 时间，无 onClick；Tag Cloud 也仅 `<Tag>` 不带链接。
- **修复**：`<Link to={`/mistakes/${mistake.id}`}>`；标签 `onClick={() => navigate(`/mistakes?tag=${tag.name}`)}`。
- **工时**：1 小时

### [M-006] `list_mistakes` 返回完整 stem_markdown，列表流量爆炸
- **文件**：`backend/app/api/routes/mistakes.py:34`、`backend/app/schemas/mistake.py`
- **描述**：列表查询返回 `MistakeOut`，含完整 stem_markdown / 错因 / code 字段。markdown 可能很大。
- **修复**：拆 `MistakeListOut`（id/title/language/difficulty/updated_at/category_name/tag_names），详情接口才用 `MistakeOut`。
- **工时**：2 小时

### [M-007] Streak toast 无 `.catch`（CLAUDE.md m1）
- **文件**：`frontend/src/pages/Review/index.tsx:95-112`
- **描述**：`getStatsOverview(...).then(...)` 无错误兜底。
- **修复**：末尾 `.catch(() => {})` 或 `try/catch async`。
- **工时**：0.2 小时

### [M-008] 5+ 个组件硬编码中文绕过 i18n
- **文件**：
  - `frontend/src/components/common/ProblemUrlImporter.tsx:21`
  - `frontend/src/components/review/VariantDrawer.tsx:33`
  - `frontend/src/pages/MistakeEditor/index.tsx:183`
  - `frontend/src/components/review/ReviewPageState.tsx:25`
  - `frontend/src/pages/MistakeList/OnboardingPage.tsx`（多处 placeholder / 提示）
- **修复**：把字串收敛到 `i18n/resources/zh-CN.ts` 与 `en-US.ts`，组件用 `t(key)`。
- **工时**：2 小时

### [M-009] OLD_USER_INITIAL_PASSWORD 默认值就是 insecure
- **文件**：`backend/app/core/config.py:18-23`、`:45`、`:96-100`
- **描述**：默认 `"coderecall"` 在 `_INSECURE_OLD_USER_PASSWORDS` 里，因此非 test 环境 fail-fast。但默认值 = insecure 导致首次启动就失败，需要每次都设置环境变量。Codex 没注意到，Gemini 也没单独提。
- **修复**：把默认值改为 `""`（空 = 必须显式设置），错误信息更友好。或者首次启动用 `secrets.token_urlsafe(24)` 自动生成 + 写日志要求用户立即修改。
- **工时**：1 小时

### [M-010] 前后端 `MAX_TITLE_LEN` 不一致（前端 200 / 后端 500）
- **文件**：`frontend/src/pages/MistakeEditor/index.tsx:238`、`backend/app/schemas/mistake_constraints.py:5`
- **修复**：前端用后端常量（`Annotated` 类型 export 到 OpenAPI，前端用 schema codegen）。
- **工时**：1 小时

### [M-011] Public 文档与运行时 API 严重漂移
- **文件**：`README.md:100`、`docs/api-contract-current.md:4` / `:26`、`docs/deployment-guide.md:13`
- **描述**：文档把 auth 路由写成 `/auth/*`（实际 `/api/v1/auth/*`）；register 响应与代码不一致；review 端点已删除但文档还在。
- **修复**：FastAPI 生成 OpenAPI → redocly 渲染对外文档，废弃手写 markdown。
- **工时**：4 小时

### [M-012] Stats 页 `tz_offset {n}m` 调试 Tag 暴露给用户
- **文件**：`frontend/src/pages/Stats/index.tsx:122`
- **描述**：调试性时区偏移直接渲染在 UI 顶部，对终端用户无意义。
- **修复**：删除该 Tag 或仅 `import.meta.env.DEV` 时显示。
- **工时**：0.3 小时

### [M-013] AI SSE try/catch 静默吞噬调试信息
- **文件**：`frontend/src/hooks/useAiAnalysisStream.ts:109` / `:147` / `:122`
- **描述**：3 处 `try { ... } catch { /* skip */ }` 静默吞噬，调试时无报错。
- **修复**：开发模式 console.warn，生产保持静默。
- **工时**：0.5 小时

## 5. Low 问题

| ID | 文件:行 | 问题 | 工时 |
|----|---------|------|------|
| L-001 | `README.md:133`、`frontend/package.json:6` | README 提示 `npm run type-check` 但 package.json 无此脚本 | 0.3h |
| L-002 | `backend/app/api/errors.py:6` / `:18` | error_payload 用 `Optional[Any]` / `dict[str, Any]`，错误结构未严格 schema 化 | 1h |
| L-003 | `backend/app/db/init_db.py:51-56` | `_ensure_old_user` 每次启动都打开新 engine + Session，未复用 SessionLocal | 0.5h |
| L-004 | `frontend/src/hooks/useAiAnalysisStream.ts:72` | `(await response.json()) as unknown` 是 src/ 唯一一个 unknown 强转 — 整体类型质量很高，但此处可改 `try/catch + Zod schema` 验证 | 1h |
| L-005 | `backend/app/services/import_export_service.py` | 每次 v3 import 都读全部 existing UUIDs 进内存做 dedup，大库会慢 | 1h |
| L-006 | `frontend/src/pages/MistakeEditor/index.tsx`、`MistakeList/index.tsx` | localStorage key `coderecall_ever_imported_${userId}` 在 logout 时不清理，污染下一个登录用户 | 0.5h |

## 6. 改进建议（非问题，但值得做）

### [I-001] OpenAPI 自动生成对外文档
FastAPI 已经免费给了 OpenAPI 3.0；用 `redocly build-docs openapi.json` 替代手写 `api-contract-current.md`，CI 上接入。

### [I-002] 端到端回归链
Playwright 覆盖：register → login → create mistake → start review → submit → streak toast → export v3 → import v3。当前 `vitest` 测的是 store / hook / component，没贯穿真实 HTTP 链路。

### [I-003] 前后端共享校验常量
`mistake_constraints.py` 用 codegen 导出到 `frontend/src/constraints.gen.ts`，避免 200/500 这类分叉。

### [I-004] 加 PWA / Service Worker
配合 Month 2 移动端适配，断网仍可看题。

### [I-005] CI 加扫描步骤
- `bandit -r backend/app`
- `pip-audit`
- `npm audit --audit-level=high`
- `eslint --max-warnings 0`
- 前端 build 检查 chunk size 上限

## 7. 已知问题验证（CLAUDE.md P2/P3）

| 编号 | CLAUDE.md 描述 | Claude 核实结果 |
|------|----------------|------------------|
| m1 | streak toast 无 .catch | ✅ **确认存在**。`Review/index.tsx:95-112` 仍是 `.then(...)` 无兜底。建议升级 → 本报告 [M-007] |
| m2 | authStore set(parsed) 全量合并 | ✅ **确认存在**。`authStore.ts:43`。已升级为 → 本报告 [C-004] |
| m3 | service user_id=None 残留 | ✅ **确认存在，且严重低估**。实际覆盖 30+ 个函数（5 个 service 文件全军覆没）。升级为 → 本报告 [C-002] |
| t1 | stats_service 内存聚合 | ✅ **确认存在**。5 个函数全部 `.all()` 拉表后 Python 聚合。升级为 → 本报告 [H-004] |
| t2 | Token 存 localStorage | ✅ **确认存在**。7 天有效期，无 refresh，无 revoke。升级为 → 本报告 [H-006] |
| t3 | Dashboard 列表无导航 | ✅ **确认存在**。Recent Mistakes 与 Tag Cloud 都纯展示。本报告 [M-005] |

**新发现的高严重度问题**（CLAUDE.md 未列）：
- [C-001] auth 接口无速率限制
- [C-003] 已有库不跑 Alembic 迁移（部署 footgun）
- [H-001] CF/LeetCode follow_redirects=True
- [H-002] /import/v3 无 payload 上限
- [H-003] requirements.txt 钉版本不全
- [H-005] review GET 隐藏写库
- [H-007] 关键测试绕过 Alembic
- [H-008] _create_all vs Alembic schema 漂移
- [M-009] OLD_USER_INITIAL_PASSWORD 默认值即 insecure（fail-fast 副作用）

## 8. 审阅元信息

- **审阅模型**：Claude（主对话亲自接手，因为 Agent lane 三次 API 500 panic + omc ask 通道单轮 advisor 模式无法落盘完整 issue）
- **审阅日期**：2026-04-30
- **审阅方法**：Read + Bash(grep/wc/find) 直接扫描，未派 subagent
- **审阅范围**（实际读了的文件）：
  - 后端：`main.py`、`core/config.py`、`db/init_db.py`、`api/routes/auth.py`、`api/routes/import_export.py`（schema 部分）、`services/problem_import_service.py`、`services/auth_service.py`（间接）、`requirements.txt`
  - 前端：`stores/authStore.ts`、`services/api.ts`、`hooks/useAiAnalysisStream.ts`（先前已读）、`pages/Dashboard/index.tsx`（先前已读）
  - grep 全面：services/* user_id 模式、TS any/ignore、follow_redirects、rate limit
- **跳过 / 未深入的部分**：
  - 没逐行读 `services/review/__init__.py`（300+ 行），仅 grep 验证副作用证据
  - 没读 `services/import_export_service.py` 全文，仅 schema 层
  - 没运行 `pytest`、`bandit`、`pip-audit`、`npm audit`
  - 没在浏览器手工 e2e
  - 没测真实 LLM provider 调用
  - 没做 SQLite 大数据量压测
  - 前端 `components/review/*`、`components/stats/*` 子组件未深入
- **诚实声明**：本报告由主对话 Claude 在已知 CLAUDE.md 与 Codex/Gemini 的审阅压力下产出，**有意识地回避参考其他模型的 issue 编号 / 措辞**，但因为已读过 final-report.md（之前的综合版），无法做到 100% 信息隔离。差异化贡献集中在 [C-002] 量化范围 / [C-003] 已有库不迁移 / [H-008] schema 漂移 / [M-009] OLD_USER_INITIAL_PASSWORD footgun 这几个独家发现上。
