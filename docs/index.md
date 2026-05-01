# CodeRecall 文档索引

## 核心文档

| 文件 | 内容 |
| :--- | :--- |
| [README.md](../README.md) | 项目介绍、快速启动、环境变量 |
| [SECURITY.md](../SECURITY.md) | 安全策略、生产部署安全检查清单 |
| [CHANGELOG.md](../CHANGELOG.md) | 版本变更记录（Keep a Changelog 风格） |

## 技术文档

| 文件 | 内容 |
| :--- | :--- |
| [docs/openapi.json](openapi.json) | 当前完整 API 契约（OpenAPI 3.x，由 `scripts/gen-docs.sh` 从 FastAPI 自动生成；不要手改） |
| Swagger UI | 启动 backend 后访问 `http://localhost:8000/docs`（或 `/redoc`） |
| [docs/deployment-guide.md](deployment-guide.md) | 生产部署指南（环境配置、反向代理、SSE、数据库备份） |
| [docs/release-runbook.md](release-runbook.md) | 发布检查清单与重置步骤 |

## 设计与规范（历史参考）

| 文件 | 内容 | 备注 |
| :--- | :--- | :--- |
| [docs/api-contract-w3.md](api-contract-w3.md) | W3 Stats API 增量契约 | ⚠️ 已废弃，当前 API 见 `openapi.json` 或 `/docs` |
| [docs/ui-spec.md](ui-spec.md) | 页面线框与布局规范 | W1-W2 时期 |
| [docs/components.md](components.md) | 组件 Props 与样式规范 | W1-W2 时期 |
| [docs/demo-video-script-final.md](demo-video-script-final.md) | 演示视频脚本 | 最终版 |
| [docs/recording-guide.md](recording-guide.md) | 录屏指南（macOS） | |

## 设计一致性

- **颜色与间距**：只使用 `frontend/src/styles/tokens.css` 中的 CSS 变量，禁止硬编码颜色
- **API 字段**：以 `docs/openapi.json` / `/docs` 为单一事实源；CI gate (`.github/workflows/openapi-sync.yml`) 阻止漂移
- **测试基线**：Backend 197 passed · Frontend 40 passed · Alembic head: 0009
