# 测试拆分收尾审计报告

## 1. 审计结论

- 原大测试文件拆分已达到阶段目标：`backend/tests/test_course_plan_pages.py` 已从拆分前约 2555 行降至 168 行，原先混杂在其中的 route 测试已按功能拆到独立文件。
- `test_course_plan_pages.py` 当前已不再是大文件。它现在主要承担共享测试 helper / fixture 承载，以及一个安全边界测试。
- 当前测试基线稳定：`pytest --collect-only` 仍收集 157 个测试，完整 pytest 仍为 157 passed。
- `test_outlines_routes.py` 当前为 1015 行，已经成为新的最大测试文件，具备二级拆分价值。但不建议在收尾阶段立刻大规模拆 `conftest.py` 或修改 fixture。若产品节奏更重要，可以先进入 Phase 2 中文错误提示与异常处理统一；若继续测试治理，建议只对 `test_outlines_routes.py` 做一轮小范围二级拆分。

## 2. 当前测试文件规模

本轮统计命令：

```text
find backend/tests -name "test*.py" -print0 | xargs -0 wc -l | sort -n
```

当前测试文件行数：

| 测试文件 | 行数 | 判断 |
| --- | ---: | --- |
| `backend/tests/test_prompt_boundary_docs.py` | 17 | 小 |
| `backend/tests/test_demo_fallback.py` | 21 | 小 |
| `backend/tests/test_courses_routes.py` | 25 | 小 |
| `backend/tests/test_lesson_draft_structure.py` | 66 | 小 |
| `backend/tests/test_lesson_drafts_ui.py` | 66 | 小 |
| `backend/tests/test_lessons_routes.py` | 106 | 小 / 中等 |
| `backend/tests/test_exports_routes.py` | 124 | 小 / 中等 |
| `backend/tests/test_chaoxing_export_from_ai_probe.py` | 130 | 小 / 中等 |
| `backend/tests/test_courses_v2_ui.py` | 132 | 小 / 中等 |
| `backend/tests/test_course_plan_parser.py` | 133 | 小 / 中等 |
| `backend/tests/test_deepseek_timeout_and_material_budget.py` | 136 | 小 / 中等 |
| `backend/tests/test_lesson_materials_xlsx.py` | 143 | 小 / 中等 |
| `backend/tests/test_lesson_draft_task_packs.py` | 153 | 中等 |
| `backend/tests/test_course_plan_import_service.py` | 164 | 中等 |
| `backend/tests/test_course_plan_models.py` | 167 | 中等 |
| `backend/tests/test_course_plan_pages.py` | 168 | 已收口 |
| `backend/tests/test_lesson_draft_generation_isolation.py` | 182 | 中等 |
| `backend/tests/test_course_management.py` | 199 | 中等 |
| `backend/tests/test_lesson_draft_ai_generation.py` | 203 | 中等 |
| `backend/tests/test_drafts_routes.py` | 215 | 中等 |
| `backend/tests/test_course_plans_routes.py` | 227 | 中等 |
| `backend/tests/test_diagnostic_probe_v2_ui.py` | 240 | 中等偏大 |
| `backend/tests/test_teaching_prep_reference_suggestions.py` | 263 | 中等偏大 |
| `backend/tests/test_learning_guides_v2_ui.py` | 273 | 中等偏大 |
| `backend/tests/test_ai_settings_routes.py` | 303 | 中等偏大 |
| `backend/tests/test_lesson_materials_outline_v2_ui.py` | 414 | 较大 |
| `backend/tests/test_materials_routes.py` | 503 | 较大 |
| `backend/tests/test_outlines_routes.py` | 1015 | 当前最大文件 |

测试文件总计 5788 行。重点变化是 `test_course_plan_pages.py` 已不再是主要大文件；当前主要规模压力转移到 `test_outlines_routes.py`。

## 3. 已拆分测试模块

- `test_ai_settings_routes.py`：AI 设置、会话级 API Key、模型选择、safe next、same-origin、session key store 和 API Key 不入库。
- `test_courses_routes.py`：课程入口 / legacy 课程页面可访问。
- `test_course_plans_routes.py`：授课计划上传、V2 return_to、上传解析、预览、确认生成正式课次和跳过未选课次。
- `test_lessons_routes.py`：正式课次列表、V2 资料整理入口、课次详情。
- `test_materials_routes.py`：课次资料提交、粘贴文本、docx / pptx / 多文件上传、不支持格式提示、资料删除。
- `test_outlines_routes.py`：知识主干生成、查看、保存、DeepSeek / mock provider、fallback、prompt 边界、模型配置和 HTTP error 边界。
- `test_drafts_routes.py`：草稿列表、默认草稿生成、课前学情测试、基础导学案、巩固提升 / 拓展探究任务包、草稿保存和 upsert。
- `test_exports_routes.py`：学习通 xlsx 导出、导出页下载入口、目录 fallback、Markdown 下载和导出文件写入。

## 4. test_course_plan_pages.py 当前剩余内容

本轮指定命令 `grep -n "^def test_" backend/tests/test_course_plan_pages.py || true` 无输出，因为剩余测试是异步测试。补充检查显示当前剩余测试函数为：

- `test_no_sql_python_c_grading_demo_routes_added`

当前共享 helper / fixture：

- `anyio_backend`
- `inline_threadpool_for_tests`
- `_build_test_client`
- `_create_course`
- `_database_contains_text`
- `_upload_sample_plan`
- `_create_first_lesson`
- `_create_reviewed_outline`

当前常量：

- `PROJECT_ROOT`
- `SAMPLE_PLAN`
- `SAME_ORIGIN_HEADERS`

建议暂时保留 `test_course_plan_pages.py` 作为共享 helper / fixture 承载文件，原因是多个已拆分 route 测试仍从它 import 测试客户端、课程创建、授课计划上传、正式课次创建和已审阅知识主干准备逻辑。

不建议马上抽 `conftest.py`。抽取全局 fixture 会同时影响 `ai_settings`、`course_plans`、`materials`、`outlines`、`drafts`、`exports` 等多组测试，失败面更大。若后续整理，应单独安排一轮 shared helper / fixture 专项，并在前后对比 157 collected / 157 passed。

## 5. test_outlines_routes.py 二级拆分判断

`test_outlines_routes.py` 当前 1015 行，包含 21 个测试函数，是当前最大测试文件。它混合了以下职责：

- route 页面 / 保存测试：课次详情中的知识主干入口、知识主干页面查看、教师保存 reviewed 内容、页面生成提示和脚本禁用。
- DeepSeek provider / fallback：无 API Key 本地结构化草稿、DeepSeek provider 成功调用、生成失败不保存、无效 provider 安全错误、flash 模型选择、mock provider 生成。
- prompt 边界 / 安全过滤：行政信息过滤、敏感材料过滤、固定章节和声明、材料长度限制、材料优先级。
- 模型配置 / timeout / HTTP error：`DEEPSEEK_ALLOWED_MODELS`、`DEEPSEEK_DEFAULT_MODEL`、`AI_REQUEST_TIMEOUT_SECONDS`、`AI_PROMPT_MATERIAL_MAX_CHARS`、`httpx.Client` timeout 和 HTTP error 分支。

建议继续拆，但不必在当前收尾轮立刻执行。若继续拆，推荐结构：

- `test_outlines_routes.py`：保留真正的知识主干 route 页面、生成 route、保存 route 和回跳相关测试。
- `test_outlines_provider_fallback.py`：迁移 DeepSeek / mock provider、fallback、生成失败和无效 provider 行为测试。
- `test_outlines_prompt_boundaries.py`：迁移 prompt 固定章节、声明、材料长度、敏感信息过滤、行政信息过滤相关测试。
- `test_outlines_model_config.py`：迁移模型白名单、默认模型、timeout fallback、HTTP error 和 `httpx.Client` monkeypatch 测试。

推荐第一刀：优先拆出模型配置 / timeout / HTTP error 和纯 prompt 边界类同步测试。理由是这组测试较少依赖数据库、ASGI client 和 route helper，迁移风险低；但仍必须保护 monkeypatch 环境变量和 `httpx.Client` 替换语义。

## 6. 风险与注意事项

- 不建议立刻大规模抽 `conftest.py`。当前共享 helper 依赖面广，过早抽取容易让多个 route 测试同时失败。
- 不建议修改业务代码来适配测试拆分。测试拆分目标是保持覆盖等价，不是修功能或改行为。
- 不建议删除或弱化断言。重复断言可能覆盖 legacy / V2 入口、return_to、安全边界、响应头或文件名边界。
- 后续二级拆分必须保持 `157 collected / 157 passed`，如果数量变化需要先说明并经确认。
- 继续拆 `test_outlines_routes.py` 时要保护 `monkeypatch`、`AI_PROVIDER`、`DEEPSEEK_ALLOWED_MODELS`、`AI_REQUEST_TIMEOUT_SECONDS`、`AI_PROMPT_MATERIAL_MAX_CHARS`、`httpx.Client`、`main.ai_provider.generate_knowledge_outline_with_provider` 等测试语义。
- 不要把学生端、自动批阅、学习通 API 直连、教师能力评价等暂缓功能混入测试拆分。
- 上传 / 导出目录覆盖、`dependency_overrides.clear()`、`client.aclose()` 和临时 SQLite 数据库语义仍需保持不变。

## 7. 下一阶段建议

1. 若继续测试治理，先做一轮 `test_outlines_routes.py` 二级拆分，第一刀拆模型配置 / timeout / HTTP error 与 prompt 边界同步测试，避免同时抽 `conftest.py`。
2. 若产品节奏优先，可以先转入 Phase 2 中文错误提示与异常处理统一；当前测试拆分第一阶段已达到目标，基线稳定。
3. `conftest.py` / shared helper 整理建议后置，等 outlines 二级拆分或 Phase 2 稳定后单独安排，不要与业务功能或大批测试移动混做。

## 8. 本轮审计命令记录

- `git status --short --branch`
  - 结果摘要：输出 `## refactor/tests-split`，开始审计时工作区无未提交改动。
- `find backend/tests -name "test*.py" -print0 | xargs -0 wc -l | sort -n`
  - 结果摘要：测试文件总计 5788 行；`test_course_plan_pages.py` 168 行；`test_outlines_routes.py` 1015 行。
- `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`
  - 结果摘要：157 tests collected in 0.78s。
- `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`
  - 结果摘要：157 passed in 33.57s。
- `grep -n "^def test_" backend/tests/test_course_plan_pages.py || true`
  - 结果摘要：无输出；该文件剩余测试为异步测试。
- `grep -n "^async def test_" backend/tests/test_course_plan_pages.py || true`
  - 结果摘要：发现 `test_no_sql_python_c_grading_demo_routes_added`。
- `grep -n "^def _" backend/tests/test_course_plan_pages.py || true`
  - 结果摘要：发现 `_build_test_client`、`_create_course`、`_database_contains_text`、`_create_reviewed_outline`。
- `grep -n "^async def _" backend/tests/test_course_plan_pages.py || true`
  - 结果摘要：发现 `_upload_sample_plan`、`_create_first_lesson`。
- `grep -n "@pytest.fixture" backend/tests/test_course_plan_pages.py || true`
  - 结果摘要：发现 `anyio_backend` 和 `inline_threadpool_for_tests` fixture。
- `ls backend/tests/test_*routes.py`
  - 结果摘要：发现 8 个拆分 route 测试文件：`test_ai_settings_routes.py`、`test_course_plans_routes.py`、`test_courses_routes.py`、`test_drafts_routes.py`、`test_exports_routes.py`、`test_lessons_routes.py`、`test_materials_routes.py`、`test_outlines_routes.py`。
- `grep -n "^\(async \)\?def test_" backend/tests/test_outlines_routes.py`
  - 结果摘要：`test_outlines_routes.py` 当前包含 21 个测试函数。
- `grep -n "monkeypatch\|AI_PROVIDER\|DEEPSEEK_ALLOWED_MODELS\|AI_REQUEST_TIMEOUT_SECONDS\|AI_PROMPT_MATERIAL_MAX_CHARS\|httpx.Client\|generate_knowledge_outline_with_provider" backend/tests/test_outlines_routes.py`
  - 结果摘要：确认 outlines 测试中存在多处 provider、环境变量和 HTTP client monkeypatch，需要在二级拆分时重点保护。
