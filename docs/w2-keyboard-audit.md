# W2 纯键盘交互闭环审计

### 一. 完整 Review 键盘路径
**用户可全程脱离鼠标完成复习闭环**：
使用 `Tab` 键聚焦页面主要内容 → 按下 `Space` 开始会话（此时焦点位于 Dashboard 的 "开始复习" 主按钮上） → 进入 Review 页面后等待题目加载 → 按下 `Space` 展开答案及 AI 解析 → 从 `1-4` 数字键中选择一个提交评级 → 页面自动切换并加载下一题 → 循环上述步骤直至完成全部复习 → 进入结算完成页，此时自动 `Tab` 焦点位于 "返回 Dashboard" 按钮 → 按下 `Enter` 返回首页 → **完成整个闭环**。

### 二. Focus 管理规范
- Review 页面首次进入且题目加载完成后，默认焦点需赋予 "Show Answer" 按钮（即 `showing_stem` 态）。
- 答案展开（Self-Rate 态）时，焦点应自动转移到 "Good" 打分按钮上（最常用的正向预期按键）。
- 完成全部复习进入结算页时，焦点自动移到 "返回 Dashboard" 的主推操作上。
- Modal（如退出确认框）打开时，焦点必须被捕获（Trap）到 Modal 内部的第一个可交互元素（如取消按钮）。
- Modal 关闭后，焦点必须安全回退到触发该 Modal 之前的按钮上。
- Drawer 组件（如原始题目抽屉）的焦点捕获规则与 Modal 保持一致。

### 三. a11y 最小合规
- 所有没有纯文本子节点的 Button 必须具备非空的 `aria-label`。
- Modal 容器必须添加 `role="dialog"` 且设置 `aria-modal="true"`。
- 顶部的复习进度条必须具有 `role="progressbar"` 并准确配置 `aria-valuenow` / `aria-valuemin` / `aria-valuemax`。
- 嵌入的 Monaco 容器在外层应提供 `role="textbox"` 并附带 `aria-label`，同时根据页面态正确设置 `aria-readonly`。
- 页面悬浮的键盘 Hint 卡片绝对不能抢占焦点流（建议配置 `pointer-events: none` 并在视觉上独立，或脱离主 Tab 顺序）。

### 四. 给 Codex 的闭环修复清单 (Next Action)
- [ ] **Day 7 P1**: 在 `Review` 页面的 `useEffect` 中增加逻辑，确保在不同状态切换时 `focus` 正确的首个交互按钮。
- [ ] **Day 7 P1**: 排查 `ExitConfirmModal` 和 `RawMistakeDrawer`，确认 Ant Design（或对应 UI 库）的 focus trap 功能是默认开启并正常工作的。
- [ ] **Day 7 P2**: 为 `Self-Rate` 组件中的四个打分按钮分别添加 `aria-keyshortcuts="1"` 等属性。
- [ ] **Day 7 P2**: 确保复习完成页的 CTA 按钮设置了 `autoFocus`。

### 五. 测试建议
- **手工全链路**: 完全断开或不触碰鼠标（仅使用 Tab、Enter、Space、1-4、Esc），完整走完 `Dashboard` → `Review` → `结算` → 返回 `Dashboard` → 进入 `MistakeEditor` 编辑一条错题 → 保存返回。
- **三大验证维度**: 1) 流程是否能 100% 走通； 2) 每一步的焦点视觉指示环（Focus Ring）是否清晰可见； 3) 是否存在 Tab 键陷阱导致陷入死循环无法跳出的情况。
