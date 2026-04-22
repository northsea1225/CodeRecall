# CodeRecall 组件规范 W1 Day 4

## 1. 原子组件 (Atoms)

### 1.1 Button
用途：触发应用内的各项操作（提交、取消、删除等）。
变体：`primary`, `secondary`, `ghost`, `danger`
尺寸：`sm` (24px), `md` (32px), `lg` (40px)

| Prop | Type | Default | Description |
|---|---|---|---|
| variant | `'primary'\|'secondary'\|'ghost'\|'danger'` | `'primary'` | 按钮视觉变体 |
| size | `'sm'\|'md'\|'lg'` | `'md'` | 按钮尺寸 |
| loading | `boolean` | `false` | 是否处于加载中状态 |
| disabled | `boolean` | `false` | 是否禁用 |
| onClick | `React.MouseEventHandler` | - | 点击事件回调 |

**Token 引用:** `var(--color-primary)`, `var(--radius-md)`, `var(--spacing-2)`
**交互态规范:**
- Hover: 亮度降低 / 增加透明度
- Active: 缩放 0.98, 加深颜色
- Disabled: `opacity: 0.5`, `cursor: not-allowed`

```tsx
import { Button } from 'antd';
import type { ButtonProps as AntdButtonProps } from 'antd';

export interface ButtonProps extends AntdButtonProps {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
}

export const AppButton: React.FC<ButtonProps> = ({ variant = 'primary', ...props }) => {
  return <Button className={`app-btn app-btn-${variant}`} {...props} />;
};
```

### 1.2 Input
涵盖标准输入框、多行文本域和搜索框。

| Prop | Type | Default | Description |
|---|---|---|---|
| status | `'error'\|'warning'\|'success'\|''` | `''` | 校验状态 |
| prefix | `React.ReactNode` | - | 前置图标 |
| suffix | `React.ReactNode` | - | 后置图标 |
| size | `'sm'\|'md'\|'lg'` | `'md'` | 尺寸 |

**Token 引用:** `var(--color-border)`, `var(--color-error)`, `var(--radius-sm)`

```tsx
import { Input } from 'antd';
import type { InputProps } from 'antd';

export const AppInput: React.FC<InputProps> = (props) => {
  return <Input className="app-input" {...props} />;
};
// AppInput.TextArea = Input.TextArea;
```

### 1.3 Tag
用途：标识语言、框架、错误原因或自定义标签。

| Prop | Type | Default | Description |
|---|---|---|---|
| label | `string` | - | 标签文本 |
| color | `string` | `'default'` | 预设颜色或 hex 值 |
| closable | `boolean` | `false` | 是否可关闭 |
| onClose | `() => void` | - | 关闭回调 |

**LangBadge / ErrorReasonBadge 色表:**
- Python: `#3572A5`
- TypeScript: `#3178C6`
- SQL: `#E38C00`
- React: `#61DAFB`
- Error (默认): `var(--color-error)`

```tsx
import { Tag } from 'antd';
import type { TagProps } from 'antd';

export interface AppTagProps extends TagProps {
  label: string;
}

export const AppTag: React.FC<AppTagProps> = ({ label, ...props }) => {
  return <Tag className="app-tag" {...props}>{label}</Tag>;
};
```

## 2. 容器组件 (Containers)

### 2.1 Card
用途：承载仪表盘指标、错题详情或列表项。

| Prop | Type | Default | Description |
|---|---|---|---|
| title | `React.ReactNode` | - | 卡片标题 |
| extra | `React.ReactNode` | - | 右上角操作区 |
| hoverable | `boolean` | `false` | 是否有悬浮浮起效果 |
| padding | `'none'\|'sm'\|'md'\|'lg'` | `'md'` | 内容区内边距控制 |

**Token 引用:** `var(--shadow-sm)`, `var(--shadow-md)` (hover), `var(--radius-lg)`, `var(--color-surface)`

```tsx
import { Card } from 'antd';
import type { CardProps } from 'antd';

export interface AppCardProps extends CardProps {
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

export const AppCard: React.FC<AppCardProps> = ({ padding = 'md', ...props }) => {
  return <Card className={`app-card pad-${padding}`} {...props} />;
};
```

### 2.2 EmptyState
用途：列表无数据、搜索无匹配、网络或加载错误时的占位。

| Prop | Type | Default | Description |
|---|---|---|---|
| title | `string` | - | 主提示文案 |
| description | `string` | - | 辅助说明文案 |
| action | `React.ReactNode` | - | 操作按钮 (如"刷新"、"去创建") |

**场景样板:**
- 列表空: "暂无错题记录" / "开始记录你的第一个 Bug 吧"
- 搜索无结果: "未找到匹配项" / "请尝试调整搜索关键词或过滤条件"
- 加载失败: "数据加载失败" / "请检查网络连接后重试"

```tsx
import { Empty } from 'antd';

export interface EmptyStateProps { title: string; description?: string; action?: React.ReactNode; }
export const EmptyState: React.FC<EmptyStateProps> = ({ title, description, action }) => (
  <Empty description={<><strong>{title}</strong><br/>{description}</>}>{action}</Empty>
);
```

### 2.3 Modal
用途：弹出式表单（如新增错题）、确认对话框。

| Prop | Type | Default | Description |
|---|---|---|---|
| open | `boolean` | `false` | 控制显示隐藏 |
| title | `React.ReactNode` | - | 弹窗标题 |
| size | `'sm'\|'md'\|'lg'\|'full'` | `'md'` | 弹窗宽度 |

**规范:**
- 动画: 采用轻量级的淡入和微小的 translateY 移动 (`var(--transition-normal)`)
- a11y: 打开时焦点自动捕获到第一个可交互元素，支持 ESC 键关闭，遮罩层点击可关闭。

```tsx
import { Modal } from 'antd';
import type { ModalProps } from 'antd';

export const AppModal: React.FC<ModalProps> = (props) => {
  return <Modal centered destroyOnClose maskClosable {...props} />;
};
```

## 3. 目录结构建议

推荐的 `frontend/src/components/` 组织方式：

```text
components/
├── common/        # 原子组件 (与业务无关)
│   ├── Button/
│   │   ├── Button.tsx
│   │   ├── Button.module.css
│   │   └── index.ts
│   ├── Input/
│   └── Tag/
├── layout/        # 页面布局容器 (AppLayout, Sidebar)
├── mistake/       # 业务特定组件 (MistakeRow, LangBadge, CodeViewer)
└── stats/         # 统计面板组件 (KPICard, ChartContainer)
```

## 4. 共享规则

- **类型定义:** 所有组件必须是 Function Component (FC) + TypeScript。Props 使用 `interface` 定义，并导出类型以便复用。
- **样式方案:** 样式优先使用 `tokens.css` 中的 CSS 变量（如 `var(--spacing-4)`，`var(--color-text-primary)`），严禁在组件代码或 CSS 中写死魔法数值 (Magic Numbers)。
- **导出规范:** 每个组件目录导出一个默认组件以及命名导出的 Props 类型（如 `export type { ButtonProps }`）。
- **性能优化:** 统一 memoize 规则，对于 `StatCard`、`MistakeRow` 等渲染频繁或处于长列表中的组件，统一使用 `React.memo` 包裹以避免不必要的重渲染。

## 5. Codex Day 4 实施优先级

- **W1 Day 4 必做:** Button, Input, FormField, EmptyState, Card（基础版）。保障核心 CRUD 的表单和列表能够跑通并具备基础样式。
- **W1 Day 5 可做:** Tag / LangBadge, Modal, StatCard。完善展示细节、状态标识和交互弹窗。
- **W2+ 扩展:** DiffViewer, SelfRateGroup, KPICard, HeatmapPlaceholder。用于后续的艾宾浩斯复习功能和深度统计分析模块。
