# AI 分析面板四态视觉与组件规范

基于前序 UI 规范，本篇进一步明确 `AiAnalysisPanel` 组件在 Review 视图中的交互位置、视觉形态及前端实施指引。

## 一. 组件位置与入口

AI 辅助按钮位于 `AnswerView` 视图下半部分 `error_reason` 卡片的右上角。
交互方式建议采用 **同区域替换下半部分展开** 的形式，保持视觉焦点的连贯性。展开时，卡片高度由约 200px 平滑伸长至 450px，内部留出大块 Markdown 渲染区域（设置 `max-height: 400px`，`overflow-y: auto`）。

```text
+---------------------------------------------------------+
| Error Reason (Your answer's analysis)        [⭐ AI 分析]|
|                                                         |
| 1. ...                                                  |
| 2. ...                                                  |
+---------------------------------------------------------+
                          ↓ 点击展开面板后
+---------------------------------------------------------+
| Error Reason (Your answer's analysis)        [ x 关闭 ]  |
| +-----------------------------------------------------+ |
| | ⭐ 思考中...                                         | |
| |                                                     | |
| | The mistake occurs because the variable is scoped...| |
| | to the block and cannot be accessed outside. |      | |
| |                                                     | |
| +-----------------------------------------------------+ |
|       [ 停止生成 (禁用) ] [ 复制 (禁用) ]                |
+---------------------------------------------------------+
```

## 二. 四态视觉规范

面板具备五种逻辑状态，对应四种核心视觉表现：

*   **禁用态 (Disabled)**:
    *   触发条件：后端 `capability` 接口返回 `enabled: false`。
    *   视觉：按钮灰显且不可点击。
    *   交互：悬浮时显示 Tooltip，引导用户前往 `.env` 填入 `LLM_API_KEY`。
*   **就绪态 (Ready)**:
    *   视觉：按钮采用主色调，带有 ⭐ emoji 前缀。
    *   交互：Hover 时颜色略微加深，点击即可触发 AI 分析流式请求。
*   **流式渲染态 (Streaming)**:
    *   视觉顶部：显示三个点的 Loading 动画以及"思考中"文案。
    *   视觉主体：接收到首个 chunk 后切换为打字机渲染模式，文本尾部出现跟随最后字符的闪烁光标。
    *   视觉底部：操作栏显示"停止"和"复制"按钮，在流完成前处于禁用状态。
*   **完成态 (Completed)**:
    *   视觉：闪烁光标消失，全文经过完整的 Markdown 渲染。
    *   视觉底部：操作栏激活，显示"复制"和"重新生成"两个可交互按钮。
*   **失败态 (Error)**:
    *   视觉主体：展示红色 Error Icon 与具体的错误描述文字。
    *   视觉底部：操作栏显示"重试"和"取消"按钮。

## 三. 组件 Props 与 State 规范

组件 `AiAnalysisPanel` 对外暴露的 Props 定义：

*   `mistakeId`: 必填 `number`，当前错题 ID。
*   `enabled`: 必填 `boolean`，来自 capability 判定是否开启 AI 功能。
*   `model`: 可选 `string`，指定使用的 LLM 模型。
*   `onCopy`: 可选回调函数。
*   `onClose`: 可选回调函数。

前端状态管理 hook `useAiAnalysisStream` 需负责 SSE 连接、chunk 累加组装、请求中断 (abort) 以及重试机制。
Hook 暴露的内部状态字面量：`idle`, `ready`, `streaming`, `completed`, `error`。
Hook 暴露的方法：`text` (当前累加文本), `startStream`, `stop`, `retry`。

## 四. 视觉打磨细节

*   **容器样式**: 卡片底色使用 `bg-subtle` 变量，添加轻量级阴影 `shadow-sm`，圆角设置为 `radius-lg`。
*   **字体排印**: 流式渲染期间，纯代码块或符号尽量使用等宽字体 `JetBrains Mono` 或 `Fira Code`，普通中英文段落回退到系统默认的无衬线字体。
*   **光标动画**: 模拟真实的终端光标，样式采用宽度 `2px` 实线、颜色为主色的 `border-right`，配合 `blink 1s infinite` 的闪烁关键帧动画。

## 五. 给 Codex 的实施指引

1.  组件路径：创建在 `frontend/src/components/review/AiAnalysisPanel.tsx`。
2.  Hook 路径：创建在 `frontend/src/hooks/useAiAnalysisStream.ts`。
3.  **Day 4 任务边界**: 仅实现纯前端骨架及视觉状态切换。接入 capability 控制入口按钮的禁用态；点击时触发 hook，但 hook 内部暂且 `return` 一个 mock 的 `setInterval` chunk 流。**真实的 SSE 联调与网络请求放置到 Day 5 进行**。
4.  **样式约定**: 容器及状态修饰符遵循 BEM 命名：`ai-panel`、`ai-panel--disabled`、`ai-panel--ready`、`ai-panel--streaming`、`ai-panel--completed`、`ai-panel--error`。
