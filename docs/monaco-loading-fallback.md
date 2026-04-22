# Monaco Loading Fallback 设计

## 一. 问题陈述
Monaco Editor 首次加载 workers 通常需要 300ms 至 2 秒的时间，这会导致首屏出现白屏现象，严重影响 Review 和 MistakeEditor 的用户体验。同时，Monaco 占据了 Vite 主包约 1.2MB 的体积，这是 TD-001 中重点关注的性能瓶颈。在 W2 Day 6，我们需要解决两件事：第一，提供 Fallback UI，让用户在等待加载时不会看到白屏；第二，采用动态 import 策略，减小主包体积，让首屏内容能够更快渲染。

## 二. Fallback UI 规范
在 CodeEditor 组件内部，默认的 loading 态视觉规范如下：
- **容器布局**：按传入的 height 属性撑开，内部元素垂直水平居中。
- **视觉元素**：显示一个 Spinner，下方跟随文字提示"编辑器加载中"。
- **尺寸与颜色**：Spinner 尺寸为 24px，使用品牌主色；文字颜色使用 text-secondary。
- **背景**：使用 bg-subtle 作为背景色，便于在页面中占位并与周围环境融合。
- **过渡动画**：当 Monaco 准备就绪切换到编辑器视图时，使用 150ms 的淡入动画（fade-in）实现平滑过渡。

## 三. 动态 import 策略
为了优化加载性能，我们需要将原本直接引入的 `@monaco-editor/react` 改造为按需加载：
- 使用 React.lazy 包装编辑器组件：`export default React.lazy(() => import('./CodeEditorInner'))`。
- 在外层的 CodeEditor 组件中使用 Suspense 将 CodeEditorInner 包裹起来。
- Suspense 的 fallback 属性传入我们在上一节定义的 Spinner 占位组件。
- **效果**：经过改造，Monaco 将被打包到一个独立的 chunk 中，首屏加载时不会拉取该资源，只有当用户进入 Review 或 Editor 页面时，才会按需拉取，从而大幅提升首屏加载速度。

## 四. 实施指引
- **拆分组件**：新建文件 `frontend/src/components/common/CodeEditor/CodeEditorInner.tsx`，将原本的 `@monaco-editor/react` Editor 组件以及 defineTheme 等 onMount 逻辑迁移至此。
- **改造入口**：将现有的 `CodeEditor/index.tsx` 变成一个薄壳组件，内部仅包含 React.lazy 包装、Suspense 容器以及 Fallback UI。
- **DiffViewer 适配**：DiffViewer 也需要进行懒加载改造。左右两个 CodeEditor 共享同一个 inner 模块即可，React.lazy 和打包工具会自动去重，避免重复加载。
- **透明切换**：MistakeEditor 和 Review AnswerView 中的 CodeEditor 引用方式保持不变，实现底层的透明替换。
- **构建配置**：修改 `vite.config.ts`，在 `build.rollupOptions.output.manualChunks` 中增加分割逻辑：将 `node_modules/@monaco-editor` 和 `node_modules/monaco-editor` 单独拆分为名为 `monaco` 的 chunk。
- **包体积分析**：在 `package.json` 中添加脚本 `scripts build:analyze`，使用 `--mode production` 结合自定义插件或 `vite-bundle-visualizer`（可选，作为 TD-001 完成的辅助标志）。

## 五. 主包大小目标
当前 Vite 主包大小约为 1.2MB。
拆分后的目标为：
- 主包体积降低至 <700KB。
- 独立的 Monaco chunk 体积控制在 <700KB。
- 完成拆分后，首屏的 FCP（First Contentful Paint）指标预计应降低 30-50%。

## 六. 验收清单
- 打开 Review 或 Editor 页面时，能看到明显的 Spinner 过渡动画，无白屏闪烁。
- 运行 `npm run build` 后，在 `dist/assets` 目录下能清晰地看到 `monaco-*.js` 的独立产物文件。
- 主包 `index-*.js` 的体积成功下降到 800KB 以下，即可视为本阶段性能优化目标达成。
- 同步在 `tech-debt.md` 的 TD-001 条目末尾追加标记：`✅ Fixed 2026-04-28`。
