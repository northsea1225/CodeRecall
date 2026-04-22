# CodeRecall (码迹) 🚀

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)
![Node 18+](https://img.shields.io/badge/Node-18%2B-green.svg)
![pytest](https://img.shields.io/badge/pytest-passing-success.svg)
![vitest](https://img.shields.io/badge/vitest-passing-success.svg)

**CodeRecall** is an intelligent, spaced-repetition-based programming mistake notebook designed to help developers learn from their errors efficiently.

<!-- CodeRecall 是一款基于间隔重复算法的智能编程错题本，旨在帮助开发者高效地从错误中学习。 -->

## ✨ Features

* 🧠 **Spaced Repetition (SM-2):** Optimized review scheduling to ensure long-term retention of programming concepts. (基于 SM-2 算法的间隔重复复习)
* 🤖 **AI-Powered Analysis:** Streaming SSE integration with LLMs (Claude/Gemini) for deep root-cause analysis of mistakes. (AI 驱动的错题根因深度分析)
* 📊 **Comprehensive Dashboard:** Visual insights including trend charts, heatmaps, and weak area identification. (包含趋势图、热力图和薄弱环节的全面数据看板)
* 📝 **Rich Code Editing:** Monaco editor integration with syntax highlighting and code fence support. (集成 Monaco 编辑器，支持语法高亮)
* 🔄 **Import/Export v2:** Seamlessly backup and restore your mistake library. (便捷的错题库导入/导出)
* 🏷️ **Categorization & Filtering:** Organize mistakes by language, framework, or custom tags. (灵活的分类和标签过滤)

## 🏗️ Architecture Overview

```text
+-------------------+       REST API & SSE       +-------------------+
|   Frontend (UI)   | <------------------------> | Backend (API)     |
|                   |                            |                   |
| - React 18        |                            | - FastAPI         |
| - TypeScript      |                            | - SQLAlchemy      |
| - Vite            |                            | - SQLite          |
| - Monaco Editor   |                            | - AI Integration  |
| - Tailwind CSS    |                            | - SM-2 Engine     |
+-------------------+                            +-------------------+
```

## 🚀 Quick Start

### Backend Setup (后端运行)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend Setup (前端运行)

```bash
cd frontend
npm install
npm run dev
```

## ⚙️ Environment Variables

Create a `.env` file in the `backend` directory:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQLite connection string | `sqlite:///./coderecall.db` |
| `AI_API_KEY` | Your LLM API Key (Claude/Gemini) | `""` |
| `AI_PROVIDER` | LLM Provider (e.g., `anthropic`, `google`) | `anthropic` |
| `CORS_ORIGINS` | Allowed frontend origins | `http://localhost:5173` |

## 🔌 API Endpoints Overview

Key routes available at `http://localhost:8000/docs`:

* `GET /api/mistakes/` - List mistakes with pagination and filtering
* `POST /api/mistakes/` - Create a new mistake entry
* `GET /api/mistakes/{id}` - Get mistake details
* `PUT /api/mistakes/{id}` - Update a mistake
* `POST /api/reviews/` - Submit a review (triggers SM-2 update)
* `GET /api/reviews/due` - Get mistakes due for review today
* `GET /api/stats/dashboard` - Get dashboard statistics (heatmaps, trends)
* `GET /api/ai/analyze/{id}` - Stream AI analysis via SSE

## 🛠️ Development Commands

### Backend

```bash
# Run tests
pytest

# Format code
black app tests

# Lint code
flake8 app tests
```

### Frontend

```bash
# Run tests
npm run test

# Type check
npm run type-check

# Build for production
npm run build
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
<!-- 欢迎提交 PR 参与贡献！ -->

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request
