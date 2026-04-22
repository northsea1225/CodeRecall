# CodeRecall W2 -> W3 Handoff

## W2 里程碑清单

- [x] **M1** 4 个 blocker 全关闭
- [x] **M2** 搜索链路前后端打通
- [x] **M3** 基础 Review 闭环可用
- [x] **M4** SM-2 纯算法落地 + 独立策略层
- [x] **M5** AI 错因分析骨架可开关可降级
- [x] **M6** 后端 pytest + 前端关键测试通过

## W2 冻结范围

- 冻结目标：保留 W2 主线可演示能力，不在本次交接里继续扩写 README、index 或额外 review package
- 验证脚本：`scripts/freeze_w2.sh`
- 冻结口径：后端测试、前端类型检查、Vitest、生产构建都通过后，输出 `frozen ok`

## W3 入口指引

### 1. Stats 真实图表

- 当前 `Stats` 还是 W1/W2 占位骨架，入口在 `frontend/src/pages/Stats/index.tsx`
- W3 建议接入真实聚合接口，并把占位卡片替换为 ECharts 图表
- 推荐顺序：
  1. 先补后端统计接口契约
  2. 再接 ECharts 折线 / 柱状 / 热力或分布图
  3. 最后补加载、空态、错误态和响应式布局

### 2. Code Diff 升级

- 现有差异对比入口在 `frontend/src/components/review/DiffViewer.tsx`
- 当前已经接了 Monaco `DiffEditor`，但仍偏基础配置
- W3 可升级为更完整的 `monaco-diff-editor` 体验：
  - 更细的只读区块配置
  - 高亮粒度优化
  - 差异导航、折叠和更好的移动端降级

### 3. SM-2 UI 切换

- Review 策略状态入口在 `frontend/src/stores/reviewStore.ts`
- `reviewStore.startSession` 已支持 `strategy` 参数，默认仍是 `random`
- W3 需要把策略选择暴露到 Review UI，让用户可以在 `random` 和 `spaced_repetition` 之间切换
- 推荐实现：
  - 在 Review 开始前加 strategy selector
  - 选项文案明确区分“随机复习”与“间隔复习”
  - 保留默认值和回退逻辑，避免旧入口失效

### 4. i18n 国际化

- W2 文案已明显增多，W3 开始继续硬编码会抬高维护成本
- 建议先从页面级高频文案开始拆：
  - `MistakeList`
  - `Review`
  - `Stats`
  - 通用空态 / 错误态 / 按钮文案
- 推荐先定字典结构、语言切换机制，再逐页迁移

## W3 关键文件 Quick Ref

- Stats 页：`frontend/src/pages/Stats/index.tsx`
- DiffViewer 升级入口：`frontend/src/components/review/DiffViewer.tsx`
- Review strategy store 入口：`frontend/src/stores/reviewStore.ts`
- Review strategy 调用点：`reviewStore.startSession(payload)`，其中 `payload.strategy` 控制 `random` / `spaced_repetition`
- Review 页面入口：`frontend/src/pages/Review/index.tsx`
- Review 请求封装：`frontend/src/services/reviewService.ts`
- Review 类型定义：`frontend/src/types/review.ts`

## 已知遗留

- `docs/tech-debt.md` 仍保留 `TD-001`：前端 npm 依赖存在 moderate severity vulnerabilities
- 该项当前不阻塞 W2 冻结，但建议在 W4 收口前清零
- 除上述技术债外，本次 handoff 未额外记录新的 W2 阻塞遗留

## W3 建议开工顺序

1. 先做 Stats 聚合接口和真实图表，尽快把占位页替换掉
2. 再做 Review strategy UI，让 `random` / `spaced_repetition` 从 store 能力升级到用户可选能力
3. 然后完善 DiffViewer 交互，把 Review 的代码对比体验抬起来
4. 最后推进 i18n，把新增文案统一收口

## Future 增强

- Code Diff 升级：支持更强的差异导航、局部折叠和审阅级展示
- Review 分享：支持把单条复习总结或题目卡片导出分享
- 社交排行：引入 streak / review count / mastery 等维度的轻量排行

## 交接结论

- W2 主线目标已完成，当前代码基线适合进入 W3 功能扩展
- W3 不建议先大改底层；优先沿现有 Review / Stats / store / service 结构递进扩展
