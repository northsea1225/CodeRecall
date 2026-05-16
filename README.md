# CodeRecall / 码错本

> **让每一次 AC，都站在错题之上**
>
> SM-2 间隔重复 + 6 阶段动态 AI 教练，把 WA 系统化转化为成长

[![pytest](https://img.shields.io/badge/pytest-245%20passed-success.svg)](backend/tests/)
[![vitest](https://img.shields.io/badge/vitest-49%20passed-success.svg)](frontend/src/)
[![e2e](https://img.shields.io/badge/playwright-13%20passed-success.svg)](frontend/e2e/)
[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](docs/DEVELOPMENT.md)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 山东大学 2026 春季编程共创活动 · 赛道一主题二

| 项 | 内容 |
|---|---|
| 参赛主题 | **赛道一 主题二：编程错题本工具** |
| 团队成员 | **胡博涵**（202500550240，全栈开发） · **董一延**（202433181022，视频制作） |
| 学院班级 | 计算机类（书院）2 班 |
| 开发周期 | 2026-04-22 → 2026-05-17（约 25 天） |
| 仓库地址 | https://github.com/northsea1225/CodeRecall |
| 演示视频 | 见 [`docs/competition/SCREENCAST.md`](docs/competition/SCREENCAST.md) 中的拍摄与提交流程 |
| 原创性声明 | [`docs/competition/ORIGINALITY.md`](docs/competition/ORIGINALITY.md) |
| 联系方式 | 胡博涵 QQ：1563570477 |

---

## 🎯 一句话定位

**面向 OI / ACM / LeetCode 选手的智能编程错题本**——不是把错题塞进数据库就完事，而是用 SM-2 间隔重复算法调度复习节奏，用 6 阶段动态 AI 教练根据复习状态给出针对性诊断。

**核心循环**：导入题目 → 记录错误 → SM-2 间隔重复调度 → 6 阶段动态 AI 深度分析 → AC

---

## ✅ 基础功能完成度（活动要求 ↔ 项目实现）

| # | 活动要求 | 项目实现 | 实现位置 |
|---|---|---|---|
| 1 | **错题添加**（题干 / 错答 / 正答 / 错因 / 分类） | 手动录入 + **LeetCode/CF URL 一键导入**；Monaco 编辑器（VS Code 同款）多语言语法高亮；Markdown + LaTeX (KaTeX) 渲染；AI 自动生成参考代码 | `/mistakes/new` |
| 2 | **错题查询**（按分类 / 关键词搜索） | 全文搜索 + 分类 + 标签 + 掌握度**多维筛选**；分页 + 排序 + 标签云 | `/mistakes` |
| 3 | **错题复习**（随机抽取 / 作答 / 核对 / 提示错因） | **SM-2 间隔重复算法**（非简单随机） + **6 阶段动态 AI 教练** + 键盘快捷键（空格翻牌，1–4 评分） + 复习 session 持久化 | `/review` |
| 4 | **错题删除 / 修改** | 标准 CRUD + **归档**（不删除但移出复习池） + 二次确认 + 草稿恢复 | `/mistakes/:id/edit` |

**4 / 4 基础功能 100% 完成 + 远超基础要求。**

---

## ⭐ 扩展功能（评审加分项）

### 🧠 算法与产品
- **SM-2 间隔重复算法**：基于 SuperMemo 2 公开论文实现，根据评分动态调整下次复习间隔
- **6 阶段 ReviewStage 动态分类**：`new_mistake / early_review / repeated_weakness / lapsed / oscillator / maintenance`——AI 提示词根据状态变化，告别"通用回复"
- **AI 流式输出**（SSE）：错题深度分析实时呈现，体验流畅
- **AI 变体题生成**：基于现有错题自动出变体，巩固训练
- **schema_v3 全量备份**：含 review_logs 历史，UUID 跨设备去重，三层幂等

### 🏗️ 工程化（评审核心加分点）
- **后端 245 测试 / 前端 49 测试 / 14 e2e 测试**，CI gate 防回归
- **Alembic 11 个数据库迁移**，schema 演进可追溯可回滚
- **CI 自动化**：bandit (SAST) + pip-audit + npm audit + bundle-size guard + OpenAPI 漂移检测
- **JWT 安全方案 (C-005)**：HttpOnly Cookie + 双提交 CSRF + jti 黑名单 + silent refresh + Bearer 兼容期
- **41 issue 三方代码审计**：Claude / Codex / Gemini **独立审阅 → 交叉验证 → 修复**（详见 [`docs/audit/2026-04-29/`](docs/audit/2026-04-29/)，本项目最具工程价值的部分）

### 🎨 用户体验
- **暗房沉浸式复习模式**：`/review/immersive` 全屏无侧边栏，专注度拉满
- **Streak 连续打卡** + 7/30 天里程碑提示
- **学习热力图** + 趋势图 + **算法能力雷达图**
- **键盘快捷键**：复习页 `1/2/3/4` 评分，空格翻牌
- **双主题（亮 / 暗）+ 中英双语 i18n**
- **PWA 支持**：可安装到桌面，断网可读已缓存错题
- **首次使用引导页**：4 道经典 C++ 错题（线段树 / DP / Dijkstra / int 溢出）一键载入

### 📥 内容生态
- **LeetCode / Codeforces URL 一键导入**：HTTP + GraphQL + HTML 解析 + MathJax 公式转换
- **AI 生成正确答案**：在编辑器里点 AI 按钮，自动生成参考代码
- **分类下拉内联创建**：录入时直接新建分类，无需切换页面

---

## 🏗 技术栈

```
Frontend                            Backend
─────────────                       ─────────────
React 18                            FastAPI
TypeScript 5                        SQLAlchemy + SQLite
Vite                                Alembic (11 migrations)
Ant Design 5                        PyJWT + passlib (bcrypt)
react-router-dom 7                  pydantic-settings
Zustand 5                           slowapi (rate limit)
Monaco Editor                       httpx
KaTeX (LaTeX)                       markdownify
vite-plugin-pwa + Workbox           uvicorn
i18next (中英双语)                  DeepSeek API (AI)
```

**测试**：pytest / vitest / Playwright **CI**：GitHub Actions (5 个 workflow)

---

## 🚀 30 秒快速运行

### 后端

```bash
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install --require-hashes -r requirements.txt
cp .env.example .env             # 编辑 .env：设置 JWT_SECRET_KEY 与 OLD_USER_INITIAL_PASSWORD
alembic upgrade head
uvicorn app.main:app --reload    # → http://localhost:8000
```

### 前端

```bash
cd frontend
npm install
npm run dev                      # → http://localhost:5173
```

### 演示账号

| 账号 | 用户名 | 密码 | 数据 |
|---|---|---|---|
| 现有数据账号 | `old_user` | `12345678` | 60 道现成错题 |
| 新用户账号（自行注册） | — | — | 空数据，演示 onboarding |

API 文档：http://localhost:8000/docs

---

## 🤖 AI 辅助开发声明（活动鼓励·主动公开）

活动文档原文："**养成善用 AI 辅助开发的硬核习惯**"。本项目作为这种习惯的实践样本，主动公开 AI 辅助开发的全流程方法论：

- 使用 **Claude / Codex / Gemini 三模型协同**（CCG 工作流）
- **41 issue 全部经过三方独立审阅 → 交叉验证 → 队员决策 → AI 落地 → 测试通过的闭环**
- **队员理解每一行代码**，不存在"AI 黑盒"

**完整透明声明**：[`docs/competition/ORIGINALITY.md`](docs/competition/ORIGINALITY.md)

---

## 📂 项目结构

```
.
├── backend/                       # FastAPI 后端
│   ├── app/                       # 业务代码（~6.4k LOC）
│   │   ├── api/routes/            # 11 个路由模块
│   │   ├── models/                # ORM 模型
│   │   ├── schemas/               # Pydantic schema
│   │   ├── services/              # 业务逻辑（含 SM-2 + 6 阶段 AI）
│   │   └── core/config.py         # 强类型配置
│   ├── alembic/versions/          # 11 个数据库迁移
│   ├── tests/                     # 245 个测试
│   └── requirements.txt           # pip-tools 钉版本（含 sha256 hash）
├── frontend/                      # React 前端
│   ├── src/                       # 业务代码（~7.4k LOC）
│   │   ├── pages/                 # 页面组件
│   │   ├── components/            # 共用组件
│   │   ├── stores/                # Zustand 状态
│   │   ├── services/api.ts        # axios + cookie + CSRF
│   │   └── i18n/                  # 中英双语
│   ├── e2e/                       # Playwright (14 cases)
│   └── public/                    # PWA manifest + icons
├── docs/
│   ├── competition/
│   │   ├── ORIGINALITY.md         # 📌 原创性 + AI 透明声明
│   │   └── SCREENCAST.md          # 📌 演示视频教程 + 5min 文案
│   ├── audit/2026-04-29/          # 🏗 三方代码审计报告（亮点）
│   ├── DEVELOPMENT.md             # 开发者技术文档
│   └── openapi.json               # 自动生成的 API 规格
├── .github/workflows/             # 5 个 CI 工作流
├── README.md                      # 本文件（评委入口）
├── SECURITY.md                    # 生产安全 checklist
└── CLAUDE.md                      # AI 协同开发交接文档
```

---

## 📖 文档导航

| 文档 | 面向读者 | 用途 |
|---|---|---|
| [README.md](README.md) | **评委 / 用户** | 项目入口（本文件） |
| [docs/competition/ORIGINALITY.md](docs/competition/ORIGINALITY.md) | **评委** | 原创性 + AI 辅助声明 |
| [docs/competition/SCREENCAST.md](docs/competition/SCREENCAST.md) | **队友董一延 / 评委** | 演示视频 5 分钟完整教程 + 旁白文案 |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | 开发者 | 环境变量 / 依赖更新 / 测试运行 |
| [SECURITY.md](SECURITY.md) | 部署者 | 生产安全 checklist |
| [docs/audit/2026-04-29/](docs/audit/2026-04-29/) | **评委（工程亮点）** | 三方代码审计完整报告 |
| [CLAUDE.md](CLAUDE.md) | 开发协作 | AI 辅助开发会话上下文 |

---

## 📊 项目数据一览

| 维度 | 数字 |
|---|---|
| 代码量 | 后端 6.4k LOC Python + 前端 7.4k LOC TS/TSX |
| 测试 | **245 + 49 + 13 = 307 个测试用例** |
| API 端点 | 43 个 |
| 数据库迁移 | 11 个 Alembic version |
| 已修 issue | 41 / 41（三方审计） |
| Git commits | 58 个（24 天） |
| 开发活跃度 | 约 2.4 commits / 天 |

---

## 📜 License

MIT License — 见 [LICENSE](LICENSE)（如有；未单独写则适用 MIT 默认条款）

---

## 🙏 致谢

- **山东大学 2026 春季编程共创活动**主办方
- 所用开源项目：FastAPI / React / Ant Design / Vite / Monaco Editor / KaTeX / 等等
- AI 协同工具：Claude / Codex / Gemini / oh-my-claudecode (OMC)
- SuperMemo SM-2 算法（Piotr Wozniak）

---

**评委你好** —— 谢谢评审，欢迎在 [GitHub Issues](https://github.com/northsea1225/CodeRecall/issues) 中提问，或联系开发负责人 **胡博涵 QQ 1563570477**。
