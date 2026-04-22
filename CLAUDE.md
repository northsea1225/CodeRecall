# 码错本 (CodeRecall) — 项目交接文档

> 新对话直接读此文件，跳过所有背景询问，立即进入执行模式。

---

## 项目简介

**码错本**：面向 OI/ACM/LeetCode 选手的智能编程错题本。
核心循环：**导入题目 → 记录错误 → SM-2 间隔重复调度复习 → 6 阶段动态 AI 深度分析**。

- 项目路径：`/Users/hfish/Claude_chat/协同码力/`
- 后端：FastAPI + SQLAlchemy + SQLite，Python 3.11+
- 前端：React 18 + TypeScript + Vite + Ant Design 5
- 测试：**120 passed**（后端 pytest），前端 vitest

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

## 已完成功能（当前状态）

### 核心功能 ✅
- 错题 CRUD（题目、错因、正确答案、代码 diff）
- SM-2 间隔重复算法调度复习（4 评分：Again/Hard/Good/Easy）
- 复习记录完整追踪（ReviewLog 表）
- 统计看板：KPI 卡片、趋势图、热力图、薄弱题表
- 导入/导出 v2

### AI 分析（本轮重点完成）✅
- **6 阶段 ReviewStage 感知提示词**（`backend/app/services/prompt_templates.py`）
  - 6 个阶段：`new_mistake` / `early_review` / `repeated_weakness` / `lapsed` / `oscillator` / `maintenance`
  - `_compute_review_stage()` 优先级：count=0→NEW → lapsed→LAPSED → weak≥2→REPEATED_WEAKNESS → oscillator→OSCILLATOR → count≤1→EARLY_REVIEW → else→MAINTENANCE
  - `_is_oscillator()`：检测最近结果 weak/strong 交替≥3次
  - `_is_lapsed()`：距上次复习 >30 天（严格大于）
  - XML 结构化输入 + `html.escape()` 防注入
  - 语言专项提示：algorithm/javascript/python/c++/cpp/c 各有专属 hint
- `ai_analysis_service.py`：`build_mistake_prompt_input()` 提取 review_logs 填充 5 个新字段
- `ai.py` 路由：`selectinload(Mistake.review_logs)` 已加
- **40 条专项单元测试**（`backend/tests/test_prompt_templates.py`）

### 主题切换 ✅
- Light/Dark 模式完整支持，左侧栏随主题正确切换
- CSS 变量：`tokens.css` → `[data-theme='light']` / `[data-theme='dark']` 两套 `--app-sider-*` 变量
- `global.css`：所有 `.app-sider` 规则改用 CSS 变量
- `routes.tsx`：`Menu theme={theme === "dark" ? "dark" : "light"}`
- `App.tsx`：ConfigProvider 加 `components: { Layout: { siderBg: "transparent", lightSiderBg: "transparent" } }`

### 品牌图标 ✅
- `frontend/public/logo.png`：蓝色圆角 `</>` 图标 + 红色闪电徽标
- `routes.tsx`：`<img src="/logo.png" alt="码错本" className="app-brand__mark" />`

---

## 关键文件速查

| 文件 | 作用 |
|------|------|
| `backend/app/services/prompt_templates.py` | AI 提示词核心，ReviewStage 枚举，所有 _compute_* 函数 |
| `backend/app/services/ai_analysis_service.py` | AI 流式请求，`build_mistake_prompt_input()` |
| `backend/app/api/routes/ai.py` | SSE 端点，review_logs eager load |
| `backend/tests/test_prompt_templates.py` | 40 条单元测试，覆盖所有 6 个阶段 |
| `frontend/src/styles/tokens.css` | 设计令牌，双主题 CSS 变量 |
| `frontend/src/styles/global.css` | 全局样式，布局规则 |
| `frontend/src/routes.tsx` | 路由 + 侧边栏 JSX |
| `frontend/src/App.tsx` | ConfigProvider，Ant Design 主题 |
| `frontend/public/logo.png` | 应用图标 |

---

## 下一步行动计划（按优先级）

### P0 — 立即执行（安全 + 低成本高收益）

#### 1. LaTeX 公式渲染
OI 题目几乎都有数学公式，当前 Markdown 渲染不支持。

```bash
cd frontend && npm install katex @types/katex
```

- 在 `review-markdown` 渲染处（`ReviewPage` 组件内）集成 KaTeX
- 前后处理 `$...$` 和 `$$...$$` 语法
- 预计工时：1-2 小时

#### 2. AI 安全加固（后端字段长度校验）
当前 `html.escape()` 防 XSS 已做，还需在 Pydantic schema 加字段长度上限：

- `stem_markdown`、`wrong_answer_markdown`、`correct_answer_markdown`：max_length=50000
- `error_reason_markdown`：max_length=10000
- `title`：max_length=500
- 文件：`backend/app/schemas/` 中对应的 `MistakeCreate`/`MistakeUpdate` schema

### P1 — 近期执行（竞赛亮点功能）

#### 3. AI 变体题生成
对已收录错题，让 AI 生成"同类陷阱"变体题，形成主动出题闭环。

- 新增端点：`POST /api/ai/generate-variant/{mistake_id}`
- 复用现有 SSE 流式架构（参考 `ai.py`）
- 提示词模板加在 `prompt_templates.py`（新增 `build_variant_prompt()` 函数）
- 前端在 ReviewPage / MistakeDetail 页加"生成变体题"按钮

#### 4. 算法能力雷达图
数据已在库里，只需前端渲染。

- 后端：在 `stats_service.py` 新增按 tag 聚合掌握度（correct 率、遗忘次数）
- 前端：Stats 页增加 Recharts `RadarChart`，各顶点为 tag 名称
- 需要先确保常用算法 tag 已预置（DFS、BFS、DP、贪心、二分、排序等）

#### 5. 键盘快捷键复习模式
- 复习页：`1/2/3/4` 直接触发 Again/Hard/Good/Easy 评分
- 空格键翻转显示答案
- 文件：`frontend/src/pages/ReviewPage.tsx`（或对应组件），加 `useEffect` 监听 `keydown`

### P2 — 中期（录入阻力，最大用户痛点）

#### 6. URL 一键导入（LeetCode 优先）
从 LeetCode 题目 URL 自动抓取题面，消除手工复制摩擦。

- 后端：新增 `POST /api/import/url`，用 `httpx` 请求 + `BeautifulSoup4` 解析 LeetCode 题目页
- 提取字段：标题、题干（含 LaTeX）、示例输入输出、难度
- 前端：导入页加 URL 输入框作为新的导入入口

---

## 竞赛核心卖点（评委展示用）

1. **6 阶段动态 AI 教练**：根据复习历史判断学生状态，给出针对性分析（非通用回复）
2. **SM-2 科学记忆曲线**：有理论支撑的遗忘曲线调度
3. **领域专项代码 Diff**：针对 OI/ACM 提交场景设计的代码对比展示

---

## 代码规范备忘

- 不写无意义注释，不写多行 docstring
- 测试用 `unittest.TestCase`（后端），不 mock 数据库
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

### 禁止行为（严重越权）

- ❌ 讨论出方案后不向用户汇报，直接让 Codex 写文件
- ❌ 用户要求"分析/查看"，却自动应用了修改建议
- ❌ 预判用户意图，在收到"执行"指令前就提前派发写文件 prompt
- ❌ Claude 自己直接使用 Edit / Write 工具修改项目代码文件（`~/.claude/**` 和 `.omc/**` 除外）
- ❌ `omc ask codex` 的 prompt 中包含 write / implement / apply changes to files 等意图，但未获授权

### 执行后复核

Codex / team 完成后，Claude 必须：回收结果 → 向用户汇报改动点 → 验证结果（如运行测试）→ 说明剩余风险。不跳过复核步骤。

### 执行前固定话术

> "我已完成方案设计，准备修改以下文件：[列表]。请确认是否让 Codex 执行？"
