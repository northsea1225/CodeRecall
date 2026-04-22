# CodeRecall W1 -> W2 Handoff

## W1 里程碑清单

- ✅ 骨架：前端路由、布局、Dashboard / Mistakes / Review / Stats / ImportExport 页面已连通
- ✅ CRUD：错题列表、创建、编辑、删除与分类/标签基础联调已打通
- ✅ 导入导出：`/api/v1/export`、`/api/v1/import` 已接入前后端
- ✅ Monaco 最小接入：`MistakeEditor` 双栏代码输入已从 `TextArea` 切到 Monaco
- ✅ UI 规范：当前实现已对齐 `docs/ui-spec.md`、`docs/components.md` 的 W1 范围

## W2 入口指引

### 搜索从哪里接

- 当前搜索入口在 `frontend/src/pages/MistakeList/index.tsx`
- 状态入口在 `frontend/src/stores/mistakeStore.ts` 的 `filters.keyword`
- 现状：UI 已有输入框，但 `fetchList()` 还没有把 `keyword` 传给 `frontend/src/services/mistakeService.ts`
- W2 建议顺序：
  1. 后端先在 `backend/app/api/routes/mistakes.py` 和对应 service/repository 增加 `keyword` 查询
  2. 前端再把 `filters.keyword` 接到 `listMistakes()` 请求参数
  3. 最后补分页、空态、搜索联动 smoke

### Review 流程页在哪里

- 占位页在 `frontend/src/pages/Review/index.tsx`
- 当前只有 W1 空态文案和路由占位，没有真实出题、作答、比对、自评逻辑

### `review_service` 应该放哪

- 后端服务建议新增到 `backend/app/services/review_service.py`
- 对应 API 路由建议放在 `backend/app/api/routes/review.py`
- 如果 W2 要做前端请求封装，新增 `frontend/src/services/reviewService.ts`

## 已知可能阻碍 W2 的点

- 导入接口运行时返回的 `skipped` 是数组，`docs/api-contract-w1.md` 里写的是计数字段；W2 若继续复用导入结果展示，需要优先统一契约
- Monaco 目前是最小直连接入，没有做懒加载、主题、worker 配置；功能可用，但首包体积会继续偏大
- Mistake 搜索框只有 UI，没有后端筛选能力，W2 做搜索时不要误以为仅补前端即可

## Key Files Quick Ref

### 后端路由

- `backend/app/main.py`
- `backend/app/api/routes/mistakes.py`
- `backend/app/api/routes/categories.py`
- `backend/app/api/routes/tags.py`
- `backend/app/api/routes/import_export.py`

### 前端 service

- `frontend/src/services/api.ts`
- `frontend/src/services/mistakeService.ts`
- `frontend/src/services/taxonomyService.ts`
- `frontend/src/services/importExportService.ts`

### 前端 stores

- `frontend/src/stores/mistakeStore.ts`
- `frontend/src/stores/draftStore.ts`
- `frontend/src/stores/uiStore.ts`

### 前端页面 / 组件

- `frontend/src/pages/MistakeEditor/index.tsx`
- `frontend/src/pages/MistakeList/index.tsx`
- `frontend/src/pages/ImportExport/index.tsx`
- `frontend/src/pages/Review/index.tsx`
- `frontend/src/components/common/CodeEditor/index.tsx`
