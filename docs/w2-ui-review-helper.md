# W2 UI 审阅辅助材料 (给 Claude 的速查指南)

### 一. W2 交付的 UI 清单
- **MistakeList**: 搜索 + 筛选联动 + 空态三种（真·空态/筛选无果/搜索无果） + 错误态 + 分页。
- **MistakeEditor**: 双栏 Monaco 编辑器 + Monaco 主题对接 + 表单字段必填/长度校验。
- **Review 主流程**: Dashboard 入口 CTA（开始复习） + 题面展示（StemView） + 展开答案（Show Answer） + 自评打分（Self-Rate） + 结算完成页 + 撒花动画。
- **Review 键盘交互**: Space/1-4/Esc/R/H 五个全局快捷键绑定及解除。
- **Review 辅助组件**: 退出二次确认框 (ExitConfirmModal) + 原始题目抽屉 (RawMistakeDrawer) + AI 分析面板 (AiAnalysisPanel) 的 5 种状态切变。
- **Dashboard**: "Coming Soon" 的 Stats 图表占位区 + 突出显示的"开始复习" CTA 按钮。

### 二. 设计一致性 self-check 清单
- [ ] **颜色规范**: 是否所有颜色均使用 `tokens.css` 变量（如 `var(--color-primary)`），无硬编码 Hex 值。
- [ ] **间距规范**: 是否所有 margin/padding 使用 `spacing-*` 变量。
- [ ] **空态引导**: 空态场景是否都配有引导 CTA（如"添加第一道错题"），而不仅是"暂无数据"。
- [ ] **快捷键提示**: Review 界面的快捷键是否在 Hint 卡片中全部完整列出。
- [ ] **AI 状态平滑过渡**: AiAnalysisPanel 的四种动态切换（禁用/ready/streaming/completed/error）是否无明显视觉跳变（高度突变）。
- [ ] **Monaco 加载回退**: Monaco Editor 异步加载时，是否有 loading fallback 骨架屏避免白屏。
- [ ] **响应式降级**: 移动端 (`md` 断点以下) 的布局降级是否已覆盖所有四个主要页面（List/Editor/Review/Dashboard）。
- [ ] **文案一致性**: 页面所有静态文案是否都能在 `copywriting-final.md` 中追溯并完全一致。
- [ ] **错误反馈**: 错误 Toast 提示是否都附带了明确的下一步行动或重试 CTA 文案。
- [ ] **高危操作**: 删除错题、中途退出复习等高危操作是否都具备二次确认弹窗。

### 三. 键盘快捷键交叉验证表
- **Space** / 场景：Review 尚未展开答案时 / 预期行为：触发 `showAnswer` 展开答案解析 / 相关文件定位：`components/review/StemView.tsx` 或 `pages/Review/index.tsx` 的 keydown hook
- **1 2 3 4** / 场景：Review 已展开答案时 / 预期行为：分别对应 `Again/Hard/Good/Easy` 触发 `submitRate` / 相关文件定位：`components/review/SelfRateGroup.tsx`
- **Esc** / 场景：Review 任意时刻 / 预期行为：暂停计时并弹出 `ExitConfirmModal` / 相关文件定位：`components/review/ExitConfirmModal.tsx` 及外层 hook
- **R** / 场景：Review 任意时刻 / 预期行为：侧边划出 `RawMistakeDrawer` 查看题目原始详情 / 相关文件定位：`components/review/RawMistakeDrawer.tsx`
- **H** / 场景：Review 任意时刻 / 预期行为：唤起或隐藏右下角快捷键 Hint 卡片 / 相关文件定位：快捷键统一管理 hook 中

### 四. 给 Claude 的重点审阅建议 (代码结构与契约)
- **契约一致性**: 后端 `ReviewSessionOut` 对应前端 `ReviewSession` 字段必须严格对齐。特别关注 `completed_count` / `total_count` 以及 `next_item` 为 `null` 时的前端边界处理。
- **重复提交幂等**: 对于同一个 `(session_id, mistake_id)`，如果因网络延迟发生二次 submit 请求，前端处理逻辑和后端返回值是否健壮（返回旧 log 而不是报 duplicate 崩溃）。
- **SM-2 策略分支**: 前端不必关心，但确保后端 `progress_updater` 里 `strategy='random'` 和 `'spaced_repetition'` 的差异处理是否干净，有无遗漏字段更新。
- **AI 降级展示**: 当后端配置或特性开关 `capability=false` 时，前端 AI 按钮必须处于 `disabled` 状态，并且 tooltip 提示文字需和环境变量中定义的占位文案一致。
- **AI 错误码映射**: 后端抛出的 401/402/429/408/504/5xx 等异常，前端拦截后的用户侧展示文案是否严格参照 `copywriting-final.md` 的规定。
- **Monaco lazy 失败**: 当 Monaco 编辑器 chunk 懒加载失败时（如弱网 404），是否有完整的 Error Boundary 或回退显示。

### 五. 非审阅项（Claude 不用看）
- W3 阶段才会实现的真实数据驱动 Stats 图表。
- 社交网络分享功能。
- 多语言 i18n 支持（计划于 W4）。
- AI 分析面板中的大模型切换器 (Premium UI)。
