# CodeRecall 设计文档索引

## 总览
本文档目录是 CodeRecall 项目的设计、契约和技术债索引，旨在为研发阶段（尤其是前端和后端交互）提供唯一真实来源（SSOT）。
- **更新规则**：契约冻结后变更需评审；UI 和组件随迭代增量更新。
- **贡献流程**：任何设计偏离或新发现的问题，优先记录在 `tech-debt.md` 或本索引中，避免散落于聊天记录。

## 文档清单

| 文件 | 内容范围 | 更新频率 | 主要使用者 |
| :--- | :--- | :--- | :--- |
| `api-contract-w1.md` | 后端 API 契约、数据模型、状态码 | W1 冻结，变更需通知 | Codex 后端 / 前端 service 层 |
| `ui-spec.md` | Dashboard/Editor/Review/Stats 页面线框与布局 | W1-W2 增量更新 | Codex 前端页面开发者 |
| `components.md` | 基础组件 Props、样式样例、色表定义 | W1-W2 增量更新 | Codex 前端组件开发者 |
| `tech-debt.md` | 非阻塞的技术债、架构隐患、遗留问题跟踪 | 持续记录，定期清理 | 所有开发者 / 项目管理者 |
| `handoff-w1-to-w2.md` | W1→W2 交接清单：已完成/入口指引/关键文件 | W 末追加 | 下周入场的 Codex |
| 后续 W2/W3 会增加... | SM-2 算法规范、AI 接入指南等 | 视迭代计划而定 | 算法/AI 负责人 |

## 快速路径
- **我要做后端接口** → 优先阅读 `api-contract-w1.md` 确保字段名和结构一致。
- **我要画新页面** → 到 `ui-spec.md` 找布局结构，到 `components.md` 找可复用组件。
- **我要改 token** → 修改 `frontend/src/design-tokens.json` 后，务必同步更新 `frontend/src/styles/tokens.css`。
- **我发现问题但不阻塞** → 立即追加到 `tech-debt.md`，按 TD 编号记录。

## 设计一致性快查
- **颜色与间距**：只允许使用 `tokens.css` 中定义的 CSS 变量（如 `var(--color-primary)`），**禁止代码中出现魔法数或硬编码颜色**。
- **组件复用**：开发新 UI 前，先在 `components.md` 查阅有无现成组件。若无，抽象后新增至通用组件库并更新文档。
- **API 字段**：严格对齐 `api-contract-w1.md` 的驼峰/下划线命名规范。出现前后端不一致时，**改 contract 不改代码**，确认后再统一修改。
- **组件封装**：前端组件应遵循 `FC + TS interface`，列表型子项需用 `React.memo` 优化重渲染。

## W2 前必看
- `ui-spec.md` §5 (Review) 和 §6 (Stats) 是 W2 和 W3 的核心目标页面，请提前熟悉布局意图。
- `components.md` 明确了组件优先级：W1 完成基础展示，W2/W3 补充高级交互（如 Diff / 统计图）。
- `tech-debt.md` 中的高优项（如选型隐患、TD-003 import skipped 契约）可能会在 W2 初期进行重构，请保持关注。
- `handoff-w1-to-w2.md` 是 W2 开发入场的首份文档。
