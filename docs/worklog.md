# Codex 工作手账

本文件用于记录每轮 Codex 施工的交接信息。代码施工轮追加本文件属于交接记录，不视为同时修改功能文档；除用户明确要求外，不应顺手修改其他文档。

## 记录格式模板

```text
## YYYY-MM-DD HH:MM +08｜本轮标题

- 日期时间：
- 本轮目标：
- 已完成内容：
- 修改文件：
- 测试结果：
- 未完成 / 待确认：
- 风险点：
- 下一轮建议：
```

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

## 2026-06-07 15:55 +08｜测试文件拆分审计

- 日期时间：2026-06-07 15:55 +08
- 本轮目标：对 `backend/tests` 当前测试文件规模、测试数量、收集情况、敏感测试机制和覆盖功能分组做拆分前审计，生成审计报告，不修改测试或业务代码。
- 已完成内容：执行 Git 状态、测试文件发现、测试文件行数统计、测试函数数量统计、pytest collect-only、完整 pytest、敏感测试机制 grep 和主要 route / 功能关键词 grep；新增 `docs/audit/test_suite_refactor_audit.md`，记录测试大文件问题、覆盖分组、高风险依赖、推荐拆分结构、拆分顺序和第一轮拆分建议。
- 修改文件：`docs/audit/test_suite_refactor_audit.md`、`docs/worklog.md`。
- 测试结果：已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`，结果 `157 tests collected in 1.22s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `157 passed in 28.03s`。
- 未完成 / 待确认：本轮未拆分任何测试文件，未修改 fixture、monkeypatch、dependency override 或业务代码；后续是否按建议先拆 `ai_settings` / session 相关测试需人工确认。
- 风险点：`test_course_plan_pages.py` 规模明显偏大，且集中包含 session、API Key、课程计划、导出下载、前测 / 导学案等多类高风险覆盖；拆分时容易出现测试数量不变但断言语义弱化，需逐轮对比 collect-only 数量和完整 pytest 结果。
- 下一轮建议：如进入测试拆分专项，第一轮建议仅从 `test_course_plan_pages.py` 中拆出 `ai_settings` / session 相关测试到独立测试文件，不同时拆 fixture、不修改业务代码、不删除或弱化断言。

## 2026-06-07 16:16 +08｜测试文件拆分第一轮：AI 设置与 session

- 日期时间：2026-06-07 16:16 +08
- 本轮目标：从 `backend/tests/test_course_plan_pages.py` 中拆出 AI 设置、会话级 API Key、模型选择、`session_key_store`、`/ai/settings` 相关测试到 `backend/tests/test_ai_settings_routes.py`，保持测试语义和断言不变。
- 已完成内容：迁移 11 个明确属于 AI 设置 / session 范围的测试；新文件复用原文件的 `_build_test_client`、`_database_contains_text`、同源 headers、`anyio_backend` 和 inline threadpool fixture；原文件保留知识主干、DeepSeek 生成、课程计划、资料、草稿和导出相关测试，未移动非本轮范围测试。
- 修改文件：`backend/tests/test_course_plan_pages.py`、`backend/tests/test_ai_settings_routes.py`、`docs/worklog.md`。
- 测试结果：拆分前已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`，结果 `157 tests collected in 1.44s`；拆分后已运行同一 collect-only 命令，结果 `157 tests collected in 1.75s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `157 passed in 35.79s`；已运行 `git diff --check`，无输出。
- 未完成 / 待确认：本轮未拆 `course_plans`、`materials`、`outlines`、`drafts`、`exports` 测试；未抽 `conftest.py`；未修改业务代码、route、模板、数据库模型或测试夹具语义。
- 风险点：新文件当前通过 `tests.test_course_plan_pages` 复用 helper 和 fixture，这是为了保持本轮最小侵入；后续继续拆分时需谨慎处理这些共享 helper，避免过早大规模整理 fixture 或改变 `dependency_overrides`、monkeypatch、临时目录覆盖语义。
- 下一轮建议：如继续测试拆分专项，建议一轮只拆课程计划上传 / 预览 / 确认相关 route 测试，拆分前后继续对比 collect-only 数量和完整 pytest 结果。

## 2026-06-07 16:25 +08｜测试文件拆分第二轮：课程入口 route

- 日期时间：2026-06-07 16:25 +08
- 本轮目标：从 `backend/tests/test_course_plan_pages.py` 中拆出明确属于课程入口 / 课程管理本身的测试到 `backend/tests/test_courses_routes.py`，保持测试语义和断言不变。
- 已完成内容：定位 `test_course_plan_pages.py` 中 courses 相关命中；仅迁移 `test_courses_page_is_accessible`，因为其他 `/courses/...` 命中核心验证授课计划上传、正式课次、资料、知识主干或导学案链路，不属于本轮 courses / 课程管理本身范围；新文件复用原文件的 `_build_test_client`、`anyio_backend` 和 inline threadpool fixture。
- 修改文件：`backend/tests/test_course_plan_pages.py`、`backend/tests/test_courses_routes.py`、`docs/worklog.md`。
- 测试结果：拆分前已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`，结果 `157 tests collected in 1.42s`；拆分后已运行同一 collect-only 命令，结果 `157 tests collected in 1.05s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `157 passed in 35.84s`；已运行 `git diff --check`，无输出。
- 未完成 / 待确认：本轮未移动 `test_course_management.py` 或 `test_courses_v2_ui.py` 中已有课程创建、重命名、删除、V2 课程中心测试；未拆 `course_plans`、`materials`、`outlines`、`drafts`、`exports` 测试；未抽 `conftest.py`。
- 风险点：`test_courses_routes.py` 当前仍通过 `tests.test_course_plan_pages` 复用测试客户端 helper，这是为了保持最小侵入；后续若继续拆课程计划相关测试，需要谨慎处理 helper 依赖，不要同时大改 fixture。
- 下一轮建议：如继续测试拆分专项，可按审计建议拆课程计划上传 / 预览 / 确认相关 route 测试，继续保持一轮只拆一类测试，并对比 collect-only 数量和完整 pytest 结果。
