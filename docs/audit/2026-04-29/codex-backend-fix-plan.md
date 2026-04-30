# CodeRecall 后端审计修复计划（Codex）

本计划覆盖 `final-report.md` 指定的全部 backend / protocol / migration / config / test-infra 问题。校验输入源为：

- `docs/audit/2026-04-29/final-report.md`
- `docs/audit/2026-04-29/codex-report.md`
- `docs/audit/2026-04-29/claude-report.md`
- `CLAUDE.md`
- `.claude/plan/audit-fixes.md`

补充说明：

- `.context/` 目录不存在，因此无额外 prefs / history 约束可读。
- 下面所有 `Files affected` 均已按当前仓库代码回查到真实路径与行号。
- Phase 是排序桶，不是并行团队的人天承诺；实际排期仍要看 PR 拆分和回归成本。

## Ordering Rules

1. `H-008` `alembic_head_engine` fixture 必须先于 `C-001` mass refactor 落地。
2. `H-009` schema audit 与 `H-008` 并行推进，不等待 `C-001`。
3. `C-002` + `H-001` 是同一个 migration-path rewrite，禁止拆成两个独立 PR。
4. `M-010` 的后端导出/共享常量实现，等待 `I-001` OpenAPI/codegen 方案；若本迭代必须先修，只能做一次性手动同步并在同 PR 写明回收计划。

## Phase 1 — 立即（<1h）

### 配置与启动细项

#### M-009 `OLD_USER_INITIAL_PASSWORD` 默认值即 insecure footgun

1. **Files affected**: `backend/app/core/config.py:18-23,45,82-100`, `backend/.env.example:30-31`, `docs/release-runbook.md:33-42`
2. **Implementation steps**:
   Step 1: 把 `Settings.old_user_initial_password` 默认值从 `"coderecall"` 改为空串或无默认值，避免“模板值本身就触发 fail-fast”。
   Step 2: 保留 `APP_ENV=test` 豁免，但把日志文案改成“测试豁免”而不是“默认值可接受”。
   Step 3: 同步 `.env.example` 和 runbook，给出可复制的随机密码生成命令。
   ```python
   old_user_initial_password: str = Field(default="", alias="OLD_USER_INITIAL_PASSWORD")
   if s.old_user_initial_password.strip() in _INSECURE_OLD_USER_PASSWORDS:
       raise RuntimeError("OLD_USER_INITIAL_PASSWORD must be set to a non-default value. Only APP_ENV=test is exempt.")
   ```
3. **Test strategy**: 新增配置单测覆盖 `APP_ENV=production` + 空值失败、`APP_ENV=test` + 空值告警通过、显式强密码通过。
4. **Edge cases & error handling**: 处理空白字符串、大小写环境值、CI 中未显式设置变量的场景；错误信息必须直接给出修复命令。
5. **Dependencies**: 无；这项可以独立先落。
6. **Risks & mitigations**: 本地开发首次启动可能因为未配密码而失败。缓解方式是同步 `.env.example`、README、runbook；回滚方式是只回滚默认值改动，不影响 schema。
7. **Acceptance criteria**: `APP_ENV!=test` 时，未配置或仍用 insecure 值的启动路径直接失败；测试环境继续可跑 160 个 pytest。
8. **Estimated effort**: `1h`

Claude 对照：同意其把这项视为配置 footgun；不同意继续保留 `"dev-only-replace-this-with-a-strong-password"` 作为“看起来安全”的默认值，默认值必须是无效值，避免误部署。

#### L-003 `_ensure_old_user` 每次新开 engine / Session

1. **Files affected**: `backend/app/db/init_db.py:50-56`, `backend/app/db/session.py:17-35`, `backend/app/services/auth_service.py:133-162`
2. **Implementation steps**:
   Step 1: 把 `_ensure_old_user()` 改为接收现有 `Session` 或现有 `Engine`，不再内部 `create_engine()`。
   Step 2: 在 `initialize_database()` 成功迁移后复用同一连接或短生命周期 `SessionLocal(bind=engine)`。
   Step 3: 如果 `C-002/H-001` 同 PR 进行，直接把该 helper 折叠进新的 startup migration flow。
3. **Test strategy**: 启动初始化测试里 mock `create_engine` 调用次数，断言默认路径只建一个 engine；回归验证 `old_user` 仍可自动创建/旋转密码。
4. **Edge cases & error handling**: 迁移失败时不得再额外打开第二个 engine；`users` 表不存在时应安全跳过旧用户逻辑。
5. **Dependencies**: 最好与 `C-002/H-001` 同步处理，但不是硬依赖。
6. **Risks & mitigations**: 重构启动顺序时容易引入 session 生命周期错误。缓解方式是只允许 helper 接收显式 session，并在测试里覆盖“无 users 表”与“已有 old_user”两条路径；回滚简单。
7. **Acceptance criteria**: 正常初始化路径只创建一次 engine；`old_user` 行为不变；无额外连接泄露。
8. **Estimated effort**: `0.5h`

Claude 对照：同意问题判断；不同意把它长期单列为独立优化，这项应在 migration-path rewrite 里顺手消化，否则会重复改启动代码。

#### L-007 JWT secret 检查仍靠字符串匹配

1. **Files affected**: `backend/app/core/config.py:28,77-102`
2. **Implementation steps**:
   Step 1: 为 `app_env` 引入明确枚举或常量 helper，例如 `is_test_env`、`is_dev_env`。
   Step 2: 把当前 `env == "test"` 分支改为强类型判定，避免 `"Test"`、`"testing"`、尾空格等行为分叉。
   Step 3: 统一 JWT secret 与 `OLD_USER_INITIAL_PASSWORD` 的环境豁免逻辑。
3. **Test strategy**: 参数化测试 `test`、`Test`、`TEST`、` test `、`testing`、`production` 的行为，断言只有规范化后的 `test` 被豁免。
4. **Edge cases & error handling**: 保留 `case_sensitive=False` 的 BaseSettings 行为，但不要让“任意接近 test 的字符串”都进入豁免。
5. **Dependencies**: 无。
6. **Risks & mitigations**: 若历史部署用的是非标准 `APP_ENV` 值，可能因为行为变严而启动失败。缓解方式是在文档中列出允许值；回滚只需恢复 helper。
7. **Acceptance criteria**: 安全豁免只在标准测试环境生效；启动错误信息能解释当前 `APP_ENV` 为何不被视为测试。
8. **Estimated effort**: `1h`

Claude 对照：同意修复方向；不同意继续散落多处 `.strip().lower()`，应抽一个单点 helper，否则后续限流、CORS、日志分支还会再复制一遍。

## Phase 2 — 本周（~14h）

### 访问控制与入口护栏

#### C-003 `/auth/token` 与 `/auth/register` 无速率限制

1. **Files affected**: `backend/app/api/routes/auth.py:57-71`, `backend/app/main.py:21-53`, `backend/app/api/routes/ai.py:31-110`, `backend/app/api/routes/import_export.py:76-84`, `backend/requirements.txt:1-16`, `backend/app/core/limiter.py`（new）
2. **Implementation steps**:
   Step 1: 先引入统一 limiter 基础设施，并在 `FastAPI` app 级注册 429 handler。
   Step 2: 给 `/auth/token` 使用“IP + 规范化用户名”的组合 key，防止单 IP 对单用户名暴破；给 `/auth/register` 用 IP 维度限制。
   Step 3: 复用同一 limiter 能力扩展到 `/api/v1/ai/analyze/stream` 与 `/api/v1/import/v3`，但 auth 规则与大流量接口规则分开配置。
   ```python
   def auth_limit_key(request: Request) -> str:
       username = request.form().get("username", "").strip().lower()
       return f"{get_remote_address(request)}:{username}"
   ```
3. **Test strategy**: 新增 auth 路由集成测试，连续命中阈值后返回 429；再加 AI/import 的 smoke test 验证 limiter 生效且正常请求不受影响。
4. **Edge cases & error handling**: 反向代理场景要明确 `X-Forwarded-For` 信任链；用户名为空的登录请求仍需受限；429 响应结构必须保持统一错误 schema。
5. **Dependencies**: `H-005` 先把 limiter 依赖钉住；`I-005` 复用同一设施。
6. **Risks & mitigations**: 过严阈值会伤害正常用户。缓解方式是先保守阈值并暴露配置项；回滚时可仅关闭装饰器，不影响 auth 代码路径。
7. **Acceptance criteria**: `/auth/token` 与 `/auth/register` 出现稳定 429；AI/import 至少有基础限流；代理部署下 key 计算可预测。
8. **Estimated effort**: `3h`

Claude 对照：同意其把这项升为 Critical，也同意 limiter 做成共享基础设施；不同意 `/auth/token` 只按 IP 限流，必须至少把用户名并入 key，否则同 NAT 下会误伤且对定向暴破约束偏弱。

#### I-005 统一 rate limiting 设施（与 C-003 重叠）

1. **Files affected**: `backend/app/main.py:21-53`, `backend/app/api/routes/auth.py:57-71`, `backend/app/api/routes/ai.py:31-110`, `backend/app/api/routes/import_export.py:76-84`, `backend/app/core/limiter.py`（new）
2. **Implementation steps**:
   Step 1: 把限流策略抽成集中配置，不让每个 router 硬编码字符串。
   Step 2: 区分 auth、AI streaming、bulk import 三类预算，并预留按环境调参入口。
   Step 3: 记录限流命中日志和响应头，便于后续调阈值。
3. **Test strategy**: 配置层单测 + 至少一条 per-router 429 集成测试，验证共享异常处理器与 headers。
4. **Edge cases & error handling**: SSE 连接命中限流时必须在握手阶段返回 429，而不是半开流；import 限流应与 body-size guard 一起工作。
5. **Dependencies**: 依附 `C-003` 实施。
6. **Risks & mitigations**: 把所有规则一次性拉进来会让排查复杂。缓解方式是先实现 auth，再挂 AI/import；回滚可逐路由关闭。
7. **Acceptance criteria**: 限流成为 app 级能力而不是 auth 特例；新增接口可以复用统一 key/handler/config。
8. **Estimated effort**: `含在 C-003 的 3h 内`

Claude 对照：同意其“auth + AI + import 共享 limiter 能力”的方向；不同意第一批 PR 就把所有路由门限绑死在同一常量文件里，建议先落 auth，再扩展其余高风险端点。

### 外部请求与导入护栏

#### H-003 Codeforces / LeetCode provider `follow_redirects=True`

1. **Files affected**: `backend/app/services/problem_import_service.py:19-34`, `backend/app/services/providers/leetcode.py:45-73`, `backend/app/services/providers/codeforces.py:100-124`
2. **Implementation steps**:
   Step 1: 把共享 `httpx.AsyncClient(..., follow_redirects=True)` 改为 `False`。
   Step 2: 对允许的 301/302 场景只做显式 host 校验后重试，且目标 host 仍必须在 `{leetcode.com, leetcode.cn, codeforces.com}` 白名单内。
   Step 3: 删除 Codeforces 里把 `301/302` 当成功响应的逻辑，改为“校验 Location 后再发第二跳”。
3. **Test strategy**: 用 `httpx.MockTransport` 模拟 302 到允许 host、302 到非白名单 host、无限跳转、无 `Location` 四条路径。
4. **Edge cases & error handling**: LeetCode CN/COM 可能存在站点级跳转；无 `Location` 或跨协议降级应返回 502/400，而不是继续跟。
5. **Dependencies**: 无。
6. **Risks & mitigations**: 关闭自动跳转可能影响个别合法 URL。缓解方式是保留“显式允许的一跳”；回滚只影响 import preview。
7. **Acceptance criteria**: 默认不自动跟随重定向；跨 host 跳转被拒绝；合法同站跳转仍可预览题面。
8. **Estimated effort**: `2h`

Claude 对照：同意其 SSRF 防御视角；不同意只做“follow_redirects=False”这一半修复，Codeforces 当前 `status_code in (200, 301, 302)` 的成功分支也必须一起清掉。

#### H-004 `/import/v3` 无 payload 体积 / 数组上限

1. **Files affected**: `backend/app/api/routes/import_export.py:76-84`, `backend/app/main.py:21-53`, `backend/app/schemas/import_export.py:138-147`, `backend/app/services/import_export_service.py:396-722`
2. **Implementation steps**:
   Step 1: 在 ASGI 层增加请求体大小上限中间件，优先在解析 JSON 之前拒绝超大 body。
   Step 2: 在 `ImportPayloadV3` 各 list 字段上增加 `max_length`，并给每类实体定义合理上限。
   Step 3: 在 service 层再做总量保护，例如 mistakes / logs 组合预算和总跳过数量上限，防止“合法小 body + 超大数组”。
   ```python
   class ImportPayloadV3(BaseModel):
       mistakes: list[ExportMistakeV3] = Field(default_factory=list, max_length=50000)
       review_logs: list[ExportReviewLog] = Field(default_factory=list, max_length=200000)
   ```
3. **Test strategy**: 增加三类测试：超大 `Content-Length` 直接 413；数组长度超限返回 422；在上限内的真实 v3 备份仍能导入。
4. **Edge cases & error handling**: 客户端未发送 `Content-Length` 时，中间件要按累计字节数中止读取；压缩传输和 chunked body 也要被限制。
5. **Dependencies**: 与 `C-003/I-005` 协同，但可独立实现。
6. **Risks & mitigations**: 上限设得过低会挡住合法备份。缓解方式是依据当前数据规模给保守值并文档化；回滚只需放宽阈值，不改 schema 语义。
7. **Acceptance criteria**: 超大 body 在进入 Pydantic 前被拒绝；数组超限返回稳定错误；正常 v3 导入回归通过。
8. **Estimated effort**: `3h`

Claude 对照：同意其“中间件 + schema 上限”双层护栏；不同意只在 schema 层做 `max_length` 就算完成，因为 FastAPI 在拿到完整请求体前无法靠 Pydantic 避免内存放大。

#### H-005 `requirements.txt` 14/17 个直接依赖未钉版本

1. **Files affected**: `backend/requirements.txt:1-16`, `backend/requirements.in`（new）, `docs/release-runbook.md:13-20,74-78`
2. **Implementation steps**:
   Step 1: 引入 `requirements.in` 作为人工维护入口，`requirements.txt` 改为编译产物。
   Step 2: 采用 `pip-compile` 或 `uv pip compile` 输出全量钉死版本；保留 `bcrypt==4.0.1` 现有兼容性 pin。
   Step 3: 在 runbook 里声明安装入口是 `requirements.txt`，更新依赖时修改 `requirements.in` 后重新编译。
3. **Test strategy**: 清空虚拟环境后 `pip install -r requirements.txt`，再跑完整 `pytest`；另加 `pip-audit` 试运行。
4. **Edge cases & error handling**: Apple Silicon / Linux wheels 差异、`passlib[bcrypt]` 与 `bcrypt` 兼容性必须固定验证。
5. **Dependencies**: 无，但 `C-003` 会新增 limiter 依赖，最好先做。
6. **Risks & mitigations**: 一次性刷新解析树可能引入隐形升级。缓解方式是只做“钉当前已验证版本”；回滚就是恢复原文件。
7. **Acceptance criteria**: 后端依赖安装可复现；升级动作有明确工作流；`pytest` 仍保持全绿。
8. **Estimated effort**: `1.5h`

Claude 对照：同意用锁定文件替代裸 requirements；不同意把“升级到最新兼容小版本”作为本次目标，本次应优先锁定当前已知可运行集合，供应链治理先于版本焕新。

### 迁移路径重写

#### C-002 `should_initialize_database()` 让已有库跳过 Alembic

1. **Files affected**: `backend/app/main.py:14-18`, `backend/app/db/init_db.py:22-72`, `backend/tests/test_db_contract.py:48-54`, `backend/tests/test_import_export_v3.py:28-33,133-140`
2. **Implementation steps**:
   Step 1: 删除“只有 SQLite 文件不存在才迁移”的判断，startup 一律执行 `alembic upgrade head`。
   Step 2: 把 `should_initialize_database()` 废弃或删掉，迁移逻辑改成单入口，例如 `migrate_database_on_startup()`。
   Step 3: 仅为测试或一次性离线工具保留显式 fallback helper，生产启动路径绝不走 `create_all()`。
   Step 4: 如仍需支持 SQLite 多进程启动，增加文件锁或明确部署约束为单 worker 迁移后再起服务。
3. **Test strategy**: 新增启动测试覆盖“已存在旧库自动升级到 head”“空库自动建库并迁移”“已有库迁移失败时启动失败”三条路径。
4. **Edge cases & error handling**: `:memory:` SQLite、相对路径 DB、只读目录、损坏 DB 文件都要 fail-fast，不能再静默跳过。
5. **Dependencies**: 与 `H-001` 同一 PR；不依赖 `H-008` 先落，但 `H-008` 应尽快补上长期回归保护。
6. **Risks & mitigations**: 改 startup 逻辑可能影响本地开发与测试基建。缓解方式是保留显式 test helper、把生产路径和测试路径分离；回滚是恢复旧 startup 判定，但不建议。
7. **Acceptance criteria**: 无论 DB 文件是否已存在，正常启动都会尝试升级到 Alembic head；升级失败时应用不启动。
8. **Estimated effort**: `与 H-001 共享 4h`

Claude 对照：同意这是 deployment footgun 且必须升 Critical；不同意把 `H-008` 作为这项的硬前置，真实生产修复应先消除启动漏迁移，测试夹具可以并行补。

#### H-001 Alembic 失败被 `except Exception` 吞掉并 fallback `create_all`

1. **Files affected**: `backend/app/db/init_db.py:34-47`, `backend/app/main.py:14-18`
2. **Implementation steps**:
   Step 1: 删除默认路径中的广义 `except Exception` fallback。
   Step 2: 迁移失败时记录结构化日志并重新抛出，让 app 启动失败。
   Step 3: 如果确有 test-only fallback 需求，单独暴露受限 helper，不复用生产入口。
3. **Test strategy**: mock `command.upgrade()` 抛异常，断言 startup 失败且不会调用 `_create_all()`；日志中包含 revision 与数据库路径。
4. **Edge cases & error handling**: 针对 Alembic config 缺失、bad revision、SQLite lock、权限问题都必须统一 fail-fast。
5. **Dependencies**: 与 `C-002` 合并交付。
6. **Risks & mitigations**: 现有依赖 fallback 的测试会失效。缓解方式是同步替换为 Alembic-head fixture 或显式 test helper；回滚不推荐。
7. **Acceptance criteria**: 生产启动路径不再存在“迁移失败后悄悄继续启动”的分支。
8. **Estimated effort**: `含在 C-002 共享 4h 内`

Claude 对照：同意两项必须一起改；不同意继续保留生产入口里的 `force_fallback` 语义，即使参数还存在，也必须限制为测试专用且不被 lifespan 调用。

#### H-008 关键测试绕过 Alembic

1. **Files affected**: `backend/tests/test_cross_user_isolation.py:20-52`, `backend/tests/test_import_export_v3.py:28-33,133-140`, `backend/tests/test_db_contract.py:48-54`, `backend/app/db/init_db.py:37-47`
2. **Implementation steps**:
   Step 1: 新建共享 fixture，例如 `alembic_head_engine` / `alembic_head_session`，统一用临时 SQLite 文件执行 `alembic upgrade head`。
   Step 2: 把直接 `Base.metadata.create_all()` 或 `initialize_database(..., force_fallback=True)` 的测试迁移到该 fixture。
   Step 3: 为需要事务隔离的测试继续用 connection-level rollback，但底座必须来自 Alembic schema。
3. **Test strategy**: 先替换 `test_cross_user_isolation.py` 与 `test_import_export_v3.py`，再补一条 fixture 自检，断言 `alembic_version` 为 `0008`。
4. **Edge cases & error handling**: Windows/macOS 文件锁、事务回滚与 TestClient 生命周期交互、模块级 fixture 污染都要覆盖。
5. **Dependencies**: 无；这是 `C-001` 的硬前置，且会解锁 `H-009`、`C-002/H-001`、`H-006` 的可靠回归。
6. **Risks & mitigations**: 测试会变慢。缓解方式是做 module-scoped engine + function-scoped transaction；回滚可临时只迁移最关键的跨用户与导入链路。
7. **Acceptance criteria**: 至少核心后端集成测试默认跑在 Alembic head schema 上；`C-001` 重构前已有覆盖网。
8. **Estimated effort**: `3h`

Claude 对照：完全同意其排序判断，这项必须先于 `C-001`；也同意把 import/export 与跨用户隔离测试作为第一批迁移对象。

#### H-009 `_create_all` 与 Alembic schema 不保证一致

1. **Files affected**: `backend/app/db/init_db.py:29-47`, `backend/alembic/versions/0007_add_user_system.py:26-110`, `backend/alembic/versions/0008_uuid_composite_unique.py:18-49`, `backend/app/models/mistake.py:31-41`, `backend/app/models/category.py:18-20`, `backend/app/models/tag.py:31-33`, `backend/app/models/review.py:56-60,73-75`
2. **Implementation steps**:
   Step 1: 在 `H-008` 新 fixture 基础上，做一次性 schema audit：Alembic head DB 与 metadata `create_all()` DB 比较表、索引、唯一约束、外键。
   Step 2: 把发现的差异记成 checklist；若生产路径已不再使用 `create_all()`，优先删除或 test-only 隔离 `_create_all()`。
   Step 3: 保留一条 contract test，防止未来重新把生产路径拉回双轨。
3. **Test strategy**: 写 schema diff 测试或小脚本，至少校验 `ix_mistakes_user_uuid`、`uq_categories_user_name`、`uq_tags_user_name`、`review_session_items` 复合约束存在。
4. **Edge cases & error handling**: SQLite inspector 对 partial index / foreign key 报告有限，要结合 SQLAlchemy metadata 和 `PRAGMA` 检查。
5. **Dependencies**: 与 `H-008` 并行；结果会反哺 `C-001` 和后续迁移设计。
6. **Risks & mitigations**: 若把“双轨都要完全等价”当成长期目标，会浪费工时。缓解方式是把该项定义为“退役双轨前的审计”，而不是永久维护两套初始化机制；回滚无意义。
7. **Acceptance criteria**: 已知生产约束和索引都能在 audit 中被覆盖；生产启动路径不再依赖 `_create_all()`。
8. **Estimated effort**: `2h`

Claude 对照：同意要做 schema audit；不同意把它理解成“继续支持 create_all 与 Alembic 长期共存”，正确目标是用 audit 证明差异后彻底退役生产 `create_all()`。

## Phase 3 — 本迭代（~22h）

### 服务层权限与语义收敛

#### C-001 service / repository 层 `user_id=None` 残留 30+ 入口

1. **Files affected**: `backend/app/services/mistake_service.py:35-165`, `backend/app/services/taxonomy_service.py:52-259`, `backend/app/services/stats_service.py:79-343`, `backend/app/services/review/__init__.py:37-245`, `backend/app/services/review/selector.py:19-55`, `backend/app/services/review/progress_updater.py:31-77`, `backend/app/services/review/recorder.py:14-22`, `backend/app/services/import_export_service.py:67-725`, `backend/app/repositories/mistake_repo.py:11-114`
2. **Implementation steps**:
   Step 1: 先在 `H-008` fixture 上建立回归保护，再按模块分批把 public service entrypoint 的 `user_id` 改为必填 `int`。
   Step 2: 为真正需要“无 owner 过滤”的内部工具保留私有 helper，名称显式带 `_unsafe` 或 `_all_users`，禁止业务路由直接调用。
   Step 3: 仓储层和 selector/progress/recorder 的 owner filter 也改为默认必带，避免 service 层修完后 repository 仍能裸用。
   Step 4: 推荐拆 5 个批次：review 链、mistake/taxonomy、stats、import/export、repository/common helper。
3. **Test strategy**: 在现有跨用户隔离测试外，补充“直接 service 调用未传 user_id 时类型或运行时失败”的单元测试；每批改完都跑全量 pytest。
4. **Edge cases & error handling**: 数据迁移/运维脚本若确实需要全局访问，必须走专门 helper；避免把 `user_id=0` 当哨兵值。
5. **Dependencies**: `H-008` 必须先落；`H-009` 需并行提供 schema/约束信心；`H-007` 依赖 review 批次先完成。
6. **Risks & mitigations**: 这是最容易引发广泛回归的改动。缓解方式是分批 PR、每批限定文件面、优先改 public API 到 internal helper 的边界；回滚按批次进行。
7. **Acceptance criteria**: 面向业务路由的 service / repository 入口不再接受 `None` 作为 owner 作用域；跨用户隔离测试继续全绿。
8. **Estimated effort**: `5-7h`

Claude 对照：同意其“30+ 函数、按批次改”的判断，也同意 `H-008` 为硬前置；不同意把所有 helper 一刀切成 public 函数签名变更，建议保留少量显式私有 helper，降低脚本/测试适配成本。

#### H-007 Review GET 接口存在隐藏写库

1. **Files affected**: `backend/app/api/routes/review.py:44-100`, `backend/app/services/review/__init__.py:88-101,150-157,204-207`, `backend/app/services/review/progress_updater.py:74-86`
2. **Implementation steps**:
   Step 1: 把 `completed_count` 与 `ended_at` 的最终写入完全收拢到 `submit_result()` 路径。
   Step 2: 让 `get_next_item()` 和 `get_summary()` 只读，不再调用会 `commit()` 的 `_progress_for_session()` 或 `_mark_session_completed_if_needed()`。
   Step 3: 如确需兜底 finalize，优先在 submit 链里自动完成；不要新增 `GET` 副作用，也不建议再引入额外 `POST /finalize`。
3. **Test strategy**: 增加回归测试：完成最后一题后调用 `GET /summary` 前后，`review_sessions.ended_at` 不应变化；`submit` 后应已正确写好完成状态。
4. **Edge cases & error handling**: 用户中途退出、重复提交、空 session、最后一题在 `answered_at is None` 的异常路径都要保持一致。
5. **Dependencies**: `C-001` 的 review 批次应先落，确保 owner 作用域已硬化。
6. **Risks & mitigations**: 如果只删 GET 写入而不补 submit 写入，会让完成状态丢失。缓解方式是先补 submit 再删 GET side effect；回滚可暂时恢复 `_mark_session_completed_if_needed()`。
7. **Acceptance criteria**: 所有 `GET /review/*` 路由对数据库只读；session 完成状态在 submit 后即正确持久化。
8. **Estimated effort**: `3h`

Claude 对照：同意问题等级和“GET 必须只读”；不同意新增显式 `POST /review/sessions/{id}/finalize`，当前产品流程不需要新协议面，直接把写入前移到 submit 更简洁。

### 契约与文档单一事实源

#### H-002 公开文档与运行时 API 严重漂移

1. **Files affected**: `docs/api-contract-current.md:3-19,26-65`, `README.md:100-116`, `docs/deployment-guide.md:11-13,201,228`, `backend/app/api/routes/auth.py:57-75`, `backend/app/api/routes/review.py:34-100`, `backend/app/main.py:31`
2. **Implementation steps**:
   Step 1: 先做一次文档纠偏，把 `/auth/*` 全量改成 `/api/v1/auth/*`，并更新 register / me / review 路由的真实响应结构。
   Step 2: 把“手写 Markdown 是权威”的表述降级，运行时 OpenAPI 才是事实源。
   Step 3: 在 `I-001` 落地前，保留一条轻量 contract test，验证 README / deployment guide 中关键 curl 示例不再引用旧路径。
3. **Test strategy**: 新增测试导出 `/openapi.json` 并断言关键 path 存在；对文档中的 curl 示例做 smoke 校验或最少做 grep-based lint。
4. **Edge cases & error handling**: 文档要同时覆盖 form-encoded login、统一错误结构、`/health` 无前缀、review 新路径。
5. **Dependencies**: `I-001` 是长期收口方案；`M-010` 依赖这里建立“后端为源”的机制。
6. **Risks & mitigations**: 手动改文档容易再次漂移。缓解方式是把这项当“止血”，随后立即用 `I-001` 自动化；回滚只影响 docs。
7. **Acceptance criteria**: README、deployment guide、api-contract 中不再出现错误 auth/review 路径与过期响应示例；关键路径可由 runtime OpenAPI 证明。
8. **Estimated effort**: `4h`

Claude 对照：同意其把这项从 Medium 提升到 High；不同意把“修文档”视为最终状态，必须明确 runtime OpenAPI 才是权威，否则 drift 会重现。

#### I-001 OpenAPI 自动生成对外文档

1. **Files affected**: `backend/app/main.py:21`, `docs/api-contract-current.md`, `docs/index.md:15,32`, `scripts/export_openapi.py`（new）, `scripts/build_api_docs.sh`（new）, `docs/api/openapi.json`（generated）
2. **Implementation steps**:
   Step 1: 增加导出脚本，从 FastAPI app 直接生成 `openapi.json`。
   Step 2: 选择一个静态渲染路径，例如 Redocly 或自定义模板，把对外 API 文档变为生成产物。
   Step 3: 在 `docs/index.md` 中把手写 `api-contract-current.md` 改成“生成文档入口”，保留历史手写文档仅作归档。
3. **Test strategy**: CI 或本地脚本校验导出的 `openapi.json` 能成功生成文档；新增 snapshot 或 checksum 防止无意漂移。
4. **Edge cases & error handling**: 自定义错误结构、`application/x-www-form-urlencoded`、SSE 路由描述都要在 schema 中正确表达；必要时补 `response_model` / `openapi_extra`。
5. **Dependencies**: 为 `H-002` 提供长期解决方案；`M-010` 后端导出等待这套机制。
6. **Risks & mitigations**: 生成文档初期可能不够“面向人类”。缓解方式是保留少量手写补充页，但路径和 schema 以 OpenAPI 为源；回滚只影响 docs pipeline。
7. **Acceptance criteria**: 可以一键从后端生成对外 API 文档；后续文档更新不再手工复制路径和响应结构。
8. **Estimated effort**: `4h`

Claude 对照：基本同意；不同意把生成目标限定为 Redocly 单一工具，仓库当前没有前置依赖，先把 `openapi.json` 作为稳定中间产物更重要。

### 数据面与模型约束

#### H-006 `stats_service.py` 全量拉表后做 Python 聚合

1. **Files affected**: `backend/app/services/stats_service.py:79-137,140-190,193-221,224-294,297-343`, `backend/app/api/routes/stats.py:16-62`, `backend/app/models/mistake.py:31-41,49-75`, `backend/app/models/review.py:73-101`, `backend/alembic/versions/0009_stats_indexes.py`（new）
2. **Implementation steps**:
   Step 1: 把 overview / trend / heatmap / top-weak / tag-radar 的聚合尽量下推到 SQL，至少先解决 `.all()` 拉全表。
   Step 2: 为常用过滤维度补索引，例如 `review_logs(user_id, shown_at)`, `mistakes(user_id, is_archived, next_review_at)`, `review_session_items(session_id, order_index)` 复核。
   Step 3: 对 tag-radar/top-weak 允许保留部分 Python 拼装，但输入集必须先在 SQL 侧缩小到当前窗口和当前用户。
3. **Test strategy**: 增加 query-count 或性能基线测试；同时用现有 stats 响应测试确保结果与当前实现一致。
4. **Edge cases & error handling**: 时区偏移、空数据集、`answered_at/shown_at` 为 null、窗口跨天边界都要保持数值不变。
5. **Dependencies**: `H-008` 提供迁移级回归；`C-001` 的 stats 批次确保 owner 作用域硬化。
6. **Risks & mitigations**: 统计逻辑最容易在“语义不变”上出错。缓解方式是先为每个接口加黄金样本测试，再改查询；回滚可逐接口进行。
7. **Acceptance criteria**: stats 端点不再通过 `.all()` 拉取当前用户全部 mistakes/review_logs；中等规模数据下响应时间和内存占用明显下降。
8. **Estimated effort**: `6-8h`

Claude 对照：同意把这项升级为 High，也同意补索引；不同意“一口气全 SQL 化”，`top-weak` 和 `tag-radar` 允许保留有限 Python 组装，重点是先切断全量拉表。

#### M-001 CORS `allow_methods=["*"]` + credentials 部署陷阱

1. **Files affected**: `backend/app/main.py:23-29`, `backend/app/core/config.py:54-59`, `docs/deployment-guide.md:11-13,80-83`
2. **Implementation steps**:
   Step 1: 把 `allow_methods=["*"]` 收紧为显式方法集，例如 `["GET", "POST", "PATCH", "DELETE", "OPTIONS"]`。
   Step 2: 如未来需要多前端 origin，给 `cors_origins` 提供逗号分隔配置，而不是继续从单个 `frontend_origin` 推导。
   Step 3: 在部署文档里写清楚“credentials=true 时不能再随意扩大 origin/methods”的约束。
3. **Test strategy**: 增加 CORS 预检测试，验证允许方法集合正确、未知 origin 被拒绝。
4. **Edge cases & error handling**: 本地 `localhost` / `127.0.0.1` 双 origin 仍要兼容；SSE 请求头和预检要继续通过。
5. **Dependencies**: 无。
6. **Risks & mitigations**: 方法集收紧可能漏掉未来新增路由。缓解方式是以测试保护，并在 router 新增时同步维护；回滚只改 middleware 配置。
7. **Acceptance criteria**: 生产 CORS 行为可预测，不再以通配符 methods 配合 credentials 运行。
8. **Estimated effort**: `1h`

Claude 对照：同意这是部署陷阱；不同意继续把 origin 推导逻辑绑定在单个 `FRONTEND_ORIGIN` 上，后续若有 preview/staging 域名会很快再次失控。

#### M-004 Category / Tag schema 缺少长度约束

1. **Files affected**: `backend/app/schemas/category.py:7-23`, `backend/app/schemas/tag.py:7-17`, `backend/app/models/category.py:24-25`, `backend/app/models/tag.py:37`, `backend/app/services/taxonomy_service.py:102-149,221-256`
2. **Implementation steps**:
   Step 1: 在 Pydantic schema 为 `name` 增加 `StringConstraints(max_length=100)`，与 ORM `String(100)` 对齐。
   Step 2: 如 `description` 也需受限，同步定义常量，避免 schema 与 DB 再分叉。
   Step 3: 保持 service 层的 `normalize_required_text()` 仅负责 trim/blank，不再承担长度兜底。
3. **Test strategy**: 新增 taxonomy schema 测试，覆盖 100 长度通过、101 长度 422、空白字符串 422。
4. **Edge cases & error handling**: 导入 v1/v3 里携带超长 category/tag 名时要稳定失败或跳过，不能等到 DB 层随机报错。
5. **Dependencies**: 无。
6. **Risks & mitigations**: 老数据若已超长，需要先审计再收紧。缓解方式是先检查现库长度分布；回滚只放宽 schema。
7. **Acceptance criteria**: taxonomy 的长度上限在 schema、service、DB 三层一致。
8. **Estimated effort**: `1h`

Claude 对照：同意补长度约束；不同意只修 schema 不审现有 DB 列宽，后端约束必须对齐 ORM/DDL，而不是引入新的 100/255 分叉。

#### M-006 `list_mistakes` 返回完整 `stem_markdown`

1. **Files affected**: `backend/app/api/routes/mistakes.py:26-45`, `backend/app/schemas/mistake.py:70-90`, `backend/app/services/mistake_service.py:35-67`, `backend/app/repositories/mistake_repo.py:38-69`
2. **Implementation steps**:
   Step 1: 新增 `MistakeListItemOut`，只保留列表页真正需要的字段，去掉大块 markdown 内容。
   Step 2: `GET /mistakes` 改用列表专用 response model；详情页继续走 `MistakeOut`。
   Step 3: 如果前端需要预览片段，后端显式提供 `stem_preview`，不要复用全量字段。
3. **Test strategy**: 调整列表 API 测试，断言 items 不再包含 `stem_markdown` 等大字段；详情 API 仍返回完整内容。
4. **Edge cases & error handling**: 搜索仍可在 repository 内匹配 markdown，但响应体不回传全文；导出接口不受影响。
5. **Dependencies**: 需要前端配合消费新 list schema；不阻塞其它后端安全修复。
6. **Risks & mitigations**: 改 response model 会影响现有 UI。缓解方式是先与前端一起改；回滚只恢复旧 model。
7. **Acceptance criteria**: 列表接口 payload 明显变小；详情页与导出数据不丢字段。
8. **Estimated effort**: `2h`

Claude 对照：同意拆列表/详情 schema；不同意继续用 `MistakeOut` 兼容两条路由，必须把“列表项”和“详情项”语义分开，否则 drift 会反复出现。

#### M-010 `MAX_TITLE_LEN` 前后端不一致，且后端当前值已高于 DB 列宽

1. **Files affected**: `backend/app/schemas/mistake_constraints.py:5-15`, `backend/app/models/mistake.py:49`, `backend/app/schemas/mistake.py:31-68`, `backend/app/services/import_export_service.py:178-191`, `frontend/src/pages/MistakeEditor/index.tsx:238`
2. **Implementation steps**:
   Step 1: 先决定单一真值，不建议继续保留后端 `500`，因为 ORM 列宽是 `String(255)`；若产品无强需求，直接统一到 `200` 或 `255`。
   Step 2: 在 `I-001` 的生成链路里把约束输出给前端，避免手工同步。
   Step 3: 在此之前若必须先修，临时把后端常量与前端规则同步到同一数值，并补 TODO 指向 codegen 回收。
3. **Test strategy**: 参数化测试 create/update/import 三条链路都使用同一上限；前端表单校验与后端 422 上限一致。
4. **Edge cases & error handling**: 历史数据若已有 200-255 之间标题，若最终统一到 200 需要决定“允许存量、限制增量”还是批量修复。
5. **Dependencies**: 后端导出机制等待 `I-001`；若本迭代先修，必须写明 interim 手动同步。
6. **Risks & mitigations**: 如果盲目把前端抬到 500，会把已有 ORM 255 列宽问题固化。缓解方式是先做列宽现实校验；回滚为恢复旧前端规则。
7. **Acceptance criteria**: create/update/import/frontend form 使用同一 title 上限；不再存在 200/500/255 三套数字。
8. **Estimated effort**: `1h`

Claude 对照：同意“必须等单一事实源”；不同意把现有后端 `500` 直接导出给前端，因为数据库列宽是 `255`，导出 `500` 等于把隐性 bug 产品化。

### 低风险质量收尾

#### L-002 `errors.py` 使用 `Optional[Any]` / `dict[str, Any]`

1. **Files affected**: `backend/app/api/errors.py:1-32`, `backend/app/main.py:34-53`, `backend/app/api/routes/auth.py:62-64`
2. **Implementation steps**:
   Step 1: 引入明确的 `ApiErrorOut` / `ApiErrorDetail` Pydantic 模型，替代裸 `dict[str, Any]`。
   Step 2: `error_payload()` 改为返回模型或模型 dump，异常处理器统一复用。
   Step 3: 对可预测 detail 结构的错误，逐步替换为明确字段，而不是随手塞任意 dict。
3. **Test strategy**: 新增错误响应 schema 测试，覆盖 401、404、422、429；OpenAPI 中的错误 shape 应稳定。
4. **Edge cases & error handling**: 422 的 `exc.errors()` 结构可能复杂，可先允许 `detail: object`，但顶层 envelope 必须定型。
5. **Dependencies**: `H-002/I-001` 会从更稳定的错误模型受益，但不是硬依赖。
6. **Risks & mitigations**: 一次性强类型化全部 detail 容易改太大。缓解方式是先固定顶层 envelope，细粒度 detail 渐进推进；回滚容易。
7. **Acceptance criteria**: 错误响应顶层结构统一、可文档化；不再由 `Any` 主导 helper API。
8. **Estimated effort**: `1h`

Claude 对照：同意要 schema 化；不同意第一步就把所有 `detail` 做成精确联合类型，先固定 envelope 更稳妥。

#### L-005 v3 import dedup 仍会把所有 incoming UUID 留在内存并做单次 `IN (...)`

1. **Files affected**: `backend/app/services/import_export_service.py:504-523`, `backend/app/schemas/import_export.py:138-147`
2. **Implementation steps**:
   Step 1: 把 `incoming_uuids` 查询改为分块，例如每 500 或 1000 个 UUID 一批。
   Step 2: 若后续 payload 规模继续扩大，可改用临时表或 staging 表做 join，而不是超长 `IN (...)`。
   Step 3: 结合 `H-004` 的数组上限，把这项作为性能优化，而不是安全边界。
3. **Test strategy**: 新增大批量 UUID 的性能/行为测试，验证分块 dedup 结果与当前实现一致。
4. **Edge cases & error handling**: UUID 大小写统一、重复 UUID、空 payload、超长单批参数限制都要处理。
5. **Dependencies**: 受 `H-004` 上限保护，但可以独立优化。
6. **Risks & mitigations**: 分块实现容易漏掉跨批重复。缓解方式是保留 Python `seen` 集合作为最终去重；回滚简单。
7. **Acceptance criteria**: import v3 不再构造超长单条 `IN (...)`；大 payload 下内存和 SQL 参数规模可控。
8. **Estimated effort**: `1h`

Claude 对照：同意需要优化；不同意其“读全部 existing UUIDs 进内存”的表述，当前代码读的是全部 incoming UUID 和匹配行，因此改造重点应是分块查询，不是回到逐行 existence check。

## Phase 4 — 季度

### 自动化治理

#### I-007 CI 增加 `bandit` / `pip-audit` / `coverage`

1. **Files affected**: `.github/workflows/backend-ci.yml`（new）, `backend/requirements.txt:1-16`, `backend/pytest.ini`（new or update）, `backend/pyproject.toml`（若后续收口测试配置）
2. **Implementation steps**:
   Step 1: 新增 backend CI workflow，先跑依赖安装、pytest、coverage，再跑 `bandit` 与 `pip-audit`。
   Step 2: 用 `pytest-cov` 设一个温和但明确的后端覆盖率门槛，例如先从 `--cov-fail-under=75` 起步。
   Step 3: 安全扫描默认只 gate 后端范围，避免本任务外的前端审计噪音把后端流水线搞红。
3. **Test strategy**: 在分支上手动跑一次 workflow；人为引入一个低质量分支验证 coverage gate 与 audit gate 都能拦截。
4. **Edge cases & error handling**: `pip-audit` 对 transitive advisory 可能偶发波动，必要时用 allowlist 文件带日期说明；coverage 门槛初期不要过高。
5. **Dependencies**: `H-005` 先提供可复现依赖锁定。
6. **Risks & mitigations**: 把 `npm audit`、bundle size、前端 lint 一起塞进同一后端 workflow 会造成误报。缓解方式是先建 backend-only pipeline，后续再扩展；回滚是把扫描步骤改为 report-only。
7. **Acceptance criteria**: PR 至少能自动跑 pytest + coverage + bandit + pip-audit；失败原因可定位；不被无关前端噪音主导。
8. **Estimated effort**: `2h`

Claude 对照：同意加 `bandit` 和 `pip-audit`；不同意把 `npm audit` 与 bundle size gate 混进这项 backend 计划，当前需求明确是 backend/test-infra，CI 也应先按后端边界落地。

## Codex Cross-Validation Notes

1. `C-002/H-001`：同意 Claude 把两项视为一个 migration-path rewrite；不同意把 `H-008` 作为生产修复的硬阻塞，真实服务应先去掉“已有库不迁移”和“异常后 fallback”。
2. `C-003/I-005`：同意共享 limiter 基础设施；不同意 `/auth/token` 只按 IP 限流，建议使用 `IP + username` 组合 key，AI/import 再使用各自预算。
3. `H-003`：同意关闭 `follow_redirects=True`；补充要求是 Codeforces 侧不能再把 `301/302` 视为成功响应。
4. `H-004`：同意 schema `max_length`；补充要求是 body-size guard 必须在 JSON 解析前生效，否则无法避免内存放大。
5. `H-009`：同意做 schema audit；不同意把双轨一致性当长期目标，正确目标是审计后退役生产 `create_all()`。
6. `H-007`：同意 GET 只读；不同意新增 `POST /finalize`，应把完成写入前移到 submit 路径，避免额外协议面。
7. `M-010`：不同意把当前后端 `MAX_TITLE_LEN=500` 作为导出真值，因为 ORM 列宽是 `255`；建议先统一到 `200` 或 `255`，再接入 codegen。
8. `L-005`：不同意“读全部 existing UUIDs”这一表述，当前更准确的问题是“单次大 `IN (...)` + 整批 incoming UUID 常驻内存”；优化方向应是分块或 staging。
9. `I-007`：同意安全扫描；不同意在 backend 计划里先把 `npm audit` 和前端 bundle gate 设为强门禁，建议先落 backend-only CI。

## Summary Table

| issue ID | phase | depends-on | unblocks | effort |
| --- | --- | --- | --- | --- |
| M-009 | Phase 1 | - | - | 1h |
| L-003 | Phase 1 | C-002/H-001 optional | - | 0.5h |
| L-007 | Phase 1 | - | - | 1h |
| C-003 | Phase 2 | H-005 | I-005 | 3h |
| I-005 | Phase 2 | C-003 | AI/import shared throttling | included in C-003 |
| H-003 | Phase 2 | - | - | 2h |
| H-004 | Phase 2 | - | safer import path | 3h |
| H-005 | Phase 2 | - | C-003, I-007 | 1.5h |
| C-002 | Phase 2 | H-001 shared PR | stable startup migration path | shared 4h |
| H-001 | Phase 2 | C-002 shared PR | fail-fast startup semantics | included in shared 4h |
| H-008 | Phase 2 | - | C-001, H-009, H-006 | 3h |
| H-009 | Phase 2 | H-008 | confidence to delete prod `create_all()` | 2h |
| C-001 | Phase 3 | H-008, H-009 parallel | H-007, stronger isolation guarantees | 5-7h |
| H-007 | Phase 3 | C-001 review batch | pure GET semantics | 3h |
| H-002 | Phase 3 | I-001 follow-up | M-010, accurate docs | 4h |
| I-001 | Phase 3 | H-002 stopgap helpful | M-010, long-term doc/source unification | 4h |
| H-006 | Phase 3 | H-008, C-001 stats batch | scalable stats endpoints | 6-8h |
| M-001 | Phase 3 | - | safer deployment defaults | 1h |
| M-004 | Phase 3 | - | taxonomy input consistency | 1h |
| M-006 | Phase 3 | FE coordination | smaller list payloads | 2h |
| M-010 | Phase 3 | I-001 preferred | single source of length truth | 1h |
| L-002 | Phase 3 | - | better OpenAPI/error docs | 1h |
| L-005 | Phase 3 | H-004 helpful | large-import performance | 1h |
| I-007 | Phase 4 | H-005 | automated backend quality gates | 2h |
