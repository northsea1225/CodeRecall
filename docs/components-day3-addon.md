# Review 新增组件规范

## 一. DiffViewer
- **用途**: 在 Review 的答案展示阶段，左右双栏对比展示 wrong 和 correct 代码。在 W2 阶段使用双栏 Monaco 编辑器只读模式，W3 可无缝升级为官方的 Monaco Diff Editor。
- **Props**:
  - `wrongCode`: string
  - `correctCode`: string
  - `language`: string (默认值: 'plaintext')
  - `height`: number | string (默认值: 400)
- **实现建议**: 基于 `components/common/CodeEditor` 进行双栏渲染。配置 `readOnly: true`, `minimap: { enabled: false }`, `lineNumbers: 'on'`。左侧顶部放置 Wrong 徽章（`color-danger`），右侧顶部放置 Correct 徽章（`color-success`）。响应式 `md` 断点以下切换为垂直堆叠展示。
- **最小 JSX 骨架**:
  ```tsx
  <Row gutter={16}>
    <Col xs={24} md={12}>
      <Badge color="danger" text="Wrong" />
      <CodeEditor value={wrongCode} language={language} readOnly height={height} />
    </Col>
    <Col xs={24} md={12}>
      <Badge color="success" text="Correct" />
      <CodeEditor value={correctCode} language={language} readOnly height={height} />
    </Col>
  </Row>
  ```

## 二. SelfRateGroup
- **用途**: 展示四个难度评分按钮（Again, Hard, Good, Easy）。
- **Props**:
  - `disabled`: boolean (提交进行中时禁用全部按钮)
  - `onRate`: (result: ReviewResult) => void (点击回调)
  - `loading`: ReviewResult | null (标记当前哪个按钮处于提交加载态)
- **实现建议**: 桌面端四个按钮横向等宽排列，在 `sm` 断点下变为 2x2 grid 网格。数字徽章用 `span` 绝对定位在左上角。键盘 1-4 快捷键监听由父组件 Review 统一处理，本组件只负责渲染和点击回调。
- **最小 JSX 骨架**:
  ```tsx
  const RATE_CONFIG = [
    { key: '1', value: 'again', label: 'Again', color: 'danger' },
    { key: '2', value: 'hard', label: 'Hard', color: 'warning' },
    { key: '3', value: 'good', label: 'Good', color: 'primary' },
    { key: '4', value: 'easy', label: 'Easy', color: 'default' },
  ];
  // render
  <div className="rate-group">
    {RATE_CONFIG.map(btn => (
      <Button
        key={btn.key}
        disabled={disabled}
        loading={loading === btn.value}
        onClick={() => onRate(btn.value)}
        className={`rate-btn-${btn.color}`}
      >
        <span className="shortcut-badge">{btn.key}</span>
        {btn.label}
      </Button>
    ))}
  </div>
  ```

## 三. ExitConfirmModal
- **用途**: Review 页面中按下 ESC 键或点击退出按钮时，触发的二次确认弹窗。
- **Props**:
  - `open`: boolean
  - `onConfirm`: () => void
  - `onCancel`: () => void
- **最小 JSX 骨架**:
  ```tsx
  <Modal
    title="确认退出复习？"
    open={open}
    onOk={onConfirm}
    onCancel={onCancel}
    okText="确认退出"
    cancelText="继续复习"
    maskClosable={false}
  >
    <p>本次进度会保留，你可以稍后继续。</p>
  </Modal>
  ```

## 四. RawMistakeDrawer
- **用途**: R 键触发的侧边抽屉，用于在复习时临时查看原始错题详细信息。
- **Props**:
  - `open`: boolean
  - `mistakeId`: number | null
  - `onClose`: () => void
- **实现建议**: 使用 antd 的 Drawer 组件，`placement="right"`，`width={480}`。内容区域展示 title, category, tags, source, difficulty 等基础字段以及 created_at, updated_at。数据 Loading 状态下展示 3 行 Skeleton。明确不展示 wrong, correct 和 error_reason 字段避免与答题区重复。

## 五. 给 Codex 的集成清单
- Review `index.tsx` 必须拆分为三个子视图：`StemView`、`AnswerView`、`CompletedView`。
- 新增的 4 个组件代码全部收敛到 `components/review` 目录下。
- Dashboard 的 "开始复习" CTA 区域使用 `StatCard` 或标准的 `Card` 组件。
- 色彩表统一走 `tokens.css` 中定义的 `--color-*` 前缀变量。
- 键盘快捷键 (ESC, R, 1-4, Space 等) 必须在 Review 页的主组件统一监听处理，禁止分散下放到子组件中。
- `SelfRateGroup` 和 `ExitConfirmModal` 组件结构简单，建议编写 RTL (React Testing Library) 单元测试（可选）。
