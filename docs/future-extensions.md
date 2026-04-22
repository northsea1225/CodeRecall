# 🚀 码迹 (CodeRecall) 未来扩展规划

本文档详细规划了码迹 (CodeRecall) 项目未来的 6 个核心扩展方向，旨在进一步提升开发者的错题记录与复习体验。

---

## 1. VS Code 插件 (VS Code Extension)

**解决的问题 (Problem Solved):**
开发者目前需要离开 IDE 才能记录错题，打断了心流。通过 VS Code 插件，可以在编写代码、调试报错时，直接划选代码并一键记录到码迹后台。

**技术方案 (Technical Approach):**
*   使用 VS Code Extension API 开发插件。
*   注册上下文菜单 (Context Menu) 和快捷键，允许用户选中代码片段（包含错误代码、正确代码或报错信息）。
*   提供一个 Webview 侧边栏表单，用于快速补充错误原因和分类。
*   通过 REST API (`POST /api/mistakes/`) 将数据同步到 CodeRecall 后端。
*   使用 VS Code 的 `SecretStorage` 安全存储后端 API Token。

**预估复杂度 (Complexity):** M (中等)

**依赖项 (Dependencies):**
*   `vscode` 扩展开发 SDK
*   CodeRecall 后端需增加 API Token 认证机制

---

## 2. 多模态 OCR 识别 (Multi-modal OCR)

**解决的问题 (Problem Solved):**
有时错误信息存在于无法复制的终端截图、第三方工具界面或网页中，手动录入成本高。

**技术方案 (Technical Approach):**
*   前端支持图片上传或剪贴板粘贴图片。
*   后端集成视觉大模型 API (如 GPT-4o Vision, Claude 3.5 Sonnet, 或 Gemini 1.5 Pro)。
*   将用户上传的截图发送给 Vision API，提示词要求其提取图中的代码、报错堆栈，并自动填充到新建错题表单的对应字段中。
*   在前端提供识别结果的预览与二次编辑功能。

**预估复杂度 (Complexity):** M (中等)

**依赖项 (Dependencies):**
*   支持 Vision 的 LLM API Key
*   前端图片处理与上传组件

---

## 3. 团队/共享错题库 (Team/Shared Mistake Library)

**解决的问题 (Problem Solved):**
目前为单机单用户版。团队开发中，许多错误是共通的，共享错题可以避免团队成员踩同样的坑，加速知识沉淀。

**技术方案 (Technical Approach):**
*   **重构数据库模型**：引入 `User`, `Team`, `TeamMistake` 等实体，通过外键关联错题与用户/团队。
*   **权限控制 (RBAC)**：引入 JWT 认证和角色权限管理，区分公开错题、私有错题和团队内可见错题。
*   **协作功能**：允许团队成员对错题进行评论、点赞或补充解决方案。
*   **复习隔离**：即使是共享错题，每个用户的复习进度（SM-2 状态）也必须独立计算和存储（多对多关联表的扩展）。

**预估复杂度 (Complexity):** L (高)

**依赖项 (Dependencies):**
*   `python-jose` / `passlib` (JWT 认证)
*   数据库迁移 (Alembic) 成本较高
*   前端路由守卫与状态管理改造

---

## 4. 间隔重复算法升级 (Spaced Repetition Improvements)

**解决的问题 (Problem Solved):**
SM-2 算法较为基础。同时，部分重度 Anki 用户希望将错题导出至 Anki 统一复习。引入更现代的 FSRS 算法能提高记忆效率。

**技术方案 (Technical Approach):**
*   **Anki 导出**：后端增加 `GET /api/export/anki` 接口，使用 `genanki` 库将错题数据（包含代码高亮 HTML）打包生成 `.apkg` 文件。
*   **FSRS 算法支持**：后端引入 `fsrs-python` 或自行实现 FSRS 核心逻辑。在系统设置中允许用户切换复习算法 (SM-2 / FSRS)。
*   数据库模型增加 FSRS 所需的状态字段 (如稳定性 `stability`，难度 `difficulty` 等)。

**预估复杂度 (Complexity):** M (中等)

**依赖项 (Dependencies):**
*   `genanki` (Python 库)
*   FSRS 算法库

---

## 5. 移动端应用 (Mobile App)

**解决的问题 (Problem Solved):**
利用碎片化时间（如通勤、排队）进行错题复习，提高学习效率。

**技术方案 (Technical Approach):**
*   **方案 A (PWA)**：使用现有的 React + Vite 前端，添加 `manifest.json` 和 Service Worker，实现 PWA，使其可以在手机桌面安装并提供类原生体验。优先优化响应式布局 (Tailwind CSS 移动端适配)。
*   **方案 B (React Native / Expo)**：复用前端的 TypeScript 业务逻辑和状态管理，使用 React Native 重写 UI 层。这种方式能提供更好的性能和原生手势体验，适合长期发展。
*   提供离线复习模式，在有网络时与后端同步数据。

**预估复杂度 (Complexity):** L (高) - 若采用 React Native

**依赖项 (Dependencies):**
*   Vite PWA 插件 (若选 PWA)
*   Expo CLI, React Native 体系 (若选 RN)

---

## 6. LLM 个性化微调 (LLM Fine-tuning)

**解决的问题 (Problem Solved):**
通用的 AI 分析可能不够贴合用户个人的技术栈和常见的思维盲区。通过微调，AI 能提供更具针对性的建议。

**技术方案 (Technical Approach):**
*   **数据准备**：增加数据导出功能，将用户长期积累的高质量错题（包含用户自己修正的原因、AI 的初始分析等）格式化为 JSONL 微调数据集。
*   **模型微调**：利用云厂商（如 OpenAI, Google Cloud Vertex AI）的微调接口，使用用户的数据对模型进行 Fine-tuning。
*   **RAG 替代方案**：鉴于微调成本较高，优先实现 RAG (检索增强生成)。将用户的历史错题向量化存入向量数据库 (如 Qdrant / Chroma)。在 AI 分析新错题时，先检索出用户历史上相似的错误，作为 Prompt 上下文，从而提供个性化的分析。

**预估复杂度 (Complexity):** L (高)

**依赖项 (Dependencies):**
*   LangChain / LlamaIndex (RAG 实现)
*   向量数据库环境
*   微调 API 的预算与配额
