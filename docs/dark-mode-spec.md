# CodeRecall Dark Mode Design Specification

## 1. 三态设计说明
- **设计状态**: light（默认）/ dark / system auto
- **交付范围**: W3 仅交付 light 和 dark 两种状态，system auto 作为 W4 的 stretch goal。
- **关于 system auto**: W3 不做 system auto 的主要原因是实现成本与演示价值的权衡。System auto 需要监听系统级的 `prefers-color-scheme` 媒体查询并在其变化时动态更新应用状态，这会增加状态管理的复杂度以及跨平台测试的成本。对于 W3 的演示目标而言，提供明确的手动切换（light/dark）已经足够展示应用的灵活性和视觉效果，将精力集中在核心功能和两种基础主题的打磨上收益更高。

## 2. 主题切换 UI
- **切换开关位置**: 顶栏（Header）右侧，使用 Ant Design 的 Switch 组件，并搭配 Sun☀️ / Moon🌙 图标。
- **切换动画**: 全局过渡动画设置为 `transition: all 300ms ease;`，确保背景色、文字色等切换平滑。
- **持久化**: 用户的选择需持久化存储，localStorage key 为 `cr-theme`。

## 3. CSS Token 映射表
| Token | Light | Dark | 用途 |
| :--- | :--- | :--- | :--- |
| `--cr-bg-base` | `#ffffff` | `#141414` | 全局应用基础背景色 |
| `--cr-bg-container` | `#ffffff` | `#1f1f1f` | 容器组件背景色（如卡片、模态框） |
| `--cr-bg-elevated` | `#ffffff` | `#262626` | 悬浮层背景色（如 Dropdown、Tooltip） |
| `--cr-text-primary` | `rgba(0, 0, 0, 0.88)` | `rgba(255, 255, 255, 0.85)` | 主要文本颜色 |
| `--cr-text-secondary`| `rgba(0, 0, 0, 0.65)` | `rgba(255, 255, 255, 0.65)` | 次要文本颜色（如辅助说明） |
| `--cr-border` | `#d9d9d9` | `#424242` | 基础边框颜色 |
| `--cr-border-divider`| `#f0f0f0` | `#303030` | 分割线颜色 |
| `--cr-primary-color` | `#1677ff` | `#1668dc` | 主色调（按钮、高亮状态等） |
| `--cr-primary-hover` | `#4096ff` | `#3c89e8` | 主色调悬浮状态 |
| `--cr-error-color` | `#ff4d4f` | `#d9363e` | 错误提示/危险操作颜色 |
| `--cr-success-color` | `#52c41a` | `#49aa19` | 成功状态颜色 |
| `--cr-warning-color` | `#faad14` | `#d89614` | 警告状态颜色 |

## 4. Monaco Editor / DiffViewer 联动机制
- **主题联动**: 当 `uiStore` 中的 `theme` 发生变化时，触发 `monaco.editor.setTheme` 更新编辑器主题。如需自定义主题，需先通过 `monaco.editor.defineTheme` 注册。
- **主题名映射**: 
  - `light` 映射到 `coderecall-light`
  - `dark` 映射到 `coderecall-dark`
- **已知问题与解决方案**: Monaco Editor 初次加载或主题切换时可能会出现短暂的白屏闪烁。建议在加载期间展示骨架屏（Skeleton），或使用 `opacity` 渐入动画平滑过渡。

## 5. Recharts 暗色调色板
- **Tooltip**: 背景色 `#262626`，文字色 `rgba(255, 255, 255, 0.85)`，确保对比度 ≥ 4.5:1。
- **Grid 线**: 颜色使用 `#303030`（与 `--cr-border-divider` 保持一致或略浅），降低视觉干扰。
- **Axis 文字**: 颜色使用 `rgba(255, 255, 255, 0.65)`（与 `--cr-text-secondary` 保持一致）。
- **图表数据色**:
  - **趋势图折线**: 使用暗色模式下的主色调 `#1668dc` 或更明亮的高亮色 `#177ddc`。
  - **热力图 (Level 1-4)**: 建议采用渐变的绿色或主色调变体，例如：
    - Level 1: `#112a45`
    - Level 2: `#15395b`
    - Level 3: `#175685`
    - Level 4: `#1677ff`

## 6. 演示注意事项
- **最佳切换时机**: 建议在包含丰富代码块（Monaco Editor）和数据图表（Recharts）的“复习回顾”或“统计概览”页面进行主题切换演示。这样能最大程度展现主题切换的全局一致性和对复杂组件的支持，视觉冲击力最强。
- **已知风险及缓解方案**:
  - **风险**: 部分第三方组件（如弹窗、特定图表元素）在暗黑模式下样式失效或对比度不足。
  - **缓解方案**: 演示前仔细检查核心流程页面的暗色表现；对于难以快速覆盖的第三方样式，可通过全局 CSS 强制覆盖，或者在演示时避免操作那些边缘组件。
