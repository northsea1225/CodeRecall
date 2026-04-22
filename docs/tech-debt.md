# CodeRecall 技术债清单

> 跟踪非阻塞但需要 W4 收口前处理的技术问题。

## W1 Day 4 发现（2026-04-21）

### TD-001 · npm 依赖漏洞
- **问题**：`npm install` 报告 5 个 moderate severity vulnerabilities
- **现状**：不阻塞构建/运行，但发布前需清零
- **建议**：W4 收口时跑 `npm audit fix` → 不能自动修的看逐条评估 → 必要时升级主版本
- **责任人**：Codex（W4）

### TD-002 · Vite 主包过大
- **问题**：`npm run build` 输出 `dist/assets/index-*.js` 约 1.2 MB，触发 Vite chunk size warning
- **影响**：首屏加载慢，演示视频录制可能体感卡顿
- **建议方向**：
  - antd 按需加载（已默认 tree-shake，但 icons/locale 可以再压）
  - Monaco Editor 走动态 import（`lazy()` + `Suspense`）—— W2 接入 Monaco 时顺带做
  - React Router 路由级 code split（`lazy()` 每个 page）
  - 考虑把 echarts/recharts 单独拆 chunk（W3 引入图表时）
- **责任人**：Codex（W3 接入 Monaco 和图表时分别处理，W4 最终验收）
- `✅ Fixed 2026-04-28`

### TD-003 · Import/Export 契约与运行时返回不一致
- **问题**：`docs/api-contract-w1.md` 将 `POST /import` 的 `skipped` 描述为计数字段，但后端运行时实际返回 `ImportSkip[]`
- **现状**：W1 前端已按运行时实现接入，不阻塞导入流程
- **建议**：W2 开始前统一文档、后端 schema、前端类型的口径，避免后续 Review/批量导入页重复适配
- **责任人**：Codex（W2）
- `✅ Fixed 2026-04-23`

### TD-004 · Dark Mode 主题切换一致性
- **问题**：W3 Dark Mode 需要覆盖全局主题、Monaco 主题和页面状态色，避免 light/dark 切换后视觉割裂
- **现状**：✅ 已完成（Day 5）
- **责任人**：Codex（W3 Day 5）
- `✅ Fixed 2026-04-25`

### TD-005 · JSON 导入导出版本兼容
- **问题**：导入导出 JSON 需要区分旧 v1 文件和带 `schema_version` 的 v2 文件，避免后续字段扩展破坏导入
- **现状**：✅ 已完成（Day 5）
- **责任人**：Codex（W3 Day 5）
- `✅ Fixed 2026-04-25`

---

## 记录约定
- 发现一条 → 追加一条，不要覆盖
- 字段：ID / 发现时间 / 问题 / 现状 / 建议 / 责任人
- 解决后在条目末尾加 `✅ Fixed YYYY-MM-DD` 但不删除（便于回溯）
