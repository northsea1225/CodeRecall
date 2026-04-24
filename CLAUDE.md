# 码错本 (CodeRecall) — 项目交接文档

> 新对话直接读此文件，跳过所有背景询问，立即进入执行模式。
> ⚠️ **角色约束**：Claude 只做方案讨论和协调，不擅自执行代码修改——必须获得用户明确授权后才能派发任务（详见文末协作规范）。

---

## 项目简介

**码错本**：面向 OI/ACM/LeetCode 选手的智能编程错题本。核心差异化：6 阶段动态 AI 教练（根据复习历史判断状态，非通用回复）+ SM-2 遗忘曲线调度 + LeetCode 一键导入。
核心循环：**导入题目 → 记录错误 → SM-2 间隔重复调度复习 → 6 阶段动态 AI 深度分析**。

- 项目路径：`/Users/hfish/Claude_chat/协同码力/`
- GitHub：`https://github.com/northsea1225/CodeRecall`
- 后端：FastAPI + SQLAlchemy + SQLite，Python 3.9.6（本地 venv）
- 前端：React 18 + TypeScript + Vite + Ant Design 5
- 测试：后端 **136 passed**（pytest），前端 **32 passed**（vitest，8 files）

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
```

API 文档：`http://localhost:8000/docs`

---

## 当前焦点

**⬜ C. 全量备份/导出（schema_v3）** — Month 1，下一个执行任务，工时约 3 天

技术债说明：
- 当前 v2 导出只含 `categories/tags/mistakes`，**不含** `review_logs / review_sessions`（数据丢失风险）
- 数据库无稳定 UUID 字段，跨设备迁移 / Anki GUID / CF 去重全会出问题
- schema_v3 结构：`{format, schema_version:3, exported_at, users, categories, tags, mistakes[{uuid, legacy_id}], review_sessions, review_session_items, review_logs}`
- 需 DB migration 给 `mistakes` 表加 `uuid` 字段

重点改造文件：
- `backend/app/schemas/import_export.py`
- `backend/app/services/import_export_service.py`
- `backend/app/api/routes/import_export.py`

---

## 已完成功能（当前状态）

### 核心功能 ✅
- 错题 CRUD（题目、错因、正确答案、代码 diff）
- SM-2 间隔重复算法（后端已实现）；前端默认策略为 `due_first` / `random`，选择 `spaced_repetition` 策略时才触发 SM-2 间隔更新
- 复习记录完整追踪（ReviewLog 表）
- 统计看板：KPI 卡片、趋势图、热力图、薄弱题表、**算法能力雷达图**
- 导入/导出 v2
- **LaTeX 公式渲染**：KaTeX，支持 `$...$` 和 `$$...$$`
- **键盘快捷键**：复习页 `1/2/3/4` 评分，空格翻牌

### AI 分析 ✅
- **6 阶段 ReviewStage 感知提示词**（`backend/app/services/prompt_templates.py`）
  - 6 个阶段：`new_mistake` / `early_review` / `repeated_weakness` / `lapsed` / `oscillator` / `maintenance`
  - 核心函数：`_compute_review_stage()`、`_is_oscillator()`、`_is_lapsed()`
  - XML 结构化输入 + `html.escape()` 防注入；各语言专属 hint
- `build_mistake_prompt_input()` 提取 review_logs 5 个字段（已修复 `user_result` 字段名 bug）
- `ai.py` 路由：`selectinload(Mistake.review_logs)` 已加
- **AI 变体题生成**：`POST /api/v1/ai/generate-variant/{mistake_id}`，普通 JSON 响应（非 SSE），前端 `VariantDrawer`
- **AI 字段长度校验**：Pydantic `Annotated` 类型，集中在 `mistake_constraints.py`

### 录入体验 ✅
- **LeetCode URL 题面预览**：`POST /api/v1/import/problem-url/preview`，httpx + LeetCode GraphQL + markdownify，支持中英文站；返回题面草稿供用户补填错误代码/正确答案/错因后保存
- **首次使用引导页（OnboardingPage）**：空题库全屏展示，含 URL 导入 + Demo 数据一键载入
  - 触发：`pagination.total === 0 && !localStorage.getItem("coderecall_ever_imported") && hasFetched`
  - Demo：4 道经典 C++ 错题（线段树/背包DP/Dijkstra/int溢出），位于 `frontend/src/data/demoImportPayload.json`
  - `mistakeStore.ts` 新增 `hasFetched: boolean` 防首次加载闪屏

### 主题 & 品牌 ✅
- Light/Dark 模式完整支持，CSS 变量双主题（`tokens.css` 双套 `--app-sider-*`）
- `frontend/public/logo.png`：蓝色圆角 `</>` 图标 + 红色闪电徽标

---

## 关键文件速查

| 文件 | 作用 |
|------|------|
| `backend/app/services/prompt_templates.py` | AI 提示词核心，ReviewStage 枚举，所有 _compute_* 函数 |
| `backend/app/services/ai_analysis_service.py` | AI 流式请求，`build_mistake_prompt_input()` |
| `backend/app/api/routes/ai.py` | SSE 端点，review_logs eager load，变体题端点 |
| `backend/app/schemas/mistake_constraints.py` | 字段长度约束 Annotated 类型 |
| `backend/app/api/routes/problem_import.py` | LeetCode URL 导入路由 |
| `backend/app/services/problem_import_service.py` | LeetCode URL 导入解析核心 |
| `backend/app/api/routes/import_export.py` | 导入/导出 v2 路由（schema_v3 重点改造点） |
| `backend/app/schemas/import_export.py` | 导入/导出 schema（schema_v3 重点改造点） |
| `backend/app/services/import_export_service.py` | 导入/导出服务逻辑（schema_v3 重点改造点） |
| `backend/tests/test_prompt_templates.py` | ReviewStage / prompt 模板专项测试 |
| `backend/app/services/taxonomy_service.py` | 分类/标签 CRUD 服务 |
| `frontend/src/pages/MistakeList/OnboardingPage.tsx` | 首次使用引导页 |
| `frontend/src/pages/MistakeList/index.tsx` | 错题列表页，引导触发逻辑入口 |
| `frontend/src/components/common/ProblemUrlImporter.tsx` | URL 导入组件，支持 `autoFocus` |
| `frontend/src/components/common/MarkdownRenderer.tsx` | Markdown + LaTeX 渲染 |
| `frontend/src/components/review/VariantDrawer.tsx` | AI 变体题抽屉 |
| `frontend/src/components/stats/RadarTagChart.tsx` | 算法能力雷达图 |
| `frontend/src/pages/Review/index.tsx` | 复习主页，键盘快捷键入口 |
| `frontend/src/stores/mistakeStore.ts` | Zustand store，含 `hasFetched` |
| `frontend/src/data/demoImportPayload.json` | 4 道 Demo C++ 错题 |
| `frontend/src/styles/tokens.css` | 设计令牌，双主题 CSS 变量 |
| `frontend/src/styles/global.css` | 全局样式，布局规则 |
| `frontend/src/routes.tsx` | 路由 + 侧边栏 JSX |
| `frontend/src/App.tsx` | ConfigProvider，Ant Design 主题 |

---

## 路线图（Month 1-3）

### Month 1 — 降阻力 + 数据安全

| 任务 | 工时 | 状态 |
|------|------|------|
| 空状态引导（Demo 数据 + URL 输入框） | 0.5天 | ✅ 已完成 |
| C. 全量备份/导出（含 review_logs、UUID、schema_v3） | 3天 | ⬜ 下一个（详见当前焦点） |
| A. CF URL 导入（provider 模式拆分，CF API 缓存） | 4天 | ⬜ 待做 |

**A 的注意事项（CF 特有坑）**：
- CF 官方 API：`codeforces.com/api/{method}`，限频 1次/2秒；`problemset.problems` 只返回元数据（标题/rating/tags），**题面 HTML 仍需页面解析**
- CF 公式在 MathJax script 中，需特殊处理，不能直接抓文本
- Gym/private 题目会 403，明确 warning 而非报错
- rating 映射：≤1000→1，1200-1500→2，1600-1900→3，2000-2400→4，≥2500→5
- 做 A 时顺手重构 LeetCode 为 provider 模式：`providers/leetcode.py`、`providers/codeforces.py`

### Month 2 — 手机端 + 习惯养成

| 任务 | 工时 | 状态 |
|------|------|------|
| E. 手机端适配（复习模式优先，纯 CSS） | 3-4天 | ⬜ 待做 |
| 连续打卡习惯增强（热力图已有，需强化 streak 激励） | 1天 | ⬜ 待做 |
| 沉浸式暗房复习模式（隐藏侧边栏，全屏） | 1天 | ⬜ 待做 |

### Month 3 — 生态 + 体验深化

| 任务 | 工时 | 状态 |
|------|------|------|
| D. Anki 导出（genanki，HTML 字段，稳定 GUID） | 2天 | ⬜ 待做 |
| 高级搜索（比赛来源、错因、掌握度多维筛选） | 2天 | ⬜ 待做 |
| AI 分析分享卡片 | 2-3天 | ⬜ 待做 |

### Month 4-6 — 护城河

- 赛后聚合洞察报告（多题 AI 分析汇总）
- 错题集公开分享（Deck Share）
- 浏览器插件（CF/LeetCode 页面一键收录）

---

## 代码规范备忘

- 不写无意义注释，不写多行 docstring
- 后端测试：`unittest.TestCase` 和 pytest 函数风格混用；数据库相关测试用真实 SQLite，不 mock DB（允许 `unittest.mock` patch 外部 API）
- CSS 变量优先，不硬编码颜色值

---

## 协作规范（强制执行）

> Claude 在此项目中的角色是**方案讨论者和协调者**，不是代码执行者。

### 标准工作流：讨论 → 呈报 → 确认 → 执行

每次功能开发或问题修复必须严格按以下顺序推进：

1. **讨论**：Claude 联合 Codex / Gemini（CCG）进行分析，**只输出**分析报告和备选方案，不触发任何写文件动作
2. **呈报方案**：Claude 将最终实施计划（涉及文件、改动点、影响范围）清晰呈报给用户，**主动停下来**等待确认
3. **用户确认**：只有收到明确授权指令（如"可以执行"、"让 Codex 改"、"按这个方案做"）才能继续；一般讨论、认可思路、继续分析**不等于**授权
4. **派发执行**：获得授权后，Claude 才调用 Codex / team 执行代码落地；执行 agent 只改授权范围内的文件

### 标准分析与执行工具

- **CCG**（`/ccg`）：Claude + Codex + Gemini 三方并行分析，用于方案设计和技术评估
- **`/team`**：派发多文件并行执行任务给 Codex/executor agent

### 禁止行为（严重越权）

- ❌ 讨论出方案后不向用户汇报，直接让 Codex 写文件
- ❌ 用户要求"分析/查看"，却自动应用了修改建议
- ❌ 预判用户意图，在收到"执行"指令前就提前派发写文件 prompt
- ❌ Claude 自己直接使用 Edit / Write 工具修改项目代码文件（`~/.claude/**`、`.omc/**`、`CLAUDE.md` 除外）
- ❌ `omc ask codex` 的 prompt 中包含 write / implement / apply changes to files 等意图，但未获授权

### 执行后复核

Codex / team 完成后，Claude 必须：回收结果 → 向用户汇报改动点 → 验证结果（如运行测试）→ 说明剩余风险。不跳过复核步骤。

### 执行前固定话术

> "我已完成方案设计，准备修改以下文件：[列表]。请确认是否让 Codex 执行？"
