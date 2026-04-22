# Review 主流程交互稿 W2 Day 2

## 1. 完整用户旅程
```text
[Dashboard] --(点击"开始复习")--> [fetch /review/session]
  --> (状态: showing_stem) 首题加载完成
  --> (思考) --> [点击 Show Answer]
  --> (状态: showing_answer) 展开Diff与错因，显示4个打分按钮
  --> [点击 Good (评分)] --> (状态: submitting)
  --> [切下一题] --(循环直至结束)--> (状态: completed)
  --> [完成页] --> 返回 Dashboard
```

## 2. 题面阶段（Before Show Answer）
```text
+--------------------------------------------------------------+
| [X] (ESC退出)                 进度: 3 / 10 [====----]        |
|                                                              |
| [Tag: Python] [★★★]                          2026-04-18创建 |
|                                                              |
| 题目内容 (Stem - Markdown)                                   |
| var(--font-size-lg), var(--line-height-relaxed)              |
|                                                              |
|                 +------------------------+                   |
|                 |    Show Answer (Space) |                   |
|                 +------------------------+                   |
+--------------------------------------------------------------+
```

## 3. 答案阶段（After Show Answer）
```text
+--------------------------------------------------------------+
| [Code Diff] (Monaco Editor)                                  |
| 左侧: Wrong Code                  右侧: Correct Code         |
|                                                              |
| [Error Reason] (Markdown Card)                  [✨ AI 分析] |
| 这里是错误原因的详细解释...                                  |
|                                                              |
| 请评估掌握程度:                                              |
| +--------+  +--------+  +--------+  +--------+               |
| | 1 Again|  | 2 Hard |  | 3 Good |  | 4 Easy |               |
| +--------+  +--------+  +--------+  +--------+               |
|  < 1 min      1 day       3 days      7 days                 |
+--------------------------------------------------------------+
```
*颜色: Again(`--color-danger`), Hard(`--color-warning`), Good(`--color-success`), Easy(`--color-primary`)*

## 4. 完成页
```text
+--------------------------------------------------------------+
|                           🎉                                 |
|                   复习完成！太棒了！                         |
|                                                              |
|  [ 统计信息 ]                                                |
|  本次复习: 10 题      用时: 5 分 30 秒                       |
|  Again: 2 次          Good+Easy: 8 次                        |
|                                                              |
|        [ 返回 Dashboard ]    [ 再来一轮 ]                    |
+--------------------------------------------------------------+
```

## 5. 键盘交互映射表
| 场景 | 按键 | 动作 |
|---|---|---|
| showing_stem | `Space` / `Enter` | 展开答案 (Show Answer) |
| showing_answer | `1`, `2`, `3`, `4` | 对应提交 Again, Hard, Good, Easy |
| 全部 Review态 | `Esc` | 退出复习（弹出二次确认 Modal） |
| showing_answer | `R` | 查看本题原始错题详细信息 |

## 6. 异常态处理
- **网络断线**：UI 顶部全局 Toast 提示"网络已断开，请检查连接"。禁用提交按钮。
- **Session过期**：(>30min未操作) 弹窗提示"会话已过期，请重新开始"，点击返回Dashboard。
- **提交失败**：打分按钮变红，提示"保存失败，点击重试 (Retry)"。
- **无到期题**：Empty State 图标 + "当前没有需要复习的题目，休息一下吧！"

## 7. 给 Codex 的实施提示
- 状态机(`reviewStore`): `idle` → `loading_session` → `showing_stem` → `showing_answer` → `submitting` → `next_question`/`completed`/`error`。
- 本地缓存当前题目的进度，防止用户误刷新导致 Session 丢失。
- 社交分享、AI 分析接入不在 W2 Day 2 实装（留到 Day 5）。
