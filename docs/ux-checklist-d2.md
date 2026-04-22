# W4 Day 2 UX 扫雷清单

| 序号 | 检查项 | 具体操作步骤 | 预期结果 | 通过标准 | 结果（人工填写） |
|------|--------|------------|---------|---------|--------------|
| 1 | Chrome DevTools Console 无红色 Error（走完整复习流程） | 1. 打开 Chrome，导航至 `http://localhost:5173`<br>2. 按 F12 打开 DevTools，切换到 **Console** 标签<br>3. 点击左侧菜单「Review」<br>4. 在 Review 页点击「开始复习」按钮<br>5. 按空格键显示答案<br>6. 在「错因复盘」Card 右上角点击「✨ AI 深度分析」按钮，等待流式输出完成<br>7. 点击「查看原始错题 (R)」打开 Drawer，然后关闭<br>8. 按数字键 1、2、3 或 4 完成自评，提交当前题目<br>9. 重复步骤 5–8，直到所有题目复习完，进入 CompletedView<br>10. 点击「返回控制台」回到 Dashboard<br>11. 全程监看 Console 面板 | Console 中无任何红色 Error 条目（包括 React 组件错误、网络 4xx/5xx、EventSource 错误、unhandled Promise rejection） | Console 无红色 Error 条目。黄色 Warning 可酌情忽略，但需记录。 | |
| 2 | Dark Mode 切换后图表坐标轴/Tooltip 颜色跟随变化 | 1. 导航至 `http://localhost:5173/stats`，确保页面有 TrendChart 数据（近 30 天有复习记录）<br>2. 观察当前 Light Mode 下 TrendChart 的 X 轴/Y 轴刻度颜色（应为深色 `#475569`）及 Tooltip 背景（应为白色）<br>3. 点击右上角 Header 中的「🌞 Light」按钮，切换为 Dark Mode<br>4. 再次观察 TrendChart 的 X 轴/Y 轴刻度颜色（应变为浅灰 `#A0A0B0`）<br>5. 将鼠标悬停在折线图上任意数据点，观察 Tooltip 弹出<br>6. 检查 Tooltip 背景色（应为深色 `#16213E`）、文字颜色（应为浅色）<br>7. 同理检查 HeatmapChart 中单元格的 Tooltip（悬停热力格子）<br>8. 再次点击「🌙 Dark」切回 Light Mode，验证颜色恢复 | Dark Mode 下：TrendChart X/Y 轴刻度文字为浅灰色，Tooltip 背景为深色卡片色，文字清晰可读；HeatmapChart Tooltip 同样跟随深色主题；Light Mode 下颜色恢复为深色文字 + 白色背景 | 切换模式后图表颜色立即更新，无需刷新；Dark/Light 两种模式下对比度均满足可读性（文字与背景不重色）。 | |
| 3 | AI 流式输出时容器自动滚动到底部 | 1. 确保后端 `.env` 已配置 `LLM_API_KEY`（AI 功能已启用）<br>2. 导航至 `http://localhost:5173/review`<br>3. 开始复习，按空格键显示答案<br>4. 在「错因复盘」Card 中，**将页面滚动到顶部**（确保 AI 面板不在视口底部）<br>5. 点击「✨ AI 深度分析」按钮，触发流式输出<br>6. 在流式输出进行中（可见「思考中...」加载动画），观察 `.ai-analysis-panel__content` 容器的滚动行为<br>7. 等待输出完成（显示「分析完成」文字），检查最终内容是否完整可见 | 流式输出过程中，当新内容出现导致 AI 分析容器高度增长时，容器内或页面自动滚动，保证最新输出内容始终可见；输出完成后最后一段文字在视口内 | 用户无需手动滚动即可看到实时生成的每一段内容；不出现「内容已生成但被截断在视口外」的情况。 | |
| 4 | 所有错题复习完后 Dashboard「今日已完成」空态样式 | 1. 确保数据库中所有错题的 `next_review_at` 均设置为今天或更早（或直接复习完所有 due 题目）<br>2. 导航至 `http://localhost:5173/dashboard`<br>3. 观察右上角按钮区域：当 `due_count === 0` 时，按钮文字应显示「今日无到期题，仍可随机复习」<br>4. 点击此按钮，跳转至 Review 页，此时 `progress.total === 0`<br>5. 检查此时 Review 页显示的空态：应出现 `ReviewPageState` 组件，显示「恭喜！今天没有需要复习的错题」<br>6. 验证空态页面的副标题「休息一下，或去录入新的错题。」可见<br>7. 验证两个 CTA 按钮「返回控制台」和「去录入」均正常渲染且可点击<br>8. 点击「返回控制台」回到 Dashboard，再次确认按钮文字与空态一致 | Dashboard 按钮文字为「今日无到期题，仍可随机复习」；Review 页出现绿色 success 图标的空态卡片，标题和副标题清晰，两个按钮布局整齐无错位 | 空态组件正常渲染，无白屏/报错；按钮文字与当前 `dueCount` 状态一致；Result 图标、标题、副标题、按钮四个元素均可见。 | |
| 5 | DiffViewer 横向滚动条检查（长代码行） | 1. 进入 Review 复习流程，选择一道包含**长代码行**（单行超过 120 字符）的错题（若无，先在 MistakeEditor 新建一道，Wrong Answer 中输入一行超长代码，如 `const veryLongVariableName = someFunction(param1, param2, param3, param4, param5, param6, param7);`）<br>2. 按空格键显示答案，进入 AnswerView<br>3. 在「代码对比」Card 中找到 Monaco DiffEditor<br>4. 观察 DiffEditor 是否出现横向滚动条（注意：`wordWrap: "on"` 已启用，应自动换行）<br>5. 分别在 1280px 宽度（笔记本）和 1920px 宽度（大屏）下验证<br>6. 拖动浏览器窗口调整宽度，观察 DiffEditor 是否随容器宽度正确 resize（`automaticLayout: true`）<br>7. 检查左侧（Wrong）和右侧（Correct）两个面板在窄窗口下是否均保持可读 | 由于 `wordWrap: "on"` 已配置，长代码行应自动折行；`automaticLayout: true` 使编辑器随窗口 resize；不应出现内容溢出父容器的横向滚动条 | 在 1280px 宽度下无水平溢出滚动；编辑器宽度随窗口变化平滑自适应；若确实出现滚动条，需记录复现步骤和截图。 | |

---

## 前置条件

### 浏览器设置

- 使用 **Chrome 120+**（推荐最新稳定版），以确保 EventSource / CSS `var()` 兼容性
- 分辨率建议：**1280×800**（笔记本模拟）和 **1920×1080**（大屏模拟），部分检查项需切换
- 清除浏览器缓存和 localStorage（DevTools → Application → Clear site data），确保以全新状态进入
- DevTools Console 过滤器设置：显示全部级别（Verbose / Info / Warning / Error），**不要**勾选「Hide network」

### Dark Mode 切换方法

- 点击页面右上角 Header 中的主题切换按钮（显示「🌞 Light」或「🌙 Dark」文字）
- 切换后 `<html>` 标签的 `data-theme` 属性应变为 `"dark"`，可在 DevTools Elements 面板确认
- 主题状态持久化于 `localStorage` 的 `cr-theme` key，测试结束后可手动清除还原

### 种子数据要求

| 检查项 | 最低数据要求 |
|--------|------------|
| 检查项 1（Console 无 Error） | 至少 **3 道**可复习错题，且均配置了 wrong_answer 和 correct_answer 代码 |
| 检查项 2（Dark Mode 图表） | 近 **7 天内**至少完成 **2 次**复习（Stats 趋势图有折线数据），热力图有亮格子 |
| 检查项 3（AI 流式滚动） | 后端 `.env` 中 `LLM_API_KEY` 已配置；至少 1 道错题可触发 AI 分析 |
| 检查项 4（空态样式） | 所有错题 `next_review_at <= today`（或已完成当日全部 due 复习）；也可手动将 `due_count` 归零后刷新 |
| 检查项 5（DiffViewer 横滚） | 至少 1 道错题的 wrong_answer 包含**单行超过 120 字符**的代码；可临时编辑现有错题 |

### 服务启动确认

```bash
# 后端（FastAPI）
cd backend && uvicorn app.main:app --reload --port 8000

# 前端（Vite）
cd frontend && npm run dev
# 默认访问 http://localhost:5173
```

---

## 代码层风险提示

以下是基于阅读实际代码发现的潜在 UI 问题，人工 QA 时需**重点关注**：

### 1. TrendChart Tooltip CSS 变量引用不一致（高优先级）

`TrendChart.tsx` 的 `<Tooltip>` 使用了 `var(--color-bg-card)` 和 `var(--color-text-primary)`，但 `tokens.css` 中 Dark Mode 对应变量为 `--color-bg-card: #16213E` 和 `--color-text-primary: #E0E0E0`。

**风险**：`HeatmapChart.tsx` 的 Tooltip 同样使用 `var(--color-bg-card)` / `var(--color-text-primary)`，但这两个变量在 Dark Mode 下**已定义**，理论上应可跟随切换。实际需确认 Ant Design 的 `Tooltip.overlayInnerStyle` 是否会被 CSS 变量正确解析（部分版本存在 inline style 中 var() 解析问题）。

### 2. AI 分析面板无自动滚动实现（高优先级）

`AiAnalysisPanel.tsx` 的 `.ai-analysis-panel__content` 容器内使用 `ReactMarkdown` 渲染流式内容，但**代码中未见任何 `useEffect` + `scrollIntoView` / `scrollTop` 逻辑**。`useAiAnalysisStream` hook 中每次 `setSnapshot` 更新 content，但不触发滚动。

**风险**：当 AI 输出内容较长（超过容器高度）时，新内容会被截断在容器底部之外，用户需手动滚动。检查项 3 极可能**不通过**，需前端补充自动滚动逻辑。

### 3. DiffViewer `wordWrap` 与横向滚动条的矛盾

`DiffViewer.tsx` 中 Monaco `options` 已设置 `wordWrap: "on"`，正常情况下不会出现横向滚动条。但注意：
- `renderSideBySide: true` 时，左右两个编辑器各占约 50% 宽度，在 **窄视口**（< 900px）下单侧宽度可能不足以触发换行，仍会出现横向溢出
- `scrollBeyondLastLine: false` 可减少底部多余空间，但不影响横向行为
- 建议测试时故意缩窄浏览器窗口至 900px 以下

### 4. Dashboard「今日已完成」没有专门的空态组件

Dashboard 页面（`/pages/Dashboard/index.tsx`）本身**没有独立的「今日已完成」空态**——当 `dueCount === 0` 时仅改变按钮文字为「今日无到期题，仍可随机复习」，空态体验实际发生在 Review 页的 `ReviewPageState` 组件（`progress.total === 0` 分支）。

**风险**：测试步骤中需从 Dashboard 点击按钮进入 Review 页才能看到空态，直接检查 Dashboard 不会看到明显的「空态样式」。若产品预期 Dashboard 本身也应有「今日任务已完成」的专属视觉提示，则当前实现缺失此功能。

### 5. Dark Mode 下 Monaco DiffEditor 主题切换时序问题

`DiffViewer.tsx` 中 `useEffect([theme])` 会在 `theme` prop 变化时调用 `monaco.editor.setTheme(theme)`，但 `monacoRef` 仅在 `onMount` 时赋值。

**风险**：若 Dark Mode 在 Monaco 实例挂载**之前**切换（如页面加载时 localStorage 已存储 `dark`），`monacoRef.current` 为 null，`useEffect` 不执行主题切换，编辑器仍使用初始 `theme` prop 值（通过 `AnswerView` 传入的 `monacoTheme`）。实际上 `AnswerView` 中 `monacoTheme` 是基于实时 `uiTheme` 计算的，所以初始渲染时主题应正确。但如果在 Monaco 已挂载后切换主题而 `onMount` 中的 `monacoRef` 引用失效，可能导致主题不更新。测试时验证：在 AnswerView 已显示 DiffEditor 的状态下，切换 Dark Mode，确认编辑器背景色立即变化。

### 6. CompletedView 缺少「今日零题空态」的专属展示

当 `progress.total === 0`（今日无到期题且用户选择了 `due_first` 策略）时，Review 页展示的是 `ReviewPageState`，而非 `CompletedView`。`CompletedView` 仅在 `completed === true && summary !== null` 时显示（即确实复习了若干题并完成了 session）。

**风险**：检查项 4 的「今日已完成空态」实际上对应两种情形需分别验证：(a) 从未开始复习但 due=0；(b) 复习完所有题目触发 CompletedView。两者 UI 不同，测试时应覆盖两种路径。
