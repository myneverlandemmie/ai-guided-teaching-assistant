# main.py Refactor Audit / main.py 拆分审计报告

## 1. 执行摘要

当前 `backend/app/main.py` 约 1492 行，已经明显超过单一入口文件的理想体量。它同时承担应用初始化、AI 设置、课程管理、课程计划上传、正式课次、课次资料、知识主干、备课参考建议、课前学情测试、学生导学案、文件导出下载和若干辅助函数。

结论：`main.py` 后续有必要拆分，但不建议在案例提交前进行大重构。当前更稳妥的策略是先保持 route path 和业务语义不变，形成拆分计划；等 V2 演示材料和测试基线稳定后，再按低风险模块逐步迁移。

## 2. main.py 当前职责概览

`main.py` 当前包含以下职责：

- FastAPI app 创建、静态文件和模板挂载；
- 数据库会话依赖、启动初始化和 demo 数据兜底；
- same-origin 校验、文件名处理、导出目录处理等辅助逻辑；
- AI settings 页面、API Key 会话保存和模型选择；
- 课程管理和 V2 课程中心；
- 课程计划上传、解析预览、确认生成正式课次；
- 正式课次列表、课次详情和 V2 课次页面；
- 课次资料上传、文本提取、资料删除；
- 知识主干生成、查看、编辑保存；
- LessonDraft 生成、保存、按类型分组展示；
- 备课参考建议生成；
- 课前学情测试 V2 与学习通习题文件导出；
- 学生导学案 V2 与 Markdown 下载；
- 文件下载路由。

## 3. 当前 route 分组

### 课程管理

- `GET /`
- `GET /courses`
- `GET /ui-v2/courses`
- `POST /courses/create`
- `POST /courses/{course_id}/rename`
- `POST /courses/{course_id}/delete`

### 授课计划上传

- `GET /courses/{course_id}/course-plan/upload`
- `POST /courses/{course_id}/course-plan/upload`
- `GET /course-plan-uploads/{upload_id}`
- `POST /course-plan-uploads/{upload_id}/confirm`

### 正式课次

- `GET /courses/{course_id}/lessons`
- `GET /lessons/{lesson_id}`

### 课次资料

- `GET /ui-v2/lessons/{lesson_id}/materials-outline`
- `POST /lessons/{lesson_id}/materials`
- `POST /lesson-materials/{material_id}/delete`

### 知识主干

- `POST /lessons/{lesson_id}/knowledge-outline/generate`
- `GET /lessons/{lesson_id}/knowledge-outline`
- `POST /knowledge-outlines/{outline_id}/save`

### 备课参考建议

- `POST /lessons/{lesson_id}/drafts/generate/teaching_prep_reference`

### 课前学情测试

- `GET /ui-v2/lessons/{lesson_id}/diagnostic-probe`
- `POST /lessons/{lesson_id}/drafts/generate`
- `POST /lessons/{lesson_id}/drafts/generate/{draft_type}`
- `POST /lessons/{lesson_id}/drafts/{draft_id}/save`
- `POST /lessons/{lesson_id}/drafts/{draft_id}/export-chaoxing`

### 学生导学案

- `GET /ui-v2/lessons/{lesson_id}/learning-guides`
- `GET /lessons/{lesson_id}/drafts`
- `POST /lessons/{lesson_id}/drafts/generate/{draft_type}`
- `POST /lessons/{lesson_id}/drafts/{draft_id}/save`
- `GET /lessons/{lesson_id}/drafts/{draft_id}/download-md`

### AI 设置

- `GET /ai/settings`
- `POST /ai/settings`
- `POST /ai/settings/clear`

### 文件下载/导出

- `GET /exports/chaoxing/{filename}`
- `GET /lessons/{lesson_id}/drafts/{draft_id}/download-md`

## 4. main.py 膨胀风险

- route 与业务编排混在一起，后续新增页面容易继续堆叠；
- 课程、课次、资料、草稿、导出等不同职责共享同一个文件，局部修改时上下文成本高；
- 文件较长，review 时难以快速定位影响范围；
- V2 页面与 legacy 页面共存，若继续集中在 `main.py`，容易误改兼容入口；
- 下载导出、AI 生成、表单保存都在同一文件，后续安全边界审查不够清晰；
- 测试失败时较难按模块判断责任归属。

## 5. 建议拆分目标

拆分目标不是改变业务，而是降低维护成本：

- route path 保持不变；
- 模板名称和表单字段保持不变；
- 数据库模型和存储语义保持不变；
- 服务层逻辑优先复用现有 `services/*`；
- 每次只迁移一组低耦合 route；
- 迁移后立即运行 pytest。

## 6. 推荐目录结构

建议逐步形成：

```text
backend/app/routes/
├── __init__.py
├── courses.py
├── course_plans.py
├── lessons.py
├── materials.py
├── outlines.py
├── drafts.py
├── ai_settings.py
└── exports.py

backend/app/services/
├── course_management_service.py
├── teaching_prep_reference_service.py
├── course_plan/
├── lesson_materials/
├── ai/
└── exports/
```

可选拆分：

- `backend/app/routes/v2_courses.py`：如果希望 V2 页面和 legacy route 分开；
- `backend/app/utils/security.py`：same-origin 校验；
- `backend/app/utils/files.py`：文件名、路径和下载响应辅助函数；
- `backend/app/services/exports/chaoxing.py`：学习通习题文件导出封装；
- `backend/app/services/exports/markdown.py`：Markdown 下载内容封装。

## 7. 建议拆分顺序

1. 先拆低风险 route：
   - `ai_settings.py`
   - `courses.py`
   - `course_plans.py`

2. 再拆页面编排 route：
   - `lessons.py`
   - `materials.py`
   - `outlines.py`

3. 再拆 AI 草稿 route：
   - `drafts.py`
   - 保持 `LessonDraft` upsert、fallback 和生成语义不变。

4. 最后拆下载导出：
   - `exports.py`
   - 保持文件路径、文件名校验和响应头行为不变。

## 8. 风险控制

- 每拆一组 route 后运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`；
- 保留所有 route path 不变；
- 不改数据库结构；
- 不改 `LessonDraft` 存储模型；
- 不改 DeepSeek Provider；
- 不改 AI settings 保存逻辑；
- 不改 `session_key_store`；
- 不改 fallback / upsert 核心逻辑；
- 不改课程计划解析逻辑；
- 不改 xlsx 资料提取逻辑；
- 不同时移动模板；
- 遇到 legacy 页面引用时，先保留兼容入口。

## 9. 不建议现在做的事

- 不建议在案例提交前大重构；
- 不建议同时改 UI 和 route 结构；
- 不建议移动旧 UI 模板；
- 不建议把所有业务逻辑一次性抽到 service；
- 不建议在拆分 route 的同时新增学生端、登录权限、作业批阅或学习通 API；
- 不建议改变现有测试夹具和演示数据语义。

## 10. 后续重构验收标准

一次拆分可接受的验收标准：

- pytest 全量通过；
- V2 课程中心仍可打开；
- 正式课次列表仍可作为 V2 过渡入口；
- 课程资料整理 V2、课前学情测试 V2、学生导学案 V2 route 不变；
- 旧页面 route 仍可访问或按测试要求保留；
- 学习通习题文件导出仍可下载；
- Markdown 下载仍可下载；
- API Key 设置、清除和模型选择行为不变；
- 无数据库迁移；
- `git diff` 显示为 route 拆分和 import 调整，不混入新业务功能。
