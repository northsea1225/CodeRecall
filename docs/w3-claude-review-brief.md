## 全局状态速览
- 当前测试数字：pytest 75 passed，vitest 28 passed
- Alembic 当前迁移版本：0004_review_log_time_spent (head)
- Build 状态：成功；保留 Vite chunk size warning
- Day 7 真实 AI SSE 验收：未通过；接口返回 `event: error` / `ai_service_unavailable`，未产生含“根因”或 4 小节标题的内容流

## 免检清单（Claude 不必深看）
- UI 样式代码（global.css/tokens.css 颜色值）
- 基础 CRUD 路由（mistakes/categories/tags）
- 文档区（docs/*.md）
- dist/ 构建产物

## 精准狙击点（Claude 重点看这4处）
1. stats_service.py + test_stats_api.py — 聚合口径、跨天边界、弱点排序
2. review/selector.py + due-count — due_first 语义、next_review_at <= now 严格性
3. uiStore.ts + tokens.css + CodeEditorInner.tsx — Dark Mode 全链路一致性
4. DiffViewer.tsx + prompt_templates.py + ai.py — Diff可读性、SSE心跳、注入防御

## 已知技术债（不需要 Claude 重构建议）
- npm 5个 moderate 漏洞（依赖链，非直接引入）
- Vite chunk size warning（antd体积，可接受）
- AI endpoint 依赖外部 API（演示时需确认 wzw.pp.ua 可用）

## W3 里程碑完成状态
| 里程碑 | 状态 |
|---|---|
| M1 W2 遗留 5+2 个 BL/HR 全关（Day 1） | [x] 已确认 |
| M2 Stats 4 接口 + Recharts 图表全部真实 | [x] 已确认 |
| M3 Dashboard 显示今日到期 + due_first 闭环 | [x] 已确认 |
| M4 DiffViewer 升级 monaco-diff-editor + 窄屏 fallback | [x] 已确认 |
| M5 Dark Mode 全链路（Review/Stats/Dashboard/Modal/Drawer 全覆盖） | [x] 已确认 |
| M6 AI Prompt v2 固定 4 小节 + 语言分支 | [x] 已确认 |
| M7 pytest + vitest + build + 真实 AI 验收全绿 | [!] 部分完成：pytest/vitest/tsc/build 全绿；真实 AI SSE 返回 `ai_service_unavailable`，未满足内容标题验收 |
