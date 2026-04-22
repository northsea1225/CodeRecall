# AI 错因分析流式渲染 UI W2 Day 2

## 1. 组件位置
放置于 Review 页面 `error_reason` 卡片的右上角操作区。作为附加分析按钮。
W2 Day 2 仅需确认组件 shape 和 UI 规范，W2 Day 5 正式接入 API。

## 2. 五个状态
| 状态 | 触发条件 | UI 表现 | 文案 |
|---|---|---|---|
| **禁用** | 无 API Key 配置 | 按钮灰显 (`--color-text-muted`) + Tooltip | "AI 分析未配置，前往设置添加" |
| **就绪** | 已配置，待点击 | 按钮 `primary` 色，带 ✨ Icon | "✨ AI 深度分析" |
| **加载** | 点击后等首个 chunk | 按钮变 Loading / 区域打字机预热 | "思考中..." (点阵动画) |
| **流式渲染** | 持续接收 chunk | 字符逐个出现，尾部带闪烁光标 | (动态生成的 Markdown 文本) |
| **完成** | SSE stream 结束 | 光标消失，全文完整 Markdown 渲染 | "分析完成" (短暂提示后消失) |
| **失败** | 请求/网络报错 | 错误 Icon + 红色提示，带重试按钮 | "分析失败，点击重试" |

## 3. 流式实现建议
- **通信协议**：强烈推荐使用 `EventSource` (SSE)，浏览器原生支持且比 fetch streaming 更好管理连接状态。
- **前端架构**：
  - 创建 `useAiAnalysisStream` hook，负责连接建立、chunk accumulation（累加）、断开与 abort。
  - 支持**断线重连**：网络波动时自动 retry 1 次，失败后才显示错误 UI。

## 4. 视觉规范
- **容器**：使用 Card 组件，`padding: var(--spacing-lg)`，`box-shadow: var(--shadow-sm)`。
- **打字机效果**：
  - CSS animation: `border-right: 2px solid var(--color-primary)` 加上 `blink` 动画。
  - 尾部光标必须紧跟最后一个字符。
- **字体**：正文使用常规无衬线体，遇到反引号代码块强制使用等宽字体 (JetBrains Mono / Fira Code)。
- **主题适配**：
  - 亮色: `--color-bg-subtle` 底色，深灰文本。
  - 暗色: `--color-surface-elevated` 底色，亮灰文本。

## 5. 降级方案
- **无 Key 时**：按钮 `disabled`，Tooltip 提示"AI 分析未配置，前往设置添加 OpenAI API Key"。
- **HTTP 429**：显示"请求过于频繁，稍后重试"。
- **HTTP 5xx**：显示"AI 服务暂时不可用"。

## 6. 给 Codex 的实施提示
- 组件文件定位：`frontend/src/components/review/AiAnalysisPanel.tsx`
- Hook 定位：`frontend/src/hooks/useAiAnalysisStream.ts`
- 接口预留：`POST /api/v1/ai/analyze/stream` (SSE 格式返回数据)
- **注意**：Day 2 阶段只需完成纯前端的 UI Mock 和组件骨架，Day 5 才会正式联调后端接口。
