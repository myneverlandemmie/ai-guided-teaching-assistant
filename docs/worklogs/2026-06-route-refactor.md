# 2026-06 main.py route 拆分归档

本文件归档“智学导评 V0.2”在 2026-06 期间的 `backend/app/main.py` route 拆分阶段记录。归档范围包括项目手账体系初始化中与 route 拆分相关的交接信息、route 拆分阶段进度汇总、`ai_settings`、`courses`、`course_plans`、`lessons`、`materials`、`outlines`、`drafts`、`exports` 拆分记录，以及 `main.py` route 拆分收尾审计记录。

## 2026-06-03 22:03 +08｜项目手账体系初始化

- 日期时间：2026-06-03 22:03 +08
- 本轮目标：初始化项目总览、工作手账和 QA 检查表，并补充 AGENTS.md 的文档治理规则。
- 已完成内容：新增项目总览、Codex 工作手账、QA 检查表；在 AGENTS.md 中补充每轮施工前阅读文档、施工后追加手账、代码施工轮不得顺手修改其他文档的要求。
- 修改文件：`AGENTS.md`、`docs/project_overview.md`、`docs/worklog.md`、`docs/qa_checklist.md`。
- 测试结果：未运行 pytest，原因：仅文档变更。
- 未完成 / 待确认：生产部署、正式权限体系、正式数据库方案、长期 API Key 加密存储方案待确认。
- 风险点：新文档依据当前仓库和既有文档整理；部分历史文档仍可能保留旧阶段表述，本轮未修改这些文件。
- 下一轮建议：后续代码施工前先阅读本文件最新记录、`docs/project_overview.md` 和 `docs/qa_checklist.md`，再按“一轮只做一件事”继续推进。

## 2026-06-03 22:03 +08｜main.py 路由拆分阶段进度汇总

- 日期时间：2026-06-03 22:03 +08
- 本轮目标：汇总当前 `backend/app/main.py` 路由拆分阶段进度，作为后续拆分交接记录。
- 已完成内容：目前已拆出 `ai_settings`、`courses`、`course_plans`、`lessons`、`materials` 五组 route 文件；最近提交历史显示拆分顺序为 AI settings、courses、course plans、lessons、materials。
- 修改文件：本条为阶段汇总记录；历史拆分涉及 `backend/app/routes/ai_settings.py`、`backend/app/routes/courses.py`、`backend/app/routes/course_plans.py`、`backend/app/routes/lessons.py`、`backend/app/routes/materials.py`。
- 测试结果：历史拆分轮次记录口径为 pytest 均通过；本轮未重新运行 pytest，原因：仅文档变更。
- 未完成 / 待确认：后续待拆 `outlines`、`drafts`、`exports`。
- 风险点：`main.py` 中仍有知识主干、草稿生成 / 保存、导出下载相关 route 和辅助函数，拆分时需保持 route path、模板名称、表单字段、redirect 行为不变。
- 下一轮建议：优先选择 `outlines.py`、`drafts.py`、`exports.py` 中的一组作为单轮拆分目标，拆分后运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`。

## 已拆 route 阶段补充

以下五组 route 已在本次 worklog 体系初始化前完成拆分，原活跃手账中的进度汇总记录保留了阶段口径：

- `backend/app/routes/ai_settings.py`：AI 设置、保存、清除相关 route。
- `backend/app/routes/courses.py`：根入口、课程列表、V2 课程中心、课程创建、重命名、删除相关 route。
- `backend/app/routes/course_plans.py`：授课计划上传、上传结果预览、确认生成正式课次相关 route。
- `backend/app/routes/lessons.py`：课程下正式课次列表、正式课次详情相关 route。
- `backend/app/routes/materials.py`：课程资料整理 V2、课次资料提交、课次资料删除相关 route。

## 2026-06-04 11:27 +08｜main.py 知识主干 route 拆分

- 日期时间：2026-06-04 11:27 +08
- 本轮目标：把知识主干生成、查看、保存 3 个 route 从 `backend/app/main.py` 拆到 `backend/app/routes/outlines.py`，保持 path、模板、表单字段、redirect 和 DeepSeek / fallback 行为不变。
- 已完成内容：新增 `create_outlines_router`，迁移 `POST /lessons/{lesson_id}/knowledge-outline/generate`、`GET /lessons/{lesson_id}/knowledge-outline`、`POST /knowledge-outlines/{outline_id}/save`；`main.py` 仅新增 outlines router 注册并删除已迁移重复 route；保留 `main.ai_provider` 与动态 threadpool 注入以兼容既有测试和运行时依赖。
- 修改文件：`backend/app/main.py`、`backend/app/routes/outlines.py`、`docs/worklog.md`。
- 测试结果：已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `157 passed in 45.44s`。
- 未完成 / 待确认：本轮未拆 drafts、exports；未做人工页面验收。
- 风险点：本轮为 route 搬迁，主要风险在知识主干生成失败时 V2 资料整理页 fallback 上下文、知识主干保存后的 return_to 跳转和既有测试 monkeypatch 依赖；已通过自动化测试覆盖基础行为，但仍建议人工点验关键页面。
- 下一轮建议：按“一轮只迁移一组 route”继续拆 `drafts.py` 或 `exports.py`，不要与 UI、数据库或文档治理混做。

## 2026-06-04 12:05 +08｜main.py 草稿 route 拆分

- 日期时间：2026-06-04 12:05 +08
- 本轮目标：把备课参考建议、课前学情测试、学生导学案、草稿列表、草稿生成和草稿保存相关 route 从 `backend/app/main.py` 拆到 `backend/app/routes/drafts.py`，保持 path、模板、表单字段、redirect、fallback 和 upsert 行为不变。
- 已完成内容：新增 `create_drafts_router`，迁移草稿 / 前测 / 导学案相关 7 个 route；保持 `POST /lessons/{lesson_id}/drafts/generate/teaching_prep_reference` 在 `POST /lessons/{lesson_id}/drafts/generate/{draft_type}` 之前注册；`main.py` 仅新增 drafts router 注册并删除已迁移重复 route；未迁移学习通导出、导出下载、Markdown 下载相关 route。
- 修改文件：`backend/app/main.py`、`backend/app/routes/drafts.py`、`docs/worklog.md`。
- 测试结果：已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `157 passed in 45.78s`；已运行 `git diff --check`，无输出。
- 未完成 / 待确认：本轮未拆 exports；未做人工页面验收。
- 风险点：本轮为 route 搬迁，主要风险在前测 / 导学案 V2 页面查询参数展示、任务包依赖提示、草稿 fallback 标记、备课参考建议生成和草稿保存 return_to 跳转；已通过自动化测试覆盖基础行为，但仍建议人工点验关键页面。
- 下一轮建议：按“一轮只迁移一组 route”继续拆 `backend/app/routes/exports.py`，只迁移学习通导出、导出下载和 Markdown 下载相关 route。

## 2026-06-04 13:50 +08｜main.py 导出 route 拆分

- 日期时间：2026-06-04 13:50 +08
- 本轮目标：把学习通习题文件导出、导出文件下载和 Markdown 下载相关 route 从 `backend/app/main.py` 拆到 `backend/app/routes/exports.py`，保持 path、目录语义、文件名校验、响应头、media_type、redirect 和错误处理不变。
- 已完成内容：新增 `create_exports_router`，迁移 `POST /lessons/{lesson_id}/drafts/{draft_id}/export-chaoxing`、`GET /exports/chaoxing/{filename}`、`GET /lessons/{lesson_id}/drafts/{draft_id}/download-md`；`main.py` 仅新增 exports router 注册并删除已迁移重复 route；导出目录通过 lambda 注入以保持运行时目录覆盖行为不变。
- 修改文件：`backend/app/main.py`、`backend/app/routes/exports.py`、`docs/worklog.md`。
- 测试结果：已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `157 passed in 43.22s`；已运行 `git diff --check`，无输出。
- 未完成 / 待确认：未做人工页面验收；`backend/app/main.py` 中仍保留多组 route 共用 helper 和常量，后续是否进一步整理需单独安排。
- 风险点：本轮为 route 搬迁，主要风险在学习通 xlsx 导出文件写入目录、非法文件名拒绝、下载响应头和 Markdown 下载文件名；已通过自动化测试覆盖基础行为，但仍建议人工点验下载链路。
- 下一轮建议：如继续重构，可单独评估 `backend/app/main.py` 中剩余公共 helper / 常量是否需要归并，但不要与功能变更混做。

## 2026-06-04 15:02 +08｜main.py 路由拆分收尾审计

- 日期时间：2026-06-04 15:02 +08
- 本轮目标：对 `backend/app/main.py` 路由拆分完成状态做收尾审计，生成审计报告，不修改业务代码。
- 已完成内容：执行 Git 状态、文件行数、`@app.*` route 装饰器、`include_router` 注册、routes 目录列表和 `main.py` 当前职责检查；新增 `docs/audit/main_py_route_refactor_closing_audit.md`，记录拆分结论、文件规模、已拆模块、剩余职责、helper / 常量建议分类、风险和下一阶段建议。
- 修改文件：`docs/audit/main_py_route_refactor_closing_audit.md`、`docs/worklog.md`。
- 测试结果：未运行 pytest，原因：本轮仅文档审计，未修改业务代码、模板、测试或依赖配置。
- 未完成 / 待确认：未做人工页面验收；审计报告中的 helper / 常量迁移仅为建议，未执行代码移动。
- 风险点：`main.py` 虽无 `@app.*` route 装饰器，但仍保留多组公共 helper 和常量；后续若继续整理，应单独安排并用测试和人工验收保护导出、fallback、upsert 等关键行为。
- 下一轮建议：先进入下一阶段产品化改进，优先做中文错误提示与异常处理统一；如做代码整理，避免与 UI、数据库、测试或功能变更混做。
