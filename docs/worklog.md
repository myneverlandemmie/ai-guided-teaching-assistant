# Codex 工作手账

本文件为当前活跃工作手账，只保留当前状态、历史归档链接和最近记录。历史完整记录见 `docs/worklogs/`。

## 当前状态摘要

- `main.py` route 拆分已完成。
- 原 `test_course_plan_pages.py` 大测试文件拆分已完成。
- `outlines` 测试二级拆分已完成。
- 当前建议进入 Phase 2：中文错误提示与异常处理统一；或按需继续进行测试共享 helper / `conftest.py` 专项审计。
- 远程 GitHub 是否 push：待用户确认。

## 历史归档

- [2026-06 main.py route 拆分记录](worklogs/2026-06-route-refactor.md)
- [2026-06 测试拆分记录](worklogs/2026-06-test-split.md)

## 最近记录

### 2026-06-07 18:07 +08｜测试拆分收尾审计

- 日期时间：2026-06-07 18:07 +08
- 本轮目标：对测试拆分专项完成状态做收尾审计，生成 `docs/audit/test_suite_split_closing_audit.md`，不修改测试文件或业务代码。
- 已完成内容：执行 Git 状态、测试文件行数统计、pytest collect-only、完整 pytest、`test_course_plan_pages.py` 剩余测试 / helper / fixture 检查、拆分 route 测试文件列表检查和 `test_outlines_routes.py` 二级拆分风险检查；新增审计报告，记录拆分结论、当前测试文件规模、已拆分测试模块、原文件剩余职责、outlines 二级拆分判断、风险和下一阶段建议。
- 修改文件：`docs/audit/test_suite_split_closing_audit.md`、`docs/worklog.md`。
- 测试结果：已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`，结果 `157 tests collected in 0.78s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `157 passed in 33.57s`。
- 未完成 / 待确认：本轮未修改任何 `backend/` 文件、测试文件、模板、静态资源或业务代码；未执行 `test_outlines_routes.py` 二级拆分；未抽 `conftest.py`。
- 风险点：`test_outlines_routes.py` 当前 1015 行，是新的最大测试文件；如继续二级拆分，需要保护 `monkeypatch`、`AI_PROVIDER`、`DEEPSEEK_ALLOWED_MODELS`、`AI_REQUEST_TIMEOUT_SECONDS`、`AI_PROMPT_MATERIAL_MAX_CHARS`、`httpx.Client` 等测试语义，并保持 `157 collected / 157 passed`。
- 下一轮建议：如果继续测试治理，优先小范围拆 `test_outlines_routes.py` 的模型配置 / timeout / HTTP error 和 prompt 边界同步测试；如果产品节奏优先，可先转入 Phase 2 中文错误提示与异常处理统一；`conftest.py` / shared helper 整理建议后置并单独安排。

### 2026-06-07 18:42 +08｜outlines 测试二级拆分第三轮：provider 与 fallback

- 日期时间：2026-06-07 18:42 +08
- 本轮目标：从 `backend/tests/test_outlines_routes.py` 中拆出 DeepSeek provider 调用、mock fallback、本地结构化草稿、生成失败安全处理和模型选择生成路径相关测试到 `backend/tests/test_outlines_provider_fallback.py`，保持测试语义和断言不变。
- 已完成内容：迁移 9 个明确属于 provider / fallback / 生成集成范围的测试；新文件仅复制必要 import；保留 route 页面 / 查看 / 保存、cross-origin route 安全、prompt 边界 / 安全过滤、模型配置 / timeout / HTTP error 测试在原有文件或已拆文件中。
- 修改文件：`backend/tests/test_outlines_routes.py`、`backend/tests/test_outlines_provider_fallback.py`、`docs/worklog.md`。
- 测试结果：拆分前已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`，结果 `157 tests collected in 1.54s`；拆分后已运行同一 collect-only 命令，结果 `157 tests collected in 1.56s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `157 passed in 35.90s`；已运行 `git diff --check`，无输出。
- 未完成 / 待确认：本轮未拆 route 页面 / 查看 / 保存测试，未拆 cross-origin route 安全测试，未抽 `conftest.py`，未修改业务代码、route、模板、数据库模型或测试夹具语义。
- 风险点：`test_outlines_provider_fallback.py` 仍依赖 `AI_PROVIDER`、`main.ai_provider.generate_knowledge_outline_with_provider`、session API Key 设置、`dependency_overrides.clear()`、临时 SQLite 数据库和 `_database_contains_text` 语义；后续如整理共享 helper 需单独拆轮并保持 `157 collected / 157 passed`。
- 下一轮建议：`test_outlines_routes.py` 可保留为最终 route 页面 / 查看 / 保存和 cross-origin 安全覆盖文件；建议先做 outlines 二级拆分收口审计，确认文件规模和覆盖边界。

### 2026-06-07 19:39 +08｜worklog 归档整理

- 日期时间：2026-06-07 19:39 +08
- 本轮目标：将已完成的 main.py route 拆分、测试拆分和 outlines 测试二级拆分历史记录归档到 `docs/worklogs/`，并让 `docs/worklog.md` 回到“当前阶段索引 + 最近状态”的轻量形式。
- 已完成内容：新增 route 拆分归档和测试拆分归档；`docs/worklog.md` 改为当前状态摘要、历史归档链接和最近记录；`AGENTS.md` 小幅补充活跃手账与归档手账的读取规则。
- 修改文件：`AGENTS.md`、`docs/worklog.md`、`docs/worklogs/2026-06-route-refactor.md`、`docs/worklogs/2026-06-test-split.md`。
- 测试结果：未运行 pytest，原因：本轮仅文档归档，未修改代码、测试、模板、静态资源、数据库或依赖配置。
- 未完成 / 待确认：远程 GitHub 是否 push 仍待用户确认；未做人工链接点击验收。
- 风险点：原活跃手账末尾的“outlines 二级拆分完成”仅为一句收尾标记，无单独测试结果或修改文件，本轮按原样语义归档，未补写不存在的细节。
- 下一轮建议：进入 Phase 2 中文错误提示与异常处理统一；如继续测试治理，单独做共享 helper / `conftest.py` 专项审计。

### 2026-06-07 20:03 +08｜测试共享 helper 显式复用整理

- 日期时间：2026-06-07 20:03 +08
- 本轮目标：将 `backend/tests/test_course_plan_pages.py` 中剩余共享 helper、fixture 和常量迁移到显式复用模块 `backend/tests/support/course_plan_helpers.py`，并将剩余真实测试迁移到独立测试文件，保持测试语义和 157 collected / 157 passed 基线不变。
- 已完成内容：新增 `backend/tests/support/` 支持模块；迁移 `PROJECT_ROOT`、`SAMPLE_PLAN`、`SAME_ORIGIN_HEADERS`、`anyio_backend`、`inline_threadpool_for_tests`、`_build_test_client`、`_create_course`、`_database_contains_text`、`_upload_sample_plan`、`_create_first_lesson`、`_create_reviewed_outline`；将 `test_no_sql_python_c_grading_demo_routes_added` 迁移到 `backend/tests/test_grading_demo_routes.py`；更新 9 个测试文件的 helper import，从 `tests.test_course_plan_pages` 改为 `tests.support.course_plan_helpers`；删除已无必要内容的 `backend/tests/test_course_plan_pages.py`。
- 修改文件：`backend/tests/support/__init__.py`、`backend/tests/support/course_plan_helpers.py`、`backend/tests/test_grading_demo_routes.py`、`backend/tests/test_ai_settings_routes.py`、`backend/tests/test_course_plans_routes.py`、`backend/tests/test_courses_routes.py`、`backend/tests/test_drafts_routes.py`、`backend/tests/test_exports_routes.py`、`backend/tests/test_lessons_routes.py`、`backend/tests/test_materials_routes.py`、`backend/tests/test_outlines_provider_fallback.py`、`backend/tests/test_outlines_routes.py`、`backend/tests/test_course_plan_pages.py`、`docs/worklog.md`。
- 测试结果：拆分前已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`，结果 `157 tests collected in 1.43s`；拆分后已运行同一 collect-only 命令，结果 `157 tests collected in 1.63s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `157 passed in 33.86s`；已运行 `git diff --check`，无输出。
- 未完成 / 待确认：本轮未抽 `conftest.py`；未修改业务代码、route、模板、数据库模型、断言、fixture 作用域、monkeypatch 语义或 dependency override 语义；未做人工页面验收。
- 风险点：`PROJECT_ROOT` 在新 helper 模块中需从 `parents[3]` 计算仓库根目录，以保持 `SAMPLE_PLAN` 指向原数据文件；后续如移动 helper 文件路径，需要同步确认该路径计算。
- 下一轮建议：如继续测试治理，可单独审计是否还有局部 `_build_test_client` 重复实现；产品节奏优先时进入 Phase 2 中文错误提示与异常处理统一。

### 2026-06-07 20:25 +08｜Phase 2 错误提示与异常处理统一：只读审计

- 日期时间：2026-06-07 20:25 +08
- 本轮目标：启动 Phase 2 中文友好错误提示与异常处理统一，先做第一轮只读审计，明确当前错误提示、fallback、上传、return_to、导出下载和日志隐私边界现状，不进入施工。
- 已完成内容：阅读 `docs/project_overview.md`、`docs/worklog.md` 当前状态和 `docs/qa_checklist.md`；检查 `backend/app/main.py`、相关 route、service、template、static 范围；搜索 `HTTPException`、`raise`、`except`、`return_to`、`message`、`error`、`DeepSeek`、`fallback`、上传格式和导出下载路径；生成 `docs/audit/phase2_error_handling_audit.md`。
- 修改文件：`docs/audit/phase2_error_handling_audit.md`、`docs/worklog.md`。
- 测试结果：已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `157 passed in 32.00s`。
- 未完成 / 待确认：本轮未修改业务代码、测试文件、模板、静态资源、README、数据库、上传文件或导出文件；下一步等待用户审阅审计报告后再决定 Phase 2.1 施工范围。
- 风险点：当前审计判断指出上传文件大小、知识主干 DeepSeek 失败 fallback、备课建议 fallback 提示、非法 `return_to` 教师提示和导出下载失败提示需要后续小步施工验证；本轮未验证人工页面流程。
- 下一轮建议：优先从 Phase 2.1 上传格式与文件大小提示开始，先解决 P0 上传格式文案统一、P1 文件过大和 V2 上传错误回到 V2 页面的问题。
