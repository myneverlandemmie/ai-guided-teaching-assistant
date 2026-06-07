# 2026-06 测试拆分归档

本文件归档“智学导评 V0.2”在 2026-06 期间的测试拆分与 outlines 测试二级拆分阶段记录。归档范围包括测试文件拆分审计，`ai_settings`、`courses`、`course_plans`、`lessons`、`materials`、`outlines`、`drafts`、`exports` 测试拆分记录，测试拆分收尾审计，outlines 测试二级拆分记录，以及“outlines 二级拆分完成”收尾记录。

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

## 2026-06-07 18:26 +08｜outlines 测试二级拆分第一轮：prompt 边界

- 日期时间：2026-06-07 18:26 +08
- 本轮目标：从 `backend/tests/test_outlines_routes.py` 中拆出 prompt 边界、行政信息过滤、敏感材料过滤、固定章节和材料长度限制相关测试到 `backend/tests/test_outlines_prompt_boundaries.py`，保持测试语义和断言不变。
- 已完成内容：迁移 4 个明确属于 prompt 边界 / 安全过滤范围的测试：`test_sanitizer_covers_common_administrative_variants`、`test_deepseek_prompt_filters_sensitive_material_information`、`test_knowledge_outline_prompt_contains_fixed_sections_and_disclaimers`、`test_deepseek_prompt_prioritizes_key_material_and_limits_length`；新文件仅复制必要 import；保留 DeepSeek provider / fallback、route 页面 / 保存、模型配置、timeout 和 HTTP error 测试在 `test_outlines_routes.py`。
- 修改文件：`backend/tests/test_outlines_routes.py`、`backend/tests/test_outlines_prompt_boundaries.py`、`docs/worklog.md`。
- 测试结果：拆分前已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`，结果 `157 tests collected in 1.52s`；拆分后已运行同一 collect-only 命令，结果 `157 tests collected in 0.95s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `157 passed in 35.91s`；已运行 `git diff --check`，无输出。
- 未完成 / 待确认：本轮未拆 DeepSeek provider / fallback 测试，未拆 route 页面 / 保存测试，未拆模型配置 / timeout / HTTP error 测试，未抽 `conftest.py`，未修改业务代码、route、模板、数据库模型或测试夹具语义。
- 风险点：`test_outlines_prompt_boundaries.py` 包含 `AI_PROMPT_MATERIAL_MAX_CHARS` monkeypatch 测试，后续继续拆模型配置或 provider 测试时仍需保护环境变量 monkeypatch 和 `httpx.Client` 替换语义；`test_outlines_routes.py` 当前仍有 fallback 中的敏感信息过滤测试，因其核心属于 mock fallback 行为，本轮按边界要求保留未动。
- 下一轮建议：如继续 outlines 二级拆分，建议拆模型配置 / timeout / HTTP error 相关同步测试到独立文件，继续保持一轮只拆一类测试，并对比 collect-only 数量和完整 pytest 结果。

## 2026-06-07 18:33 +08｜outlines 测试二级拆分第二轮：模型配置与错误边界

- 日期时间：2026-06-07 18:33 +08
- 本轮目标：从 `backend/tests/test_outlines_routes.py` 中拆出 DeepSeek 模型配置、允许模型列表、默认模型、timeout fallback 和 HTTP error 边界相关测试到 `backend/tests/test_outlines_model_config.py`，保持测试语义和断言不变。
- 已完成内容：迁移 4 个明确属于模型配置 / timeout / HTTP error 范围的测试：`test_deepseek_model_config_parses_allowed_models`、`test_deepseek_model_config_falls_back_when_env_is_invalid`、`test_deepseek_config_accepts_v4_models_and_invalid_timeout_falls_back`、`test_deepseek_http_errors_do_not_keep_exception_chain_or_key`；新文件仅复制必要 import；保留 route 页面 / 保存、DeepSeek provider、mock fallback 和 prompt 边界测试在原有文件中。
- 修改文件：`backend/tests/test_outlines_routes.py`、`backend/tests/test_outlines_model_config.py`、`docs/worklog.md`。
- 测试结果：拆分前已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`，结果 `157 tests collected in 1.50s`；拆分后已运行同一 collect-only 命令，结果 `157 tests collected in 0.83s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `157 passed in 36.17s`；已运行 `git diff --check`，无输出。
- 未完成 / 待确认：本轮未拆 route 页面 / 保存测试，未拆 DeepSeek provider / fallback 测试，未拆 prompt 边界 / 安全过滤测试，未抽 `conftest.py`，未修改业务代码、route、模板、数据库模型或测试夹具语义。
- 风险点：`test_outlines_model_config.py` 仍依赖环境变量 monkeypatch 和 `app.services.ai.deepseek_client.httpx.Client` 替换语义；后续继续拆 provider / fallback 测试时需要保护 `AI_PROVIDER`、`main.ai_provider.generate_knowledge_outline_with_provider`、`dependency_overrides.clear()` 和临时数据库语义。
- 下一轮建议：如继续 outlines 二级拆分，建议拆 DeepSeek provider / mock fallback 相关测试到独立文件；route 页面 / 保存测试可继续留在 `test_outlines_routes.py` 作为最终 route 覆盖文件。

## 2026-06-07 18:42 +08｜outlines 测试二级拆分第三轮：provider 与 fallback

- 日期时间：2026-06-07 18:42 +08
- 本轮目标：从 `backend/tests/test_outlines_routes.py` 中拆出 DeepSeek provider 调用、mock fallback、本地结构化草稿、生成失败安全处理和模型选择生成路径相关测试到 `backend/tests/test_outlines_provider_fallback.py`，保持测试语义和断言不变。
- 已完成内容：迁移 9 个明确属于 provider / fallback / 生成集成范围的测试：`test_deepseek_generation_without_api_key_uses_local_structured_draft`、`test_deepseek_generation_uses_provider_and_saves_outline`、`test_generated_outline_is_sanitized_before_saving`、`test_deepseek_generation_error_does_not_save_outline_or_expose_key`、`test_invalid_ai_provider_shows_safe_error_without_outline`、`test_deepseek_generation_uses_flash_selected_model`、`test_can_generate_mock_knowledge_outline_without_materials`、`test_mock_knowledge_outline_uses_lesson_material_keywords`、`test_mock_knowledge_outline_filters_sensitive_material_information`；新文件仅复制必要 import；保留 route 页面 / 查看 / 保存、cross-origin route 安全、prompt 边界 / 安全过滤、模型配置 / timeout / HTTP error 测试在原有文件或已拆文件中。
- 修改文件：`backend/tests/test_outlines_routes.py`、`backend/tests/test_outlines_provider_fallback.py`、`docs/worklog.md`。
- 测试结果：拆分前已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`，结果 `157 tests collected in 1.54s`；拆分后已运行同一 collect-only 命令，结果 `157 tests collected in 1.56s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `157 passed in 35.90s`；已运行 `git diff --check`，无输出。
- 未完成 / 待确认：本轮未拆 route 页面 / 查看 / 保存测试，未拆 cross-origin route 安全测试，未拆 prompt 边界 / 安全过滤测试，未拆模型配置 / timeout / HTTP error 测试，未抽 `conftest.py`，未修改业务代码、route、模板、数据库模型或测试夹具语义。
- 风险点：`test_outlines_provider_fallback.py` 仍依赖 `AI_PROVIDER`、`main.ai_provider.generate_knowledge_outline_with_provider`、session API Key 设置、`dependency_overrides.clear()`、临时 SQLite 数据库和 `_database_contains_text` 语义；本轮只做原样移动，后续如整理共享 helper 需单独拆轮并保持 `157 collected / 157 passed`。
- 下一轮建议：如继续 outlines 二级拆分，`test_outlines_routes.py` 可保留为最终 route 页面 / 查看 / 保存和 cross-origin 安全覆盖文件；建议先做 outlines 二级拆分收口审计，确认文件规模和覆盖边界。

## outlines 二级拆分完成

- 原活跃手账末尾记录：`outlines 二级拆分完成`。
- 归档说明：该记录作为 outlines 测试二级拆分完成的收尾标记保留；原记录未包含单独的日期时间、测试结果或修改文件，本归档不补写未记录的细节。
