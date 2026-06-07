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

## 2026-06-07 16:35 +08｜测试文件拆分第三轮：授课计划 route

- 日期时间：2026-06-07 16:35 +08
- 本轮目标：从 `backend/tests/test_course_plan_pages.py` 中拆出授课计划上传、解析预览、确认生成正式课次相关测试到 `backend/tests/test_course_plans_routes.py`，保持测试语义和断言不变。
- 已完成内容：迁移 7 个明确属于 `course_plans` route 范围的测试，覆盖上传页、V2 return_to、安全 return_to、非 xlsx 拒绝、样例 xlsx 上传解析、预览页展示、确认选中课次、跳过未选课次以及正式课次生成；原文件保留 `_upload_sample_plan` 和 `_create_first_lesson` helper，供 lessons、materials、outlines、drafts、exports 相关测试继续准备课次；未移动以正式课次作为前置条件但核心验证其他模块的测试。
- 修改文件：`backend/tests/test_course_plan_pages.py`、`backend/tests/test_course_plans_routes.py`、`docs/worklog.md`。
- 测试结果：拆分前已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`，结果 `157 tests collected in 1.43s`；拆分后已运行同一 collect-only 命令，结果 `157 tests collected in 1.75s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `157 passed in 35.92s`；已运行 `git diff --check`，无输出。
- 未完成 / 待确认：本轮未拆 lessons、materials、outlines、drafts、exports 测试；未抽 `conftest.py`；未修改业务代码、route、模板、数据库模型或测试夹具语义。
- 风险点：`test_course_plans_routes.py` 当前仍通过 `tests.test_course_plan_pages` 复用 `_build_test_client`、`_create_course`、`_upload_sample_plan`、`SAMPLE_PLAN` 和 fixture，这是为了保持本轮最小侵入；后续继续拆 lessons / materials 时需要谨慎处理 helper 依赖，不要同时大改 fixture。
- 下一轮建议：如继续测试拆分专项，建议按功能边界拆 lessons 或 materials 相关 route 测试，继续保持一轮只拆一类测试，并对比 collect-only 数量和完整 pytest 结果。

## 2026-06-07 16:49 +08｜测试文件拆分第四轮：正式课次 route

- 日期时间：2026-06-07 16:49 +08
- 本轮目标：从 `backend/tests/test_course_plan_pages.py` 中拆出正式课次列表、正式课次详情和课次入口相关测试到 `backend/tests/test_lessons_routes.py`，保持测试语义和断言不变。
- 已完成内容：迁移 3 个明确属于 lessons route 范围的测试，覆盖 `GET /courses/{course_id}/lessons` 正式课次列表、列表中的 V2 课次入口链接、`GET /lessons/{lesson_id}` 课次详情页；保留核心验证资料上传、知识主干、草稿、任务包和导出下载的测试在原文件中。
- 修改文件：`backend/tests/test_course_plan_pages.py`、`backend/tests/test_lessons_routes.py`、`docs/worklog.md`。
- 测试结果：拆分前已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`，结果 `157 tests collected in 1.43s`；拆分后已运行同一 collect-only 命令，结果 `157 tests collected in 1.73s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `157 passed in 35.92s`；已运行 `git diff --check`，无输出。
- 未完成 / 待确认：本轮只找到 3 个可明确移动的 lessons 测试；未移动虽然访问 `/lessons/{lesson_id}` 但核心验证 materials、outlines、drafts 或 exports 的测试；未抽 `conftest.py`；未修改业务代码、route、模板、数据库模型或测试夹具语义。
- 风险点：`test_lessons_routes.py` 当前仍通过 `tests.test_course_plan_pages` 复用 `_build_test_client`、`_create_course`、`_upload_sample_plan` 和 fixture，这是为了保持本轮最小侵入；后续拆 materials / outlines 时仍需谨慎处理共享 helper，不要同时大改 fixture。
- 下一轮建议：如继续测试拆分专项，建议拆 materials 相关 route 测试，继续保持一轮只拆一类测试，并对比 collect-only 数量和完整 pytest 结果。

## 2026-06-07 17:04 +08｜测试文件拆分第五轮：课次资料 route

- 日期时间：2026-06-07 17:04 +08
- 本轮目标：从 `backend/tests/test_course_plan_pages.py` 中拆出课次资料页面、资料上传、粘贴文本、多文件上传、资料删除和资料格式边界相关测试到 `backend/tests/test_materials_routes.py`，保持测试语义和断言不变。
- 已完成内容：迁移 11 个明确属于 materials route 范围的测试，覆盖 `POST /lessons/{lesson_id}/materials` 粘贴文本、docx / pptx / txt / md 多文件上传、文件内容提取、默认标题序号、重复行去重、unsupported format 友好提示、`POST /lesson-materials/{material_id}/delete` 删除，以及旧课次详情页中的资料展示和格式支持提示；保留核心验证知识主干、草稿、导学案和导出的测试在原文件中；未修改已有 `test_lesson_materials_outline_v2_ui.py` 和 `test_lesson_materials_xlsx.py`。
- 修改文件：`backend/tests/test_course_plan_pages.py`、`backend/tests/test_materials_routes.py`、`docs/worklog.md`。
- 测试结果：拆分前已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`，结果 `157 tests collected in 1.44s`；拆分后已运行同一 collect-only 命令，结果 `157 tests collected in 1.66s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `157 passed in 33.55s`；已运行 `git diff --check`，无输出。
- 未完成 / 待确认：本轮未拆 outlines、drafts、exports 测试；未抽 `conftest.py`；未修改业务代码、route、模板、数据库模型或测试夹具语义。
- 风险点：`test_materials_routes.py` 当前仍通过 `tests.test_course_plan_pages` 复用 `_build_test_client`、`_create_course`、`_upload_sample_plan` 和 fixture，这是为了保持本轮最小侵入；后续继续拆 outlines / drafts / exports 时仍需谨慎处理共享 helper，避免过早大规模整理 fixture 或改变临时目录、dependency override、monkeypatch 语义。
- 下一轮建议：如继续测试拆分专项，建议拆 outlines / 知识主干相关 route 测试，继续保持一轮只拆一类测试，并对比 collect-only 数量和完整 pytest 结果。

## 2026-06-07 17:27 +08｜测试文件拆分第六轮：知识主干 route

- 日期时间：2026-06-07 17:27 +08
- 本轮目标：从 `backend/tests/test_course_plan_pages.py` 中拆出知识主干生成、查看、保存、DeepSeek / fallback、行政信息过滤、prompt 边界和知识主干入口展示相关测试到 `backend/tests/test_outlines_routes.py`，保持测试语义和断言不变。
- 已完成内容：迁移 21 个明确属于 outlines 范围的测试，覆盖知识主干生成 route、跨站生成拒绝、无 API Key 本地结构化草稿、DeepSeek Provider 调用与模型选择、生成结果行政信息过滤、生成失败不保存且不泄露 Key、无效 Provider 安全错误、mock 知识主干 fallback、知识主干页面查看与教师保存、生成提示与禁用脚本、知识主干 prompt 固定章节 / 声明 / 材料长度限制 / 敏感信息过滤，以及旧课次详情页中的知识主干入口；保留核心验证草稿、导学案和导出的测试在原文件中。
- 修改文件：`backend/tests/test_course_plan_pages.py`、`backend/tests/test_outlines_routes.py`、`docs/worklog.md`。
- 测试结果：拆分前已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`，结果 `157 tests collected in 1.36s`；拆分后已运行同一 collect-only 命令，结果 `157 tests collected in 1.57s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `157 passed in 33.72s`；已运行 `git diff --check`，无输出。
- 未完成 / 待确认：本轮未拆 drafts、exports 测试；未抽 `conftest.py`；未修改业务代码、route、模板、数据库模型或测试夹具语义。
- 风险点：`test_outlines_routes.py` 当前仍通过 `tests.test_course_plan_pages` 复用 `_build_test_client`、`_create_course`、`_upload_sample_plan`、`_database_contains_text`、同源 headers 和 fixture，这是为了保持本轮最小侵入；后续拆 drafts / exports 时仍需谨慎处理共享 helper，避免过早大规模整理 fixture 或改变 dependency override、monkeypatch、临时目录覆盖语义。
- 下一轮建议：如继续测试拆分专项，建议拆 drafts / 草稿、前测、导学案相关 route 测试，继续保持一轮只拆一类测试，并对比 collect-only 数量和完整 pytest 结果。

## 2026-06-07 17:45 +08｜测试文件拆分第七轮：草稿 route

- 日期时间：2026-06-07 17:45 +08
- 本轮目标：从 `backend/tests/test_course_plan_pages.py` 中拆出备课参考建议、课前学情测试、学生导学案、草稿列表、草稿生成、草稿保存和任务包相关测试到 `backend/tests/test_drafts_routes.py`，保持测试语义和断言不变。
- 已完成内容：迁移 5 个明确属于 drafts route 范围的测试，覆盖草稿列表需先有已审阅知识主干、默认生成课前学情测试与基础导学案、基础导学案存在后生成巩固提升和拓展探究任务包、教师编辑保存草稿、重复生成时 upsert 当前草稿；保留核心验证学习通导出和 Markdown 下载的测试在原文件中，未移动 exports / 下载相关测试。
- 修改文件：`backend/tests/test_course_plan_pages.py`、`backend/tests/test_drafts_routes.py`、`docs/worklog.md`。
- 测试结果：拆分前已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`，结果 `157 tests collected in 1.41s`；拆分后已运行同一 collect-only 命令，结果 `157 tests collected in 1.42s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `157 passed in 34.46s`；已运行 `git diff --check`，无输出。
- 未完成 / 待确认：本轮未拆 exports / 下载测试；未修改已有 draft / guide 相关测试文件；未抽 `conftest.py`；未修改业务代码、route、模板、数据库模型或测试夹具语义。
- 风险点：`test_drafts_routes.py` 当前仍通过 `tests.test_course_plan_pages` 复用 `_build_test_client`、`_create_course`、`_create_first_lesson`、`_create_reviewed_outline` 和 fixture，这是为了保持本轮最小侵入；其中任务包生成测试包含辅助性的 Markdown 下载响应头断言，但核心验证仍是 drafts / 任务包生成，后续 exports 拆分时应继续把真正导出下载测试留在 exports 范围。
- 下一轮建议：如继续测试拆分专项，建议拆 exports / 学习通导出和 Markdown 下载相关 route 测试，继续保持一轮只拆一类测试，并对比 collect-only 数量和完整 pytest 结果。

## 2026-06-07 18:00 +08｜测试文件拆分第八轮：导出下载 route

- 日期时间：2026-06-07 18:00 +08
- 本轮目标：从 `backend/tests/test_course_plan_pages.py` 中拆出学习通习题文件导出、导出文件下载和 Markdown 下载相关测试到 `backend/tests/test_exports_routes.py`，保持测试语义和断言不变。
- 已完成内容：迁移 3 个明确属于 exports / 下载范围的测试，覆盖课前学情测试草稿导出学习通 xlsx 模板、无课程名称时学习通目录 fallback、基础导学案 Markdown 下载内容与导出文件写入；原文件仅保留 `test_no_sql_python_c_grading_demo_routes_added` 安全边界测试和共享 helper / fixture；未修改已有 `test_chaoxing_export_from_ai_probe.py`。
- 修改文件：`backend/tests/test_course_plan_pages.py`、`backend/tests/test_exports_routes.py`、`docs/worklog.md`。
- 测试结果：拆分前已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`，结果 `157 tests collected in 1.40s`；拆分后已运行同一 collect-only 命令，结果 `157 tests collected in 1.38s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `157 passed in 33.25s`；已运行 `git diff --check`，无输出。
- 未完成 / 待确认：本轮未拆 `test_outlines_routes.py`；未抽 `conftest.py`；未修改业务代码、route、模板、数据库模型或测试夹具语义；未移动核心验证草稿 / 任务包生成但带辅助下载断言的测试。
- 风险点：`test_exports_routes.py` 当前仍通过 `tests.test_course_plan_pages` 复用 `_build_test_client`、`_create_course`、`_create_first_lesson`、`_create_reviewed_outline` 和 fixture，这是为了保持本轮最小侵入；`test_course_plan_pages.py` 仍作为共享 helper 承载文件，后续如要继续收口应单独评估 helper / fixture 迁移，不要与功能测试移动混做。
- 下一轮建议：测试拆分第一阶段已基本完成；建议做一轮测试拆分收尾审计，确认 `test_course_plan_pages.py` 剩余职责、各新测试文件规模、collect-only 数量和完整 pytest 基线。

## 2026-06-07 18:07 +08｜测试拆分收尾审计

- 日期时间：2026-06-07 18:07 +08
- 本轮目标：对测试拆分专项完成状态做收尾审计，生成 `docs/audit/test_suite_split_closing_audit.md`，不修改测试文件或业务代码。
- 已完成内容：执行 Git 状态、测试文件行数统计、pytest collect-only、完整 pytest、`test_course_plan_pages.py` 剩余测试 / helper / fixture 检查、拆分 route 测试文件列表检查和 `test_outlines_routes.py` 二级拆分风险检查；新增审计报告，记录拆分结论、当前测试文件规模、已拆分测试模块、原文件剩余职责、outlines 二级拆分判断、风险和下一阶段建议。
- 修改文件：`docs/audit/test_suite_split_closing_audit.md`、`docs/worklog.md`。
- 测试结果：已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`，结果 `157 tests collected in 0.78s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `157 passed in 33.57s`。
- 未完成 / 待确认：本轮未修改任何 `backend/` 文件、测试文件、模板、静态资源或业务代码；未执行 `test_outlines_routes.py` 二级拆分；未抽 `conftest.py`。
- 风险点：`test_outlines_routes.py` 当前 1015 行，是新的最大测试文件；如继续二级拆分，需要保护 `monkeypatch`、`AI_PROVIDER`、`DEEPSEEK_ALLOWED_MODELS`、`AI_REQUEST_TIMEOUT_SECONDS`、`AI_PROMPT_MATERIAL_MAX_CHARS`、`httpx.Client` 等测试语义，并保持 `157 collected / 157 passed`。
- 下一轮建议：如果继续测试治理，优先小范围拆 `test_outlines_routes.py` 的模型配置 / timeout / HTTP error 和 prompt 边界同步测试；如果产品节奏优先，可先转入 Phase 2 中文错误提示与异常处理统一；`conftest.py` / shared helper 整理建议后置并单独安排。
