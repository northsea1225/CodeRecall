# CodeRecall UI Spec W1 Day 2

## 1. Dashboard
### Desktop 1280px Wireframe
```text
+------------------------------------------------------------------------------+
| [Logo] CodeRecall       [ Search Mistakes... ]       [+ Add]  [ Profile ]    |
+------------------------------------------------------------------------------+
|                                                                              |
|  +--------------+    +--------------+    +--------------+   +-------------+  |
|  | Total        |    | Mastered %   |    | Due Today    |   | [Review Now]|  |
|  |     128      |    |     64%      |    |      12      |   +-------------+  |
|  +--------------+    +--------------+    +--------------+                    |
|                                                                              |
|  +-------------------------------------+    +------------------------------+ |
|  | Recent Mistakes                     |    | Tag Cloud                    | |
|  | - [Py] Loop Index Out of Range  2h  |    | #Python #React #SQL #Hooks   | |
|  | - [TS] Type 'null' is not ...   5h  |    | #Rust #Algorithm             | |
|  | - [SQL] Missing JOIN Condition  1d  |    +------------------------------+ |
|  +-------------------------------------+    +------------------------------+ |
|                                             | Mistake Trend (W3 Chart)     | |
|                                             | [ . . . Placeholder . . . ]  | |
|                                             +------------------------------+ |
+------------------------------------------------------------------------------+
```

### 字段映射与组件
| 区域 | API 字段 | antd 组件 | Token 引用 |
| :--- | :--- | :--- | :--- |
| StatCard | `count`, `percentage` | `Statistic` | `--color-brand-primary` |
| MistakeRow | `title`, `language`, `created_at` | `List.Item` | `--color-border-default` |
| TagCloud | `tags.name` | `Tag` (checkable) | `--color-text-secondary` |
| Search | N/A (Client-side filter) | `Input.Search` | `--radius-base` |

### 交互状态规范
- **加载态 (Loading):** 使用 `Skeleton.Button` 对齐三张卡片，`Skeleton.List` 模拟列表。
- **空态 (Empty):** 引导文案 "No mistakes yet" (`--color-text-secondary`) + 居中 Add 按钮。
- **错误态 (Error):** `Result` 组件，状态码 500 时显示 "Sync Failed"，重试按钮颜色为 `--color-brand-primary`。

## 2. MistakeEditor
### Desktop 1280px Wireframe
```text
+------------------------------------------------------------------------------+
|  [ Back ]  Create / Edit Mistake                                  [Save]     |
+------------------------------------------------------------------------------+
|  Title: [__________________________________________________________________] |
|  Stem (Markdown): [________________________________________________________] |
+------------------------------------------------------------------------------+
|  Cat: [Select...]  Tags: [Multi-Select...]  Lang: [TS]  Diff: [***..] Src:[_]|
+------------------------------------------------------------------------------+
|  [ Wrong Answer (Monaco Editor)   ] | [ Correct Answer (Monaco Editor)  ]    |
|  |                                | |                                   |    |
|  | // Paste buggy code here       | | // Paste fixed code here          |    |
|  +--------------------------------+ +-----------------------------------+    |
+------------------------------------------------------------------------------+
|  Error Reason (Markdown Textarea):                                           |
|  [                                                                         ] |
+------------------------------------------------------------------------------+
|                                                           [Cancel]  [Save]   |
+------------------------------------------------------------------------------+
```

### 组件清单与校验
| 字段 | 组件 | 校验规则 | Token / 样式 |
| :--- | :--- | :--- | :--- |
| `title` | `Input` | 必填, max 200 | `font-size: 1.25rem` |
| `stem_markdown` | `Input.TextArea` | 选填 | `--color-border-default` |
| `category_id` | `Select` | 必填 | `--radius-base` |
| `tags` | `Select` (mode: tags) | 选填 | `margin-right: --spacing-sm` |
| `language` | `Select` | 必填 (默认 Plain) | `--color-text-secondary` |
| `difficulty` | `Rate` | 必填 (1-5) | `color: #fadb14` |
| `wrong_answer_markdown` | `Monaco` | 必填 (Diff-Left) | `height: 400px` |
| `correct_answer_markdown` | `Monaco` | 必填 (Diff-Right) | `height: 400px` |
| `error_reason_markdown` | `Input.TextArea` | 选填 | `min-height: 120px` |

## 3. 响应式断点 (Responsive Design)
- **断点策略:**
  - `sm: 640px`: 移动端窄屏
  - `md: 768px`: 平板/移动端横屏
  - `lg: 1024px`: 标准桌面
  - `xl: 1280px`: 宽屏桌面
- **Dashboard 降级处理:**
  - `< md`: 三张 StatCard 垂直堆叠为一列。
  - `< md`: Tag Cloud 与 Trend 移动至 Mistake List 下方。
- **Editor 降级处理:**
  - `< md`: 双栏 Monaco Editor 切换为垂直堆叠，Wrong Answer 在上。
  - `< sm`: 顶部 Save/Cancel 按钮简化为图标或固定在底部工具栏。

## 4. 给 Codex 的实施提示
- **W1 核心组件路径:**
  - `src/components/common/StatCard.tsx`: 封装看板卡片。
  - `src/components/common/FormField.tsx`: 统一 Form.Item 布局。
  - `src/components/mistake/MistakeRow.tsx`: 列表行展示，含 `LangBadge`。
- **Monaco 接入:**
  - 使用 `@monaco-editor/react`。W1 仅需配置基本 `language` 切换，无需自定义 Worker。
  - 主题统一使用 `vs-dark` 或 `light`，W2 再适配 `--color-bg-base`。
- **Dashboard 占位:**
  - Trend Chart 使用 `div` 背景占位，内部渲染 "Coming in W3" 文字。
- **样式细节:**
  - 所有边距必须引用 `tokens.css` 中的 `--spacing-md` (16px) 或 `--spacing-lg` (24px)。
  - 按钮悬浮态颜色应由 `--color-brand-primary` 配合 `opacity: 0.8` 实现。

## 5. Review

**Desktop 1280px ASCII Wireframe**

*Before "Show Answer"*
```text
+------------------------------------------------------------------------------+
| Progress: [###-------] 3/10                 Strategy: [Due First v]          |
+------------------------------------------------------------------------------+
| Question: Implement Binary Search                                            |
| [ stem_markdown rendered here ]                                              |
+------------------------------------------------------------------------------+
| Your Answer:                                                                 |
| +--------------------------------------------------------------------------+ |
| | // Monaco Editor (blank initially)                                       | |
| |                                                                          | |
| +--------------------------------------------------------------------------+ |
+------------------------------------------------------------------------------+
| [ Show Answer ]                                                              |
+------------------------------------------------------------------------------+
```

*After "Show Answer"*
```text
+------------------------------------------------------------------------------+
| Code Diff:                                                                   |
| +-----------------------------------+--------------------------------------+ |
| | User Attempt                      | Correct Answer                       | |
| | function search(...) {            | function search(...) {               | |
| |   // user code                    |   // correct_answer_markdown         | |
| | }                                 | }                                    | |
| +-----------------------------------+--------------------------------------+ |
+------------------------------------------------------------------------------+
| Error Reason:                                                                |
| [ error_reason_markdown rendered here ]                                      |
+------------------------------------------------------------------------------+
| Self-Rate:                                                                   |
| [ Again (<1m) ]   [ Hard (2d) ]   [ Good (5d) ]   [ Easy (8d) ]              |
+------------------------------------------------------------------------------+
```

**附录**
- **字段映射表**：
  - 题干：`mistake.stem_markdown`
  - 答案：`mistake.correct_answer_markdown`
  - 错因：`mistake.error_reason_markdown`
  - 策略：`review_mode` (Due First / Random)
  - 评分：`review_logs.user_result` (Again/Hard/Good/Easy)
  - 间隔：`review_logs.new_interval_days`
- **组件清单**：`ProgressBar`, `Select` (Strategy), `MarkdownViewer`, `MonacoEditor`, `Button`, `DiffViewer`, `SelfRateGroup`
- **空态**：无到期题显示 "All caught up! No mistakes to review right now." 居中插图。
- **加载态**：题目卡片与编辑器的骨架屏（Skeleton）。
- **结束态**：会话完成总结页 "Session Complete!"，展示本次复习总数与正确率。

## 6. Stats

**Desktop 1280px ASCII Wireframe**
```text
+------------------------------------------------------------------------------+
| Filters: [ Last 30 Days v ] [ All Categories v ]                             |
+------------------------------------------------------------------------------+
| +----------------+ +----------------+ +----------------+ +-----------------+ |
| | Total Mistakes | | Total Reviews  | | Current Streak | | Avg Mastery     | |
| |      124       | |      856       | |     12 Days    | |     85%         | |
| +----------------+ +----------------+ +----------------+ +-----------------+ |
+------------------------------------------------------------------------------+
| Review Heatmap (52 Weeks)                                                    |
| [|||||||  |||||||  |||||||  |||||||  |||||||  |||||||  |||||||  ||||||]      |
+------------------------------------------------------------------------------+
| +-----------------------------------+--------------------------------------+ |
| | Error Reason Distribution (Pie)   | Top Weak Points (List)               | |
| | [ ( ) ] Logic Error 40%           | 1. Dynamic Programming (8)           | |
| |         Syntax Error 20%          | 2. Graph Traversal (5)               | |
| +-----------------------------------+--------------------------------------+ |
| | Language Distribution (Bar)       |                                      | |
| | [======] TS (50)                  |                                      | |
| | [====] Python (30)                |                                      | |
| +-----------------------------------+--------------------------------------+ |
```

**附录**
- **字段映射表**：调用 API `GET /stats/overview` 和 `GET /stats/trend` 获取聚合数据。
- **图表库选型**：推荐 **Recharts**，基于 React 且支持 TypeScript，高度可定制，能完美契合 Linear/Notion 的极简风格调性（使用 CSS 变量控制颜色）。
- **状态管理**：
  - 空态：图表区域显示 "Not enough data to generate insights yet."
  - 加载态：卡片显示数字闪烁骨架屏，图表显示半透明占位。
  - 错误态：显示 `var(--color-error)` 提示及 Retry 按钮。

## 7. Review + Stats 响应式

基于断点设计的降级规则：
- **< sm (640px)**：
  - **Review**：`DiffViewer` 变为垂直堆叠（User Attempt 在上，Correct Answer 在下）。`SelfRateGroup` 按钮变为 2x2 网格。
  - **Stats**：4 张 `KPICard` 单列垂直排列。Heatmap 开启横向滚动条（`overflow-x: auto`）。
- **md (768px)**：
  - **Stats**：`KPICard` 变为 2 列 2 行排布。饼图与列表组件垂直堆叠。
- **lg (1024px)**：
  - **Review**：空间足够，`DiffViewer` 恢复左右并排对比。
- **xl (1280px+)**：
  - **全局**：采用标准 Desktop 布局，最大内容宽度限制为 1200px 居中对齐，左右留白 `var(--spacing-xl)`。

## 8. W1 Day 3 给 Codex 的实施提示

- **Review 页**：W1 阶段只做静态占位与路由连通，编写空态文案与假数据渲染，真实复习逻辑放在 W2。
- **Stats 页**：W1 阶段只做布局骨架和 `KPICard` 占位，主图表区显示 "Coming in W3" 提示符，真实图表集成放在 W3。
- **推荐新增组件**：
  - `DiffViewer`：封装 `monaco-diff-editor` 以支持代码比对。
  - `SelfRateGroup`：封装 4 个状态按钮的评价组件。
  - `HeatmapPlaceholder`：提供 GitHub 风格的复习热力图占位。
  - `KPICard`：统一样式的指标展示卡片，包含 `var(--shadow-sm)` 和 `var(--radius-lg)`。
- **颜色规则（结合 tokens.css）**：
  - Again：使用 `var(--color-error)`
  - Hard：使用 `var(--color-warning)`
  - Good：使用 `var(--color-success)`
  - Easy：使用 `var(--color-brand-primary)`
- **间距规则**：卡片间距统一使用 `var(--spacing-md)`，模块间距使用 `var(--spacing-lg)`。
