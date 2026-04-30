# Gemini 全栈审阅报告 — CodeRecall（2026-04-29）

## 0. 执行摘要
- **总体评分**: B（功能完整且已修复核心阻塞问题，但在数据规模扩展和前端状态安全上仍有技术债）
- **总问题数**: Critical 1 · High 2 · Medium 4 · Low 3
- **Top 5 风险**:
  1. [C-001] Token 存储于 localStorage 存在 XSS 窃取风险 (`frontend/src/stores/authStore.ts:18`)
  2. [H-001] 统计服务全量加载数据至内存，存在内存溢出和性能劣化风险 (`backend/app/services/stats_service.py:89`)
  3. [H-002] 外部可控的 Zustand 状态注入漏洞 (`frontend/src/stores/authStore.ts:43`)
  4. [M-001] 越权隐患：服务层 API 默认 user_id=None 残留 (`backend/app/services/stats_service.py:89`)
  5. [M-002] Dashboard 看板列表与标签云缺少可点击导航 (`frontend/src/pages/Dashboard/index.tsx:189`)
- **审阅者视角**：本次审阅最核心的发现是前端 `authStore` 对 `localStorage` 的信任假设过强（直接透传合并对象），这不仅放大了 XSS 的爆炸半径，还导致了潜在的前端状态注入风险。而后端的统计服务内存聚合在数据量上升时必将成为瓶颈。

## 1. 维度评分总览

| 维度 | 得分 | 关键发现 |
|------|------|----------|
| 安全 | C | 依然使用 `localStorage` 存储长期有效的 JWT，且 `authStore` 直接反序列化不受信的存储内容，XSS 影响面大；发现 API 缺少严格限制默认 `user_id=None` 的情况。 |
| 质量 | B | 类型注解完备，代码风格一致。但存在隐患：错误处理有遗漏（如 promise 未处理 rejection）。 |
| 架构 | B | 前后端职责划分明确，Zustand 分模块合理。统计服务层的“从 DB 拉取所有数据并在 Python 中计算”这一设计有较大缺陷，违反了下推 DB 计算原则。 |
| 性能 | C | 后端存在显著的内存聚合问题（N+1 及全量拉取）；前端的并行请求 `Promise.allSettled` 处理较好。 |
| UX | B | 深色模式和 UI 一致性好，按键支持体验佳；但存在未捕获的 fetch 错误和部分面板（Dashboard 列表）缺少跳转链路。 |
| 文档 | A | `CLAUDE.md` 非常详尽，与代码现状一致性极高。 |
| 测试 | B | 后端测试覆盖率高（160 用例），核心业务隔离和 Schema 迁移有测试保障。但前端端到端测试以及对于 AI SSE 的错误流解析缺乏集成测试验证。 |

## 2. Critical 问题（上线阻塞 / 数据泄露 / 安全漏洞）

### [C-001] 长期有效的 JWT Token 明文存储于 localStorage
- **维度**: 安全
- **文件**: `frontend/src/stores/authStore.ts:18`
- **问题描述**: 系统当前将拥有 7 天有效期的 JWT Token 直接通过 `localStorage.setItem` 存储在本地。若发生任何 XSS 攻击（例如：导入含有恶意 markdown payload 的错题但未被渲染器过滤），攻击者可轻易窃取 token 并接管账户。
- **影响**: 用户凭证泄露，造成数据篡改或隐私泄露。
- **复现路径**: XSS payload `localStorage.getItem("coderecall_token")`
- **修复建议**: 
  - 长期方案：改用后端签发的 `HttpOnly` Cookie 存储 accessToken 或引入 refresh_token 机制。
  - 短期方案：如果必须用 localStorage，至少缩短 JWT 的有效期（如从 10080 缩短为 120 分钟），并引入无感刷新逻辑。
- **预估工时**: 6 小时（长期方案需修改 CORS、axios interceptor 与后端 Auth 逻辑）

## 3. High 问题（本周修复）

### [H-001] 统计聚合服务拉取全量数据至 Python 内存
- **维度**: 性能 / 架构
- **文件**: `backend/app/services/stats_service.py:89` 及其他方法
- **问题描述**: `get_overview`、`get_trend`、`get_heatmap` 等多个函数使用 `mistakes = db.scalars(select(Mistake)...).all()` 将某一用户甚至全量用户的错题和复习记录拉取到内存中进行 `for` 循环统计。
- **影响**: 随着用户数和打卡记录增多，内存将迅速暴涨并导致 OOM，接口响应时间出现严重长尾。
- **复现路径**: 导入上千条 ReviewLog 记录并访问 `/stats` 接口即可发现响应时间激增。
- **修复建议**:
  将聚合逻辑下推至 SQLite（或未来的 PG）使用 `GROUP BY` 和聚合函数：
  ```python
  # 伪代码：
  count = db.scalar(select(func.count(Mistake.id)).where(Mistake.user_id == user_id, Mistake.is_archived.is_(False)))
  ```
- **预估工时**: 4 小时

### [H-002] Zustand 状态污染（对象解构合并任意输入）
- **维度**: 安全 / 架构
- **文件**: `frontend/src/stores/authStore.ts:43`
- **问题描述**: `initializeAuth` 在读取 localStorage 时直接使用 `set(parsed);`。如果攻击者或者某些第三方脚本污染了 `localStorage.getItem("coderecall_token")` 的 JSON 内容，将会把非预期的字段合并进 Zustand 的全局 state。
- **影响**: 会造成非预期的状态注入，或破坏该 store 的状态结构。
- **复现路径**: 
  在浏览器控制台执行：`localStorage.setItem('coderecall_token', JSON.stringify({ token: "...", userId: 1, admin: true }))`
- **修复建议**:
  严格限制写入的状态字段：
  ```typescript
  set({ token: parsed.token, username: parsed.username, userId: parsed.userId });
  ```
- **预估工时**: 0.5 小时

## 4. Medium 问题（本迭代修复）

### [M-001] Service 层的 user_id=None 默认参数残留，存在越权隐患
- **维度**: 安全 / 架构
- **文件**: `backend/app/services/stats_service.py:89`, `backend/app/services/import_export_service.py:53` 等
- **问题描述**: 尽管接口层已通过 `Depends(get_current_user)` 获取了 user，但 service 层的签名仍允许 `user_id: int | None = None`。这可能在后续内部调用时漏传 `user_id` 从而越权访问全局数据。
- **影响**: 开发新功能时容易产生越权漏洞。
- **复现路径**: 阅读代码签名。
- **修复建议**: 移除 `None` 默认值，要求业务服务强绑定 `user_id`，如需全局查询应当单开 `get_all_for_admin(db)` 函数。
- **预估工时**: 1 小时

### [M-002] Dashboard 无可点击跳转的导航反馈
- **维度**: UX / 可用性
- **文件**: `frontend/src/pages/Dashboard/index.tsx:189`
- **问题描述**: 在 Dashboard 上的近期错题列表（`Recent Mistakes`）和标签云（`Tag Cloud`），用户无法点击直接跳转到该题的详情或筛选列表。
- **影响**: 看板仅起到只读展示作用，阻断了“发现问题->解决问题”的用户操作链路。
- **复现路径**: 登录系统 -> Dashboard -> 试图点击某道错题或标签 -> 无任何交互。
- **修复建议**: 为 `List.Item` 和 `Tag` 增加 `<Link>` 或 `onClick` 事件，例如 `onClick={() => navigate('/mistakes?tag=' + tag.name)}`。
- **预估工时**: 1 小时

### [M-003] 未捕获的 Fetch Promise Rejection (Streak Toast)
- **维度**: 质量 / UX
- **文件**: `frontend/src/pages/Review/index.tsx:98`
- **问题描述**: 在复习完成后，调用 `getStatsOverview` 触发打卡 Toast 提示，但这里没有通过 `.catch` 捕获异常。当网络断开或请求失败时，会产生 Unhandled Promise Rejection 并抛向控制台，部分场景可能阻断后续执行。
- **影响**: 在弱网环境下影响控制台洁净度或造成应用部分崩溃。
- **复现路径**: 断网后结束一轮 Review。
- **修复建议**: `void getStatsOverview({...}).then(...).catch((err) => console.error("Streak check failed", err));`
- **预估工时**: 0.2 小时

### [M-004] API 接口的默认返回策略有少许冗余
- **维度**: 性能
- **文件**: `backend/app/api/routes/mistakes.py:34`
- **问题描述**: 列表查询 `list_mistakes` 返回包含 `stem_markdown` 甚至全量错误信息的 `MistakeOut` 列表，如果 markdown 内容很大，列表查询会产生巨大流量，消耗带宽。
- **影响**: 列表页加载缓慢。
- **修复建议**: 提供 `MistakeListOut` 轻量模型（不包含长文本字段如 `stem_markdown` 等），只保留题目、ID、难度等基础信息。
- **预估工时**: 2 小时

## 5. Low 问题（技术债 / 风格）

### [L-001] AI 接口在错误流处理时类型过于宽泛
- **维度**: 质量
- **文件**: `frontend/src/hooks/useAiAnalysisStream.ts:109`
- **问题描述**: 解析 payload.delta 时存在 `try { ... } catch { /* skip */ }` 这样的静默吞噬机制。虽防止了崩溃，但调试时缺乏有效报错信息。

### [L-002] 缺乏对重复导入的软提示反馈
- **维度**: UX
- **文件**: `frontend/src/pages/Dashboard/index.tsx`
- **问题描述**: 数据导入时被 `skip` 的错因和数量不会向用户醒目展示，用户可能会困惑为何数据量未增加。

### [L-003] JWT 密钥检查依赖 app_env 字符串匹配
- **维度**: 安全 / 质量
- **文件**: `backend/app/core/config.py:72`
- **问题描述**: 对于 insecure_secrets 的告警检查直接使用了 `.strip().lower() == "test"`，在其他非 prod 环境（如 CI）可能意外阻断或未捕获。

## 6. 改进建议（非问题，但值得做）

- **[I-001] 增加前端 PWA / Service Worker**: 鉴于项目有移动端访问诉求和复习打卡需求，可以增加离线缓存能力，使应用在断网时也能查看题目。
- **[I-002] 引入限流机制（Rate Limiting）**: `auth/token` 以及 AI 相关的 `ai/analyze/stream` 应当在后端引入基于 IP / User 的限流，防止被恶意爆破密码或恶意消耗 API 余额。
- **[I-003] 添加 API 端到端集成测试**: 目前前端缺失了针对 React UI 的自动化测试，可考虑加入 Playwright 测试覆盖 Onboarding 到 Review 的核心流程。

## 7. 已知问题验证

| 编号 | CLAUDE.md 描述 | 你的核实结果 |
|------|----------------|--------------|
| m1 | streak toast fetch 无 .catch | **确认存在**。`frontend/src/pages/Review/index.tsx:98` 确实只有 `.then()` 没有捕获。 |
| m2 | authStore set(parsed) 全量合并 | **确认存在**。`frontend/src/stores/authStore.ts:43` 未对解析字段做严格筛查。 |
| m3 | service user_id=None 残留 | **确认存在**。如 `stats_service.py:89` 参数 `user_id: int \| None = None`。 |
| t1 | stats_service 内存聚合 | **确认存在**。严重的技术债，使用 `.all()` 拉取全部记录。 |
| t2 | Token 存 localStorage | **确认存在**。使用 `localStorage.setItem`，XSS 脆弱。 |
| t3 | Dashboard 列表无导航 | **确认存在**。Dashboard 的 List 和 Tag 缺乏 `navigate` 绑定。 |

## 8. 审阅元信息
- **审阅模型**：Gemini
- **审阅日期**：2026-04-29
- **审阅范围**：
  - 后端：`backend/app/api/routes/*`, `auth_service.py`, `ai_analysis_service.py`, `stats_service.py`, `deps.py`, `config.py`, `alembic` 迁移脚本 0007/0008。
  - 前端：`frontend/src/routes.tsx`, `authStore.ts`, `api.ts`, `Dashboard/index.tsx`, `Review/index.tsx`, `useAiAnalysisStream.ts`。
  - 文档：`CLAUDE.md` 及全量架构概述。
- **跳过 / 未深入的部分**：
  - 未深入测试前端组件级别的细粒度重渲染 (`re-render`) 问题。
  - 未详细梳理所有的 CSS/响应式媒体查询断点代码（主要侧重架构与逻辑层）。
  - 没有深入 review Provider (如 LeetCode、CF) 中的具体正则和 DOM 解析逻辑是否健壮。