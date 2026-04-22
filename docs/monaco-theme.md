# CodeRecall Monaco Editor 主题对接方案

## 一. 主题命名与注册策略
为了在系统中保持统一的视觉体验，我们需要定义并注册两个自定义 Monaco 主题：`coderecall-light` 和 `coderecall-dark`。
在组件初始化阶段，通过调用 `monaco.editor.defineTheme` 注册这两套规则。
当前启用的主题将通过 `uiStore` 的状态或 `document.documentElement` 上的 `data-theme` 属性来决定，确保与全局应用的亮暗色模式同步。

## 二. coderecall-light 规则
`coderecall-light` 主题继承自基础的 `vs` 主题，以确保默认的亮色表现。
- **Colors 映射：**
  - `editor.background`: 使用系统变量 `bg-canvas`
  - `editor.foreground`: 使用系统变量 `text-primary`
  - `editor.lineHighlightBorder`: 使用系统变量 `border-default`
  - `editor.selectionBackground`: 使用系统变量 `color-primary` 并设置透明度为 20%
- **Token Rules 四类核心语义：**
  - `comment`: 映射为 `text-tertiary` 并设置为斜体 (italic)
  - `keyword`: 映射为 `color-primary` 并设置为加粗 (bold)
  - `string`: 映射为 `color-success`
  - `number`: 映射为 `color-warning`

## 三. coderecall-dark 规则
`coderecall-dark` 主题继承自基础的 `vs-dark` 主题，适配暗色环境。
- **Colors 映射：**
  - `editor.background`: 使用系统变量 `bg-canvas-dark`
  - `editor.foreground`: 使用系统变量 `text-primary-dark`
  - `editor.lineHighlightBorder`: 调整为暗色边框适配值
  - `editor.selectionBackground`: `color-primary` 配合适合暗色底的透明度
- **Token Rules 核心语义：**
  同样涵盖 comment、keyword、string 和 number，但对应的颜色值需要调整到暗色底上对比度合适（符合 WCAG 标准）的值。

## 四. 动态注入机制
为了将 CSS 变量注入到 Monaco 中，建议实现一个 `defineMonacoThemes` 的初始化函数。
伪代码逻辑如下：
1. 读取 `getComputedStyle(document.documentElement)` 拿到 CSS 变量当前值（如 `--bg-canvas`）。
2. 将这些 CSS 变量转换为 Monaco 可用的 hex 色值。
3. 分别执行 `defineTheme('coderecall-light', ...)` 和 `defineTheme('coderecall-dark', ...)`。
4. 在 `CodeEditor` 组件的 `onMount` 生命周期里调用一次上述注册逻辑。
5. 监听 `document.documentElement` 的 `attribute change`，当系统主题切换时，重新读取颜色变量并调用 `editor.updateOptions({ theme: newTheme })`。

## 五. 给 Codex 的实施指引
开发执行需按以下步骤更新：
1. 更新 `components/common/CodeEditor/index.tsx`：增加 `onMount` handler 来执行主题注册和加载。
2. 为 `CodeEditor` 组件的 props 增加可选的 `theme` 属性，默认值为 `'coderecall-light'`。
3. `DiffViewer` 内部渲染的两个 `CodeEditor` 实例也要透传此 `theme` 属性以保持一致。
4. 在 `uiStore` 中增加 `theme` 字段，类型为 `'light' | 'dark'`。在 W2 阶段先固定返回 `'light'`，W3 阶段再实现完整的切换 UI 交互。
