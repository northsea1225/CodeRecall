# W2 页面状态 Map

## MistakeList

| 状态 | 触发条件 | UI 表现 | 文案引用 | 是否 W2 做 |
|---|---|---|---|---|
| 空库 | DB 无记录 | EmptyState 居中 (描述文字用 `--color-text-secondary`) | 引导录入错题 | 是 |
| 筛选无结果 | 条件无匹配 | EmptyState (Icon + Text) | "当前筛选条件下无错题" | 是 |
| 搜索无匹配 | 关键词无匹配 | EmptyState (Icon + Text) | "未找到匹配的错题" | 是 |
| 加载中 | 请求 API pending | 骨架屏或 Spinner | "正在检索错题..." | 是 |
| API 错误 | 500/网络中断 | Error 组件 + 重试按钮 | "列表加载失败，请重试" | 是 |
| 分页溢出 | 请求不存在页码 | 禁用下一页按钮 | (无) | 是 |
| 删除确认 | 点击删除图标 | Modal 覆盖当前页 | 删除确认弹窗标题/Body | 是 |

## Review

| 状态 | 触发条件 | UI 表现 | 是否 W2 做 |
|---|---|---|---|
| 无到期题 | 无需 review 题目 | EmptyState 庆祝插画 | 是 |
| 进行中·未Show | 刚进入/下一题 | 仅显 Stem 和可选错因，底部巨大 Show Answer | 是 |
| 进行中·已Show | 点击 Show Answer | 展开 Diff Editor，底部呈现四个 Self-Rate 按钮 | 是 |
| 进行中·已Rate | 点击 Rate 按钮 | 按钮 Loading 短暂过渡，随后切换至下一题 | 是 |
| 会话完成 | 队列耗尽 | Stats 卡片 + 撒花效果 + 回 Dashboard 按钮 | 是 |
| 提交失败 | Rate 接口报错 | 按钮变红 (使用 `--color-error`) + Toast 提示 | 是 |
| AI 分析禁用 | 无 key 时 | 按钮灰显 + Tooltip 提示去设置 | 否(扩展) |
| AI 分析加载 | 点击 AI 诊断 | 骨架屏 / 打字机预热 | 否(扩展) |
| AI 分析失败 | 请求超时/报错 | 错误文本 (`--color-error`) + 重试按钮 | 否(扩展) |
| AI 分析成功 | 流式返回完毕 | Markdown 渲染分析结果 (`--color-text-primary`) | 否(扩展) |

## 其他

| 状态 | 场景差异与 UI 表现 |
|---|---|
| Editor 模式 | 新建：字段全空，主按钮"创建"；编辑：回填原数据，主按钮"保存修改"。 |
| ImportExport | 导入中：禁用所有交互，显进度条；完成/失败：触发对应 Toast 并在右上角展示。 |
| ErrorBoundary | 捕获 React 级崩溃，整页展示 Fallback UI (居中 Icon + 报错原因)，提供"刷新页面"按钮。 |
