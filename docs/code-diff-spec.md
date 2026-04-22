# Code Diff 视觉升级规范 W3 Day 4 预备

## 一 目标与红线
用 monaco-diff-editor 替代当前双栏并排 CodeEditor，让 wrong 和 correct 的差异在 Review 和 MistakeEditor 中一眼可见。

* Diff 首屏 300ms 内渲染
* 窄屏自动降级双栏或 inline
* dark 模式颜色不失真
* 不要让 diff 编辑器的 scroll 冲突 Review 页的 keyboard hook

## 二 方案对比 monaco-diff-editor vs 双栏并排
* monaco-diff-editor 优势：同行对齐无缝；原生内嵌 hunks 导航；内置 inline 模式切换；与现有 Monaco 共享 worker
* monaco-diff-editor 劣势：对长代码的首次渲染略重 200-300ms；需要额外管理 original/modified 两个 model
* 双栏并排优势：实现简单 现有已有；独立可控；两边可独立编辑（如 W4 想做协同编辑）
* 双栏并排劣势：无法行对齐；Diff 清晰度差；视觉认知负担重
* 决策：W3 Day 4 升级主路径为 monaco-diff-editor 双栏保留为 fallback（窄屏或超长代码）

## 三 DiffViewer v2 接口
* props 保持不变对外兼容：wrongCode correctCode language height theme
* 新增可选 props：renderMode 'side-by-side' 或 'inline' 默认 side-by-side；onHunkChange 当前 hunk 编号回调可选
* 内部实现：使用 @monaco-editor/react 的 DiffEditor 组件
* readOnly 双侧都设 true
* 不展示 minimap lineNumbers on scrollBeyondLastLine false automaticLayout true

## 四 diff 颜色 token 映射
* 添加行 color-success 浅底 green 深字 在 tokens.css 新增 color-diff-add-bg color-diff-add-fg
* 删除行 color-danger 浅底 red 深字 新增 color-diff-remove-bg color-diff-remove-fg
* 修改行 color-primary 浅底 blue 深字 新增 color-diff-change-bg color-diff-change-fg
* 未改动行 保持默认 editor.background
* dark 主题同样 6 个变量 走 dark 色板 color-diff-add-bg-dark 等
* light add bg 对应 #DCFCE7 fg #166534
* light remove bg 对应 #FEE2E2 fg #991B1B
* light change bg 对应 #DBEAFE fg #1E40AF
* dark add bg 对应 #064E3B fg #86EFAC
* dark remove bg 对应 #7F1D1D fg #FCA5A5
* dark change bg 对应 #1E3A8A fg #93C5FD

## 五 渲染模式切换
* Review 页的 DiffViewer 外层加小图标按钮切换 side-by-side 或 inline
* 默认 side-by-side（桌面宽屏）
* 窄屏 md 断点以下自动切 inline（useMediaQuery hook）
* 切换保存到 uiStore.diffMode 字段 持久化到 localStorage
* inline 模式下 diff 用颜色标注行状态 不再分两栏 用户垂直滚动

## 六 hunk 导航工具栏（可选 W3 若时间不足延后）
* DiffEditor 右上角小工具条 显示当前 hunk N / 总 hunks
* 上一 hunk 按钮 Prev 下一 hunk 按钮 Next
* 键盘快捷键 j 下一 hunk k 上一 hunk（和 Vim 风一致）
* 快捷键只在 DiffViewer 有焦点时才生效 避免冲突 Review 页的 1 2 3 4

## 七 性能与 fallback
* 超长代码阈值 wrongCode.length 加上 correctCode.length 大于 50000 字符 触发 fallback
* fallback 规则：关 minimap 只读模式 折叠未改动块
* 再超过 100000 字符：降级到 inline 模式并隐藏 hunk 工具栏
* 极端情况降级到 React 原生 pre code 只读纯文本视图（保底不崩）

## 八 Dark Mode 联动
* DiffViewer 主题 prop 和 CodeEditor 一致 coderecall-light 或 coderecall-dark
* theme.ts 增加 defineDiffTheme 方法 处理 diffEditor 专属 token
* HR2-004 主题切换重 define 同样适用于 DiffEditor（实际 DiffEditor 在同一个 monaco 实例 一次 defineTheme 全局生效）

## 九 a11y
* DiffEditor 外层 role region aria-label 代码对比
* hunk 工具栏每个按钮 aria-label 上一差异 下一差异
* readOnly DiffEditor 告诉屏幕阅读器 aria-readonly true

## 十 实施步骤给 Codex Day 4
* Step 1 装 monaco-editor 依赖（@monaco-editor/react 已有 DiffEditor 但 monaco-editor 需显式装）
* Step 2 新建 frontend/src/components/review/DiffViewer.tsx 替换旧版 保留同 props
* Step 3 新建 frontend/src/components/common/CodeEditor/DiffCodeEditorInner.tsx 薄壳 lazy
* Step 4 tokens.css 加 12 个 diff 变量 6 light 和 6 dark
* Step 5 theme.ts 的 defineCodeRecallThemes 内新增 diff-specific 颜色
* Step 6 Review 的 AnswerView.tsx 使用新 DiffViewer（props 不变）
* Step 7 MistakeEditor 的 双栏 CodeEditor 保留（编辑场景不是 diff）
* Step 8 新增 vitest 覆盖 renderMode 切换 超长代码 fallback
