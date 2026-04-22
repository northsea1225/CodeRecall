# CodeRecall Review 页微交互设计清单

## 一. 转场动画
为了提升做题沉浸感，页面和题目切换时需要柔和的转场：
- 题目切换时，当前的 `AnswerView` 模块淡出（Fade Out），下一题的题干（stem）淡入（Fade In），过渡时间设为 200ms。
- 当达到 Review 完成页时，增加撒花庆祝效果。可以使用 CSS confetti 或者纯 JS 的 `setInterval` 动态创建 50 个 `span` 元素从页面顶部下落，动画持续 3 秒后执行 DOM 清理操作。

## 二. Self-Rate 评分按钮点击反馈
针对用户点击 1-4 分的自评按钮：
- 点击瞬间触发缩放动画：`transform: scale(0.96)` 持续 0.1s，随后立刻回弹至 `1.0`。
- Loading 状态处理：点击后若需等待提交，按钮内的图标替换为 spinner，但文字颜色保持不变。
- 防误触机制：点击任意一个评分按钮后，其余三个按钮的 `opacity` 降为 0.5 且禁用交互，直到 `next_question` 加载完成并渲染新题目。

## 三. 键盘快捷键 Hint 可视化
面向极客用户的快捷键指引：
- 用户首次进入 Review 页时，右下角悬浮滑出一个卡片展示快捷键列表：Space（显示答案）、1-4（提交评分）、Esc（退出 Review）、R（查看原题）。
- 该悬浮卡片展示 3 秒后自动淡出消失。
- 用户之后可以通过按下 `H` 键再次唤起该提示面板。（注：此为可选功能，W2 阶段优先级为做到此为止即可）。

## 四. 进度条过渡效果
- 进度条（Progress bar）增加时，`width` 属性的变化应带有 300ms 的 `ease-out` 过渡动画。
- 进度数字（例如 5/10）直接更新即可，不需要数字跳动（count up）动画，避免视觉上过于累赘。

## 五. AI 分析完成的交互反馈
- 当收到大模型 stream 返回的完成事件后，AI 面板右上角短暂显示一个绿色的对勾图标，持续 0.5 秒后自然消失。
- 面板内的"复制"按钮被点击后，背景色短暂变绿 0.3 秒，同时文案变为"已复制"，随后恢复默认样式和文案。

## 六. 错题 Markdown 渲染规范
- 题干与错因渲染：使用 `react-markdown` 配合 `remark-gfm` 插件以支持表格和任务列表等 Github 风格特性。
- 代码块高亮：使用 `rehype-highlight`（或类似的 `highlight.js` 封装）处理代码块，并确保高亮的 CSS 变量完全适配 `tokens.css` 的背景色与前景色规范。
- 适用范围：W2 Day 5 阶段，上述 Markdown 渲染规则仅限用于 Review 页面中的 `stem` 和 `error_reason` 展示区。由于 `MistakeEditor` 已经全面接入 Monaco Editor，所以编辑器部分不再需要独立的 markdown 预览组件。

## 七. 给 Codex 的实施指引
前端开发指引：
1. 新建 `frontend/src/styles/animations.css` 文件，集中存放所有的复用动画关键帧（keyframes，例如撒花、淡入淡出）。
2. 新建自定义 Hook `frontend/src/hooks/useConfetti.ts` 来封装完成页的撒花逻辑。
3. 在 `frontend/src/pages/Review/index.tsx` 中引入并应用上述动画与交互逻辑。
