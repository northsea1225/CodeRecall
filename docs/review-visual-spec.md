# Review 视觉与组件规范

## 一. Self-Rate 按钮组语义层级
- **Again**: 危险色语义 / 引用变量 `color-danger` / 危险按钮 (Danger Button)
- **Hard**: 警告色语义 / 引用变量 `color-warning` / 警告按钮 (Warning Button)
- **Good**: 主色语义 / 引用变量 `color-primary` / 主按钮 (Primary Button)
- **Easy**: 次级色语义 / 引用变量 `color-primary-transparent` 或 `text-secondary` / 次按钮或文本按钮 (Default/Text Button)
- **尺寸与间距**: 高度 48px（触屏友好），组件间距 `spacing-md` (16px)，最小宽度 120px，保持四个按钮等宽。
- **交互焦点**: 外边框 2px，按下状态 (active) 缩放比例 `scale(0.96)`，并配有 0.1s 的 transition 动画。
- **快捷键提示**: 数字徽章 `1`/`2`/`3`/`4` 使用小圆标样式，放置在按钮左上角。

## 二. 进度条视觉
- **尺寸**: 宽度 100%，高度 8px。
- **颜色**: 底色使用 `bg-subtle`，进度填充色使用 `color-primary`。
- **文案**: 右侧进度文字展示 `N/M` 格式，颜色使用 `text-secondary`。

## 三. ESC 退出二次确认（补 D2-002）
- **Modal 规范**:
  - `title`: 确认退出复习？
  - `body`: 本次进度会保留，你可以稍后继续。
  - `okText` (确认按钮): 回 Dashboard
  - `cancelText` (取消按钮): 返回 Review
  - `maskClosable`: false（防止点击遮罩层误触退出）

## 四. R 键查看原始错题（补 D2-003）
- **Drawer 规范**:
  - `placement`: right
  - `width`: 480px
  - **展示字段**: 仅展示 `title`, `category`, `tags`, `source`, `difficulty`, `created_at`, `updated_at`。
  - **屏蔽字段**: 不重复展示 `wrong`, `correct`, `error_reason`，避免视觉冗余。
  - **Loading 态**: 内容加载中时展示三行 `Skeleton` 骨架屏。

## 五. 移动端 md 断点降级
- **showing_stem 阶段**: 进度条贴近顶部，Stem（题干）字号下降一级。Show Answer 按钮固定吸底，退出按钮文字替换为 "X" 图标。
- **showing_answer 阶段**: Code Diff 视图由左右双栏变为垂直堆叠（上方展示 Wrong，下方展示 Correct），Self-Rate 按钮组由单行横排折叠为 2x2 网格。
- **完成页 (CompletedView)**: 统计数据卡片变为单列布局，底部 CTA（Call to Action）按钮变为全宽自适应。

## 六. Dashboard 入口 CTA 文案
- `title`: 你今天的错题复习
- `主按钮`: 开始复习 (N题)
- `二级文案`: 预计小于 5 分钟完成
