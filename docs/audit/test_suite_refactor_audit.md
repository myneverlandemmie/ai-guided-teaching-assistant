# 测试文件拆分审计报告

## 1. 审计结论

- 当前测试套件存在明确的大文件问题，集中体现在 `backend/tests/test_course_plan_pages.py`：2555 行、63 个测试函数，约占测试代码总行数 45.2%。
- 不建议现在立刻大规模拆测试。测试拆分比 route 拆分更容易在“测试仍通过”的情况下弱化覆盖，因此应先审计、确认目标结构，再按功能分轮拆分。
- 当前 `main.py` route 拆分刚完成，pytest 基线为 157 个测试全部通过。建议优先保留这个基线，先进入 Phase 2 功能改进；如要拆测试，应单独开测试拆分专项，一轮只拆一类测试。

## 2. 当前测试文件规模

本轮使用实际目录 `backend/tests` 统计。当前共有 20 个 `test*.py` 文件，总计 5657 行。

| 测试文件 | 行数 | 测试函数数 | 规模判断 |
| --- | ---: | ---: | --- |
| `backend/tests/test_course_plan_pages.py` | 2555 | 63 | 严重大文件 |
| `backend/tests/test_lesson_materials_outline_v2_ui.py` | 414 | 11 | 大文件 |
| `backend/tests/test_learning_guides_v2_ui.py` | 273 | 6 | 中等偏大 |
| `backend/tests/test_teaching_prep_reference_suggestions.py` | 263 | 6 | 中等偏大 |
| `backend/tests/test_diagnostic_probe_v2_ui.py` | 240 | 4 | 中等偏大 |
| `backend/tests/test_lesson_draft_ai_generation.py` | 203 | 6 | 中等 |
| `backend/tests/test_course_management.py` | 199 | 6 | 中等 |
| `backend/tests/test_lesson_draft_generation_isolation.py` | 182 | 4 | 中等 |
| `backend/tests/test_course_plan_models.py` | 167 | 7 | 中等 |
| `backend/tests/test_course_plan_import_service.py` | 164 | 6 | 中等 |
| `backend/tests/test_lesson_draft_task_packs.py` | 153 | 6 | 中等 |
| `backend/tests/test_lesson_materials_xlsx.py` | 143 | 2 | 小 / 中等 |
| `backend/tests/test_deepseek_timeout_and_material_budget.py` | 136 | 6 | 小 / 中等 |
| `backend/tests/test_course_plan_parser.py` | 133 | 11 | 小 / 中等 |
| `backend/tests/test_courses_v2_ui.py` | 132 | 3 | 小 / 中等 |
| `backend/tests/test_chaoxing_export_from_ai_probe.py` | 130 | 2 | 小 / 中等 |
| `backend/tests/test_lesson_draft_structure.py` | 66 | 2 | 小 |
| `backend/tests/test_lesson_drafts_ui.py` | 66 | 4 | 小 |
| `backend/tests/test_demo_fallback.py` | 21 | 1 | 小 |
| `backend/tests/test_prompt_boundary_docs.py` | 17 | 1 | 小 |

主要拆分压力来自 `test_course_plan_pages.py`。`test_lesson_materials_outline_v2_ui.py` 也可作为后续第二批整理对象，但不应和第一轮同时拆。

## 3. 当前测试数量与收集情况

- `grep -R "^def test_" backend/tests | wc -l`：66 个同步测试函数。
- `grep -R "^async def test_" backend/tests | wc -l`：91 个异步测试函数。
- `pytest --collect-only -q`：157 tests collected in 1.22s。
- 完整 pytest：已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `157 passed in 28.03s`。

本轮 collect-only 数量和完整 pytest 结果与当前基线一致，未发现测试收集缺口。

## 4. 测试覆盖功能分组

- `ai_settings`
  - 主要在 `test_course_plan_pages.py`：`/ai/settings` 页面、保存、清除、safe next、same-origin、无效模型、无效 session cookie、API Key 不入库。
  - 同文件还覆盖 `session_key_store` 过期、容量和非法环境变量。
- `courses`
  - `test_course_management.py`：课程创建、重命名、删除、级联删除。
  - `test_courses_v2_ui.py`：`/ui-v2/courses` 入口、V2 创建课程、legacy 页面不变。
  - `test_course_plan_pages.py` 中也有 `/courses` 入口和课程相关链路测试。
- `course_plans`
  - `test_course_plan_pages.py`：授课计划上传页、上传、预览、确认 / 跳过、return_to。
  - `test_course_plan_parser.py`：Excel 解析和课程编码 / 标题解析。
  - `test_course_plan_import_service.py`：导入服务、确认正式课次、失败状态。
  - `test_course_plan_models.py`：数据库表、课程、上传记录、计划课次和正式课次模型。
- `lessons`
  - `test_course_plan_pages.py`：正式课次列表、课次详情。
  - `test_lesson_materials_outline_v2_ui.py`、`test_diagnostic_probe_v2_ui.py`、`test_learning_guides_v2_ui.py`：课次入口链接到 V2 页面。
- `materials`
  - `test_course_plan_pages.py`：粘贴文本、docx、pptx、多文件、删除、不支持格式提示、页面不泄露绝对路径。
  - `test_lesson_materials_outline_v2_ui.py`：资料整理 V2 页面、return_to、删除后回跳、legacy 页面不变。
  - `test_lesson_materials_xlsx.py`：xlsx 提取和 xls 友好拒绝。
- `outlines`
  - `test_course_plan_pages.py`：知识主干生成、DeepSeek / mock provider、sanitizer、错误不泄露 Key、保存 reviewed。
  - `test_lesson_materials_outline_v2_ui.py`：V2 页面展示 outline 编辑器、保存 / 生成后回跳。
  - `test_demo_fallback.py`、`test_deepseek_timeout_and_material_budget.py`：本地结构化草稿、prompt 限长和 DeepSeek 超时配置。
- `drafts`
  - `test_course_plan_pages.py`：legacy 草稿页、diagnostic probe、guide_low / mid / high、upsert 和编辑保存。
  - `test_diagnostic_probe_v2_ui.py`：课前学情测试 V2 页面、生成、保存、导出回跳。
  - `test_learning_guides_v2_ui.py`：学生导学案 V2、任务包依赖、return_to。
  - `test_lesson_draft_generation_isolation.py`：单类草稿生成不污染其他类型。
  - `test_lesson_draft_ai_generation.py`、`test_lesson_draft_task_packs.py`、`test_lesson_draft_structure.py`、`test_lesson_drafts_ui.py`：AI / fallback 生成结构、任务包文案、模板状态 target。
  - `test_teaching_prep_reference_suggestions.py`：备课参考建议生成、显示、保存、Markdown 下载。
- `exports`
  - `test_course_plan_pages.py`：学习通 xlsx 导出、Markdown 下载。
  - `test_diagnostic_probe_v2_ui.py`：V2 前测页导出 return_to。
  - `test_chaoxing_export_from_ai_probe.py`：AI 前测题解析后导出行非空。
  - `test_teaching_prep_reference_suggestions.py`：备课参考建议 Markdown 下载友好文件名。
  - `test_lesson_drafts_ui.py`：下载文件名不暴露内部 tier。
- 其他公共 fixture / 数据库 / 安全边界
  - 多个 UI route 文件内存在 `_build_test_client(tmp_path)`，通过 SQLite 临时库、`main.app.dependency_overrides[main.get_db]` 和 `httpx.ASGITransport` 构造测试客户端。
  - `test_course_plan_pages.py` 集中覆盖 safe redirect、same-origin、session cookie、API Key 不入库、敏感材料过滤。

## 5. 高风险测试依赖

- `fixture`
  - 多个文件各自定义 `anyio_backend`、`_build_test_client` 或本地数据构造 helper。
  - `test_course_plan_pages.py` 中的 `_upload_sample_plan`、`_create_first_lesson`、`_database_contains_text` 等 helper 被多个测试依赖。
- `monkeypatch`
  - 用于环境变量：`AI_PROVIDER`、`AI_SESSION_KEY_*`、`DEEPSEEK_*`、prompt 材料长度限制等。
  - 用于替换 `main.run_in_threadpool`，避免真实线程和外部请求。
  - 用于替换 `main.ai_provider.generate_knowledge_outline_with_provider`、DeepSeek / lesson draft HTTP client 和 AI 调用函数。
- `dependency_overrides`
  - 多个测试文件通过 `main.app.dependency_overrides[main.get_db] = override_get_db` 替换数据库依赖。
  - 拆分时必须确保每个测试结束后仍清理 `main.app.dependency_overrides.clear()`。
- `tmp_path`
  - 大量测试使用临时 SQLite 数据库、上传文件、docx / pptx / xlsx 文件和导出文件路径。
  - 拆分时不能改动临时目录语义，否则可能污染本地 `app.db` 或运行产物目录。
- 上传 / 导出目录覆盖
  - `test_course_plan_pages.py` 覆盖 `main.COURSE_PLAN_UPLOAD_DIR`、`main.LESSON_MATERIAL_UPLOAD_DIR`、`main.CHAOXING_EXPORT_DIR`、`main.GUIDE_EXPORT_DIR`。
  - `test_teaching_prep_reference_suggestions.py` 覆盖 `main.GUIDE_EXPORT_DIR`。
  - `test_lesson_materials_xlsx.py` 覆盖 `main.LESSON_MATERIAL_UPLOAD_DIR`。
- API Key / session / fallback
  - `test_course_plan_pages.py` 覆盖 session key store 过期和容量、AI 设置保存 / 清除、API Key 不入库、不回显、跨站提交拒绝。
  - 多个草稿和知识主干测试依赖本地 structured draft / fallback 不改变行为。
- 其他拆分时不能破坏的依赖
  - same-origin headers、safe return_to、下载响应头、文件名校验、V2 页面 return_to、`LessonDraft` upsert、任务包依赖提示。
  - `grep` 本轮也命中 `backend/tests/__pycache__` 的 binary file matches；这些是测试运行产物，不应在拆分审计轮删除或作为测试源文件处理。

## 6. 推荐拆分目标结构

建议后续测试目录仍使用 `backend/tests`，可以逐步演进到：

- `backend/tests/conftest.py`
  - 仅在确认一类 fixture 稳定后再抽；不要第一轮就把所有 `_build_test_client` 都合并。
- `backend/tests/test_ai_settings_routes.py`
- `backend/tests/test_courses_routes.py`
- `backend/tests/test_course_plans_routes.py`
- `backend/tests/test_lessons_routes.py`
- `backend/tests/test_materials_routes.py`
- `backend/tests/test_outlines_routes.py`
- `backend/tests/test_drafts_routes.py`
- `backend/tests/test_exports_routes.py`
- `backend/tests/test_session_key_store.py`
- `backend/tests/test_prompt_and_ai_boundaries.py`

现有 service / parser 类测试可以保留或小幅调整命名：

- `test_course_plan_parser.py`
- `test_course_plan_import_service.py`
- `test_course_plan_models.py`
- `test_lesson_draft_ai_generation.py`
- `test_deepseek_timeout_and_material_budget.py`

## 7. 推荐拆分顺序

- 一轮只拆一类测试。
- 不修改业务代码。
- 不删除测试。
- 不弱化断言。
- 不改变测试夹具语义。
- 不改变 monkeypatch、dependency override、tmp_path 目录覆盖语义。
- 每轮拆分后先运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`，确认测试数量不减少。
- 每轮拆分后再运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，确认完整测试通过。
- 如果测试数量减少，必须明确原因并经用户确认，不能把减少视为默认可接受。

建议顺序：

1. 从 `test_course_plan_pages.py` 中拆 `ai_settings` / session 相关测试。
2. 拆 `course_plans` 上传 / 预览 / 确认相关 route 测试。
3. 拆 `materials` 上传 / 提取 / 删除相关 route 测试。
4. 拆 `outlines` 知识主干生成 / 保存相关 route 测试。
5. 拆 `drafts` 草稿生成 / 保存 / upsert 相关 route 测试。
6. 拆 `exports` 学习通导出 / Markdown 下载相关 route 测试。
7. 评估是否需要整理 V2 UI 专项测试和 parser / service 单元测试命名。

## 8. 第一轮测试拆分建议

最适合第一刀的是从 `backend/tests/test_course_plan_pages.py` 中拆出 `ai_settings` / session 相关测试，目标文件建议为 `backend/tests/test_ai_settings_routes.py`，另可在后续单独考虑 `backend/tests/test_session_key_store.py`。

理由：

- 该范围 endpoint 清晰，主要集中在 `/ai/settings`、`/ai/settings/clear`、session cookie、safe next 和 same-origin。
- 这组测试与课程计划上传、材料解析、知识主干、草稿生成、导出下载的业务链路相对独立。
- 拆出后能明显减少最大文件的复杂度，同时为后续 route-by-route 拆分建立模板。

注意：

- 第一轮不要同时抽全局 `conftest.py`。
- 可以先保持局部 `_build_test_client` 语义不变；如必须共享 helper，应只抽最小必要 fixture，并确保 collect-only 数量仍为 157。
- 不要顺手删除看似重复的 AI 设置测试，因为这些测试覆盖了安全边界和 API Key 不泄露行为。

## 9. 风险与注意事项

- 测试拆分比 `main.py` route 拆分更容易“看起来没坏但实际覆盖变弱”，尤其是断言被移动时遗漏页面文本、响应头、redirect 或数据库断言。
- 不建议 Codex 自动删除重复测试。重复可能是为了覆盖不同入口、legacy / V2 页面、return_to 或安全边界。
- 不建议同时拆 fixture 和大量测试函数。fixture 变动会影响多个测试文件，定位失败原因更困难。
- 不建议在测试拆分轮修改业务代码。拆分目标是保持覆盖等价，不是修功能。
- 拆分前后应对比 pytest collect-only 数量和完整 pytest 结果。
- 拆分时要保护 `dependency_overrides.clear()`、`client.aclose()`、临时目录覆盖和 monkeypatch 恢复。
- 上传 / 导出相关测试不能改为真实运行目录，避免污染上传文件、导出文件或本地数据库。
- 不应把学生端、自动批阅、学习通 API 直连等暂缓功能混入测试拆分。

## 10. 本轮审计命令记录

- `git status --short --branch`
  - 结果摘要：输出 `## refactor/main-routes`；开始审计时工作区无未提交改动。
- `find backend -path "*/tests/*" -name "test*.py" -print`
  - 结果摘要：发现 20 个测试文件，实际测试目录为 `backend/tests`。
- `find backend -path "*/tests/*" -name "test*.py" -exec wc -l {} +`
  - 结果摘要：测试文件总计 5657 行；最大文件 `test_course_plan_pages.py` 为 2555 行。
- `grep -R "^def test_" backend/tests || true`
  - 结果摘要：发现同步测试函数；补充计数命令结果为 66 个。
- `grep -R "^async def test_" backend/tests || true`
  - 结果摘要：发现异步测试函数；补充计数命令结果为 91 个。
- `grep -E -c "^(async )?def test_" backend/tests/test*.py`
  - 结果摘要：按文件统计测试函数数量；`test_course_plan_pages.py` 63 个最多。
- `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`
  - 结果摘要：157 tests collected in 1.22s。
- `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`
  - 结果摘要：157 passed in 28.03s。
- `grep -R "monkeypatch" backend/tests || true`
  - 结果摘要：命中 DeepSeek、session、threadpool、provider 和环境变量相关测试；也命中 `__pycache__` binary file matches。
- `grep -R "dependency_overrides" backend/tests || true`
  - 结果摘要：多个 UI route 测试通过 `main.app.dependency_overrides[main.get_db]` 替换数据库依赖，并在结束时 clear。
- `grep -R "tmp_path" backend/tests || true`
  - 结果摘要：大量测试使用临时数据库、上传文件和导出目录。
- `grep -R "client" backend/tests || true`
  - 结果摘要：大量 route 测试使用 httpx ASGI client。
- `grep -R "CHAOXING_EXPORT_DIR" backend/tests || true`
  - 结果摘要：`test_course_plan_pages.py` 覆盖学习通导出目录。
- `grep -R "GUIDE_EXPORT_DIR" backend/tests || true`
  - 结果摘要：`test_course_plan_pages.py` 和 `test_teaching_prep_reference_suggestions.py` 覆盖 Markdown 导出目录。
- `grep -R "session_key_store" backend/tests || true`
  - 结果摘要：`test_course_plan_pages.py` 覆盖 session key store。
- `grep -R "ai/settings" backend/tests || true`
  - 结果摘要：`test_course_plan_pages.py` 覆盖 AI 设置 route。
- `grep -R "ui-v2/courses" backend/tests || true`
  - 结果摘要：`test_courses_v2_ui.py` 和 `test_course_plan_pages.py` 覆盖 V2 课程入口。
- `grep -R "course-plan" backend/tests || true`
  - 结果摘要：课程计划 parser、import service、route 页面和上传确认均有覆盖。
- `grep -R "materials-outline" backend/tests || true`
  - 结果摘要：资料整理 V2 页面和 return_to 链路有覆盖。
- `grep -R "knowledge-outline" backend/tests || true`
  - 结果摘要：知识主干生成、保存、V2 回跳和 AI 设置入口有覆盖。
- `grep -R "diagnostic-probe" backend/tests || true`
  - 结果摘要：课前学情测试 V2 页面和入口链接有覆盖。
- `grep -R "learning-guides" backend/tests || true`
  - 结果摘要：学生导学案 V2 页面、入口链接和依赖链路有覆盖。
- `grep -R "export-chaoxing" backend/tests || true`
  - 结果摘要：学习通 xlsx 导出 route 有覆盖。
- `grep -R "download-md" backend/tests || true`
  - 结果摘要：导学案 / 备课参考建议 Markdown 下载 route 有覆盖。

本轮仅新增审计文档和手账记录，未修改测试文件或业务代码。
