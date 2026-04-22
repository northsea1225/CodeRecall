# Stats 页完整设计文档

## 一 页面目标与红线
展示错题学习轨迹与弱点分布，让用户看见进步和下一步复习重心。
体验红线：4 个 KPI 数字首屏 500ms 内出现；图表加载不跳跃；空库不白屏；移动端单列可读。

## 二 页面顶部过滤器
- 时间范围：Select 选项，过去 7 天 / 30 天 / 90 天，默认 30 天
- 时区：前端从 `new Date().getTimezoneOffset()` 反推 `tz_offset_minutes` 参数（如中国 UTC+8 是 +480），用户不需要手动切换
- 右侧刷新按钮：强制 re-fetch 四个接口，保证数据最新

## 三 4 张 KPI 卡设计
- 总题数 Total Snaps：
  - 字段：`total_mistakes` 计数（含 archived）
  - 副标：其中 active N 题，mastered N 题
  - 图标：书签
- 总复习次数 Total Reviews：
  - 字段：`reviewed_7d`（最近 7 天）
  - 副标：今日 N 次
  - 图标：复习循环
- 当前连击 Current Streak：
  - 字段：`streak_days`
  - 副标：连续复习天数
  - 图标：火焰
  - 样式：`streak >= 7` 时，使用 token `color-success` 高亮
- 平均掌握度 Avg Mastery：
  - 字段：`avg_accuracy_7d` 百分比展示
  - 副标：avg_ease_factor F 值
  - 样式：`<60%` 使用 token `color-warning`，`>=80%` 使用 token `color-success`

## 四 热力图 Review Heatmap
- 数据结构：52 周 x 7 天（或所选 days 范围内天数）；每 cell 包含 `date` (YYYY-MM-DD), `count`, `level` (0-4)
- 颜色映射（依据 `tokens.css`）：
  - level 0 用 `color-bg-subtle`
  - level 1-4 用 `color-success` 的不同 alpha 或混合色阶递进
- 交互设计：hover cell 显示 tooltip，文案格式为"某月某日 完成 N 次复习"
- 空库状态：显示一整块浅灰色的占位图，叠加 copywriting"开启复习即可点亮小格子"

## 五 错因分类饼图
- 数据聚合策略（W3）：
  - 当前后端无 `error_reason_tag` 字段，W3 不新增后端接口
  - 决策：前端复用 `top-weak` 接口的 `category_name` 字段，使用前端 groupby 聚合处理数据
  - 标题定为"弱点分类分布"，而不是"错因分类"
- 色板规范：固定 6 色，走 `tokens.css` 主色系（如 primary, success, warning, info 等），避免过于花哨
- 交互交互：hover 扇区时，tooltip 显示分类名 + 题数 + 占比百分比
- 未来规划（W4）：评估后端是否接入 `error_reason_tag` 字段以做真正的错因聚合

## 六 语言分布柱图
- 数据来源：与饼图同源，由前端将 `top-weak` 列表数据做 `groupby language` 聚合
- 坐标轴设计：
  - x 轴：语言名（如 Python, TypeScript, Go 等）
  - y 轴：题数（整型刻度）
- 展现策略：固定取 Top 5 语言，剩余项合并计入"Other"柱子

## 七 Top 弱点列表
- 表头定义：题目、Language、Category、状态、复习次数、最近结果、Weak Score
- 视觉标记：
  - `last_result`：若为 `again` 标红（`color-danger`），`good/easy` 标绿（`color-success`）
  - `overdue_days > 0`：整行或状态列标黄（`color-warning`），并提示"过期 N 天"
- 交互行为：点击数据行，触发路由跳转至 `/mistakes/:id` 查看详情
- 空库状态：展示插图，配文"加油，还没有弱点就是最大的优势"，整体搭配松弛感

## 八 Recharts 选型理由
- 体积优势：Recharts 打包体积约 150KB gzip，远小于 ECharts 的约 600KB gzip
- 框架契合度：React 友好，声明式 JSX 写法与项目风格一致（相比之下 ECharts 需要繁琐的 ref 和配置对象）
- 功能匹配度：W3 只需实现饼图、柱图、折线图，功能足够；热力图采用原生 CSS Grid 实现，不走图表库
- 性能考量：主包压力较大，W2 刚把 bundle 优化到 600KB 以下，坚决不因图表库再次膨胀

## 九 响应式降级
- Tablet 级降级（md: `<768px`）：
  - 4 个 KPI 卡片重排为 2x2 grid 布局
  - 热力图容器开启横向滚动（`overflow-x: auto`）
  - 饼图与柱图从左右并排改为垂直堆叠布局
- Mobile 级降级（sm: `<640px`）：
  - KPI 卡片完全单列排列（1x4）
  - 所有图表组件强制 `max-width: 100vw` 并适配边距

## 十 空态 / 加载态 / 错误态
- 空态处理：所有 KPI 归 0，展示"还没有数据，开始录入错题"的 CTA 按钮，点击跳转至 `/mistakes/new`
- 加载态 (Loading)：使用 Skeleton 骨架屏；KPI 数字区使用 `Skeleton.Button`，图表区使用 `Skeleton.Image` 或大块矩形
- 错误态 (Error)：统一使用 Alert 组件，文案"网络错误请重试"，并附带 Retry 按钮重新触发 fetch

## 十一 文案字典（引用 copywriting-final.md）
- "总题数" / "总复习次数" / "当前连击" / "平均掌握度"
- "弱点分类分布" / "语言分布" / "复习热力图"
- "近 7 天" / "近 30 天" / "近 90 天"
- "开启复习即可点亮小格子"
- "加油，还没有弱点就是最大的优势"

## 十二 给 Codex 的实施优先级
- Day 2 必做（P0）：4 个 KPI 卡片 + 热力图 + Top-weak 列表的基础实现和渲染
- Day 3 开发内容：饼图 + 柱图（基于 top-weak 数据纯客户端聚合，无需等后端新接口）
- 暂缓项：复杂动画转场（推迟到 W4 的打磨期统一优化）
- 基础动画规范：若要做，饼图 hover 稍微放大；柱图带简单的自下而上顺序出场；转场时间严格控制在 200ms 以内，避免视觉拖沓和噪声

## 十三 跟 Day 3 的 Diff spec 的接口
- 关联性：Stats 页本身不直接使用 Diff 组件；但用户在 Top-weak 列表点击具体题目跳转至 `/mistakes/:id` 后，会进入 Editor 并使用 Diff 展示 `wrong_code` 与 `correct_code`
- 视觉一致性要求：需保证全局 tokens 的一致性，Day 3 Diff 的 color 约定（如错误底色/高亮色）必须和 Stats 页面的语义色保持高度一致（弱点=红 `color-danger`，正确=绿 `color-success`），确保用户心智模型的统一
