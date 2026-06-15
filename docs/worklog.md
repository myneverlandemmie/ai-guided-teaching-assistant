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

### 2026-06-07 20:56 +08｜Phase 2.1a：课次资料上传错误提示收束

- 日期时间：2026-06-07 20:56 +08
- 本轮目标：只处理课次资料上传错误提示收束，保留 `.txt` / `.md` / `.docx` / `.pptx` / `.xlsx` 支持范围，增加课次资料上传大小上限，超限时显示“文件过大，请拆分资料后上传。”，并保证从 V2 资料整理页上传失败时仍停留在 V2 页面。
- 本轮修改范围：`backend/app/routes/materials.py`、`backend/app/templates/lesson_materials_outline_v2.html`、`backend/tests/test_materials_routes.py`、`docs/worklog.md`。
- 已完成内容：在 `materials.py` 中新增 `MAX_LESSON_MATERIAL_UPLOAD_BYTES = 50 * 1024 * 1024`，通过 `seek/tell` 在读取正文前检查课次资料上传大小，无法直接取大小时按 1 MiB 分块检查；超限文件不写入数据库、不保存上传文件；保留 `.xls` 和其他不支持格式的中文细分提示；新增 route 内部错误响应 helper，按现有 V2 `return_to` 渲染 `lesson_materials_outline_v2.html`，legacy 来源继续渲染 `lesson_detail.html`；V2 模板复用 `error_message` 显示错误。
- 新增或调整测试：加强不支持格式测试，断言非 500、支持格式范围和无资料记录；新增超限文件测试，monkeypatch 小上限后确认中文提示、无数据库记录、无失败上传文件；新增 V2 上传失败测试，确认页面仍为 `lesson_materials_outline_v2.html` 且显示课程、课次和错误提示；保留既有 `.txt` / `.md` / `.docx` / `.pptx` / `.xlsx` 成功路径测试。
- 测试结果：施工前已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`，结果 `157 tests collected in 1.31s`；施工前已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `157 passed in 32.32s`；施工后已运行 materials 相关测试 `PYTHONPATH=. ../.venv/bin/pytest -q tests/test_materials_routes.py tests/test_lesson_materials_outline_v2_ui.py tests/test_lesson_materials_xlsx.py`，结果 `26 passed in 10.37s`；施工后已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`，结果 `159 tests collected in 0.71s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `159 passed in 32.81s`；已运行 `git diff --check`，无输出。
- 未完成 / 待确认：本轮未处理授课计划上传大小限制、`.xlsx` 空表文案、AI Key 缺失提示、DeepSeek fallback、备课参考建议 fallback、`return_to` 公共 helper、学习通导出失败或 Markdown 下载失败；未做浏览器人工页面验收；未 commit、未 push。
- 风险点：50 MiB 上限适合普通文本、Word、PPT 和 Excel 教学材料，但实际学校课件若包含大量图片或视频截图，可能需要教师拆分后上传；V2 错误显示仅做最小模板补充，建议人工从 V2 上传 `.pdf` 和超限文件确认页面体验。
- 下一轮建议：Phase 2.1b 单独处理授课计划上传大小限制，继续避免混入 AI fallback、导出下载和公共异常系统。

### 2026-06-07 21:33 +08｜Phase 2.2：课次资料 XLSX 空表提示收束

- 日期时间：2026-06-07 21:33 +08
- 本轮目标：只处理课次资料上传中 `.xlsx` 空表或未读取到有效文本时的中文友好提示，目标文案为“表格内容为空或未读取到有效文本，请检查后重新上传。”。
- 本轮修改范围：`backend/app/services/lesson_materials/document_text_extractor.py`、`backend/tests/test_lesson_materials_xlsx.py`、`docs/worklog.md`。
- 已完成内容：在 `.xlsx` 文本提取服务中新增 `EMPTY_XLSX_TEXT_MESSAGE` 常量，并将没有有效表格文本时的 `LessonMaterialExtractionError` 文案统一为目标文案；保持非空 `.xlsx` 提取、`.txt/.md/.docx/.pptx` 处理、不支持格式提示和 Phase 2.1a 上传大小限制逻辑不变；route 继续捕获 `LessonMaterialExtractionError`、带文件名前缀展示错误并删除失败上传文件。
- 新增或调整测试：在 `test_lesson_materials_xlsx.py` 中新增空 workbook 上传测试、只有空白字符单元格的 `.xlsx` 上传测试，并增强非空 `.xlsx` 成功路径断言，确认非空资料不出现空表提示；空白字符 `.xlsx` 测试同时覆盖 V2 页面错误回显不退回 legacy 页面。
- 测试结果：施工前已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`，结果 `159 tests collected in 1.34s`；施工前已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `159 passed in 33.45s`；施工后已运行 xlsx / materials 相关测试 `PYTHONPATH=. ../.venv/bin/pytest -q tests/test_lesson_materials_xlsx.py tests/test_materials_routes.py tests/test_lesson_materials_outline_v2_ui.py`，结果 `28 passed in 11.03s`；施工后已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`，结果 `161 tests collected in 0.76s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `161 passed in 33.72s`；已运行 `git diff --check`，无输出。
- 未完成 / 待确认：本轮未处理授课计划 `.xlsx` 上传或空表、AI Key 缺失提示、DeepSeek fallback、备课参考建议 fallback、`return_to` 公共 helper、学习通导出失败、Markdown 下载失败、DOCX 下载或 DOCX 导出；未做浏览器人工页面验收；未 commit、未 push。
- 风险点：当前空表判断依赖 openpyxl 读取出的单元格值经 `str(value).strip()` 后是否为空，能覆盖默认空 sheet、全空单元格和空白字符单元格；建议人工从 V2 页面上传空 `.xlsx` 再确认页面体验和提示位置。
- 下一轮建议：按 Phase 2 审计计划继续小步处理，优先在用户确认后进入 AI Key 缺失与 DeepSeek fallback 提示，或单独安排授课计划上传大小限制 Phase 2.1b。

### 2026-06-08 09:06 +08｜Day 12.1：基础版 DOCX 下载 V0

- 日期时间：2026-06-08 09:06 +08
- 本轮目标：为已有导学案 / 备课参考建议草稿增加基础 `.docx` 下载能力，让教师可下载后继续人工编辑；不做完整 DOCX 模板系统、Markdown 完美渲染、批量导出、ZIP 导出或 Pandoc 集成。
- 本轮修改范围：`backend/app/routes/exports.py`、`backend/app/services/exports/__init__.py`、`backend/app/services/exports/docx_exporter.py`、`backend/app/templates/learning_guides_v2.html`、`backend/app/templates/lesson_drafts.html`、`backend/app/templates/lesson_materials_outline_v2.html`、`backend/tests/test_exports_routes.py`、`backend/tests/test_learning_guides_v2_ui.py`、`backend/tests/test_drafts_routes.py`、`backend/tests/test_teaching_prep_reference_suggestions.py`、`docs/worklog.md`。
- 已完成内容：确认项目已有 `python-docx` 依赖并复用；新增基础 DOCX helper，将系统名称、教师草稿声明、课程 / 课次信息、草稿标题和草稿正文写入 Word；在现有 Markdown 下载语义下新增 `/lessons/{lesson_id}/drafts/{draft_id}/download-docx` route，支持 `guide_low`、`guide_mid`、`guide_high` 和 `teaching_prep_reference`；生成 `.docx` 后按现有 guides 导出目录语义落盘一份运行时文件，并返回正确 MIME 类型下载响应；空内容或生成失败返回中文友好提示，不展示 traceback 或服务器路径；在已有 Markdown 下载按钮旁增加“下载 DOCX”入口，草稿内容为空时不显示 DOCX 入口。
- DOCX V0 支持范围：`#` / `##` / `###` 标题、普通段落、`-` / `*` 无序列表、`1.` / `1)` 有序列表；不能识别的 Markdown 行保留为普通段落，尽量不丢正文。
- 未支持的复杂 Markdown 能力：表格完整转换、复杂嵌套列表、代码块高亮、图片、超链接、HTML、脚注和复杂样式。
- 新增或调整测试：新增 DOCX 下载成功测试，使用 `python-docx` 打开响应并断言“学习导航”“知识要点”“传感器”“普通段落内容”等关键文本；新增空内容 DOCX 友好失败测试；增强 Markdown 下载测试，确认 `.md` 响应头和正文不变；更新导学案 V2、legacy 草稿页和备课参考建议页测试，确认已有下载区出现 DOCX 链接；学习通导出测试保持通过。
- 施工前测试结果：已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`，结果 `161 tests collected in 1.54s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `161 passed in 35.00s`。
- 施工后测试结果：已运行导出 / 导学案 / 备课参考相关测试 `PYTHONPATH=. ../.venv/bin/pytest -q tests/test_exports_routes.py tests/test_learning_guides_v2_ui.py tests/test_teaching_prep_reference_suggestions.py tests/test_drafts_routes.py`，结果 `22 passed in 8.77s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`，结果 `163 tests collected in 0.77s`，比施工前新增 2 个测试；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `163 passed in 35.88s`；已运行 `git diff --check`，无输出。
- 未完成 / 待确认：本轮未做 DOCX 模板系统、复杂 Markdown 渲染、批量导出、ZIP 导出、Pandoc / mammoth / pypandoc 集成；未做浏览器人工页面验收；未处理学习通导出失败提示、Markdown 写出失败提示、AI fallback 或上传逻辑；未 commit、未 push。
- 风险点：DOCX V0 为轻量转换，复杂表格、嵌套列表、图片和链接会以普通段落或原始文本方式保留；建议人工在导学案 V2 页、legacy 草稿页和备课参考建议区各点击一次“下载 DOCX”，用 Word / WPS 打开确认排版可接受。
- 下一轮建议：如继续导出能力，可单独做 DOCX 模板样式和更完整 Markdown 转换；如继续 Phase 2，可按审计计划处理导出失败中文提示或 AI fallback 提示。

### 2026-06-08 11:45 +08｜Day 12.1b：DOCX V0 样式与轻量 Markdown 修复

- 日期时间：2026-06-08 11:45 +08
- 本轮目标：修复 Day 12.1 人工验收发现的 DOCX 可读性问题，只处理 DOCX exporter 的字体、标题层级、行内 Markdown 和 fenced code block 基础显示，不扩大导出功能范围。
- 本轮修改范围：`backend/app/services/exports/docx_exporter.py`、`backend/tests/test_exports_routes.py`、`docs/worklog.md`；工作区仍保留 Day 12.1 未提交的 route、模板和相关测试改动，但本轮未继续修改 route URL、按钮、文件名或 MIME 逻辑。
- 已完成内容：在 DOCX exporter 中集中设置 Normal、Title、Heading 1/2/3、List Bullet、List Number 样式的中文 East Asia 字体为 `宋体`，英文字体为 `Times New Roman`；调整文档标题和三级标题字号、加粗、颜色和段前段后间距；新增简单行内 Markdown 解析，闭合的 `**...**` 转成加粗 run，闭合的 `` `...` `` 转成 `Consolas` 等宽 run；新增 fenced code block 处理，忽略语言标记，保留代码块换行，使用 `Consolas` 字体和 `EFEFEF` 浅灰底纹；未闭合代码块按代码块内容保留，避免 500。
- 仍未支持的复杂 Markdown 能力：表格完整转换、复杂嵌套列表、代码块语法高亮、图片、超链接、HTML、脚注、数学公式和复杂样式。
- 新增或调整测试：加强 `test_guide_low_can_download_docx_with_basic_markdown`，测试生成 DOCX 中存在 `w:eastAsia="宋体"`，行内加粗移除 `**` 且对应 run `bold=True`，行内代码移除反引号且使用 `Consolas`，fenced code block 不输出三个反引号和语言标记 `sql`，保留 `SELECT *` / `FROM student` / `WHERE id = 1;`，并在 XML 中检查 `Consolas` 字体和 `EFEFEF` 底纹；保留 DOCX 响应、MIME、文件名和关键文本断言。
- 施工前测试结果：已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `163 passed in 33.10s`。
- 施工后测试结果：已运行 `PYTHONPATH=. ../.venv/bin/pytest -q tests/test_exports_routes.py`，结果 `5 passed in 2.67s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`，结果 `163 tests collected in 0.77s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `163 passed in 32.52s`；已运行 `git diff --check`，无输出。
- 未完成 / 待确认：本轮未引入 Pandoc、pypandoc、mammoth 或系统级依赖；未改 HTML 转 DOCX 链路、DOCX 模板系统、表格完整转换、语法高亮、图片 / 链接 / 脚注 / 数学公式转换；未做人工打开 Word / WPS 验收；未 commit、未 push。
- 风险点：行内 Markdown 解析只处理简单闭合标记，不处理复杂嵌套；代码块为基础等宽浅灰显示，不做语法高亮；建议人工重新下载一份含中文、加粗、行内代码和代码块的 DOCX，用 Word / WPS 确认字体和层级显示符合预期。
- 下一轮建议：如继续 DOCX 能力，可单独做模板化样式和更完整 Markdown 转换；否则可回到 Phase 2 导出失败中文提示或 AI fallback 提示小步施工。

### 2026-06-08 12:16 +08｜Day 12.1c：DOCX V0.1 视觉样式强制落地修复

- 日期时间：2026-06-08 12:16 +08
- 本轮目标：继续修复 DOCX 人工验收发现的视觉落地问题，只处理 DOCX exporter 的字体强制落地、标题样式稳定、保守列表识别和异常 Markdown 标记处理，不扩大导出能力范围。
- 本轮修改范围：`backend/app/services/exports/docx_exporter.py`、`backend/tests/test_exports_routes.py`、`docs/worklog.md`；工作区仍保留 Day 12.1 / Day 12.1b 未提交的 route、模板和相关测试改动，但本轮未修改 route、模板、数据库、AI、上传或依赖配置。
- 已完成内容：将系统标题、课次信息、草稿标题和正文全部改为通过统一 paragraph / run helper 写入，使普通 run 和加粗 run 都直接设置 `Times New Roman` + East Asia `宋体`，不只依赖样式继承；代码 run 继续设置 `Consolas`；列表识别改为只接受行首明确 `- item`、`* item`、`1. item`、`1) item`，避免普通自然段误转 bullet；移除所有样式中的 `w:keepNext` / `w:keepLines`，避免 Word / WPS 显示黑色小方块格式标记；异常行尾孤立反引号会被忽略，文本保留且不抛 500；fenced code block 继续去掉 fence 和语言标记，保留换行、等宽字体和浅灰底色。
- 仍未支持的复杂 Markdown 能力：表格完整转换、复杂嵌套列表、代码块语法高亮、图片、超链接、HTML、脚注、数学公式和复杂样式模板。
- 新增或调整测试：加强 `test_guide_low_can_download_docx_with_basic_markdown`，新增普通自然段“本课学习目标 / 教师确认提示”不使用 List 样式的断言；确认明确无序 / 有序列表仍为 `List Bullet` / `List Number`；确认 `word/document.xml` 也包含 `w:eastAsia="宋体"`，不只是 `styles.xml`；确认 `styles.xml` 和 `document.xml` 均不包含 `w:keepNext` / `w:keepLines`；确认异常行尾反引号不残留且文本不丢失；保留加粗、行内代码、代码块、MIME、文件名和关键文本断言。
- 施工前测试结果：已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `163 passed in 32.39s`。
- 施工后测试结果：已运行 `PYTHONPATH=. ../.venv/bin/pytest -q tests/test_exports_routes.py`，结果 `5 passed in 2.76s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`，结果 `163 tests collected in 0.79s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `163 passed in 32.45s`；已运行 `git diff --check`，无输出。
- 未完成 / 待确认：本轮未引入 Pandoc、pypandoc、mammoth 或系统级依赖；未做 HTML 转 DOCX、复杂 Markdown 解析器、表格完整转换、语法高亮、模板系统、图片 / 链接 / 脚注 / 数学公式转换；未做 Word / WPS 人工打开验收；未 commit、未 push。
- 风险点：行内 Markdown 仍只处理简单闭合标记，复杂嵌套或混合异常标记会以普通文本保留；不同 Word / WPS 版本对字体回退仍可能有差异，建议人工重新下载含中文标题、自然段、列表、加粗、行内代码和代码块的 DOCX 验收。
- 下一轮建议：如视觉仍需提升，可单独做 DOCX 模板样式系统；否则可回到 Phase 2 导出失败中文提示或 AI fallback 提示小步施工。

### 2026-06-08 12:32 +08｜Day 12.1d：DOCX V0.1 文档结构与代码块底纹最终收束

- 日期时间：2026-06-08 12:32 +08
- 本轮目标：收束 DOCX V0.1 的文档结构与代码展示，只处理 exporter 的页眉、正文标题、列表识别、中文标签行、代码块底纹和 standalone SQL 代码段，不扩大功能范围。
- 本轮修改范围：`backend/app/services/exports/docx_exporter.py`、`backend/tests/test_exports_routes.py`、`docs/worklog.md`；工作区仍保留 Day 12.1 / 12.1b / 12.1c 未提交的 route、模板和相关测试改动，但本轮未修改 route、模板、数据库、AI、上传、依赖配置或学习通 / Markdown 下载逻辑。
- 已完成内容：将 `智学导评 V0.2｜AI 输出为教师草稿，需教师审阅确认后使用` 移入页眉，正文不再把系统名作为 Title；正文 Title 改为真实文档标题，如 `0401-光敏传感器数据采集｜全班通用导学案`；保留课次信息正文块；Markdown 标题降级到正文结构层级，`#` / `##` 使用 Heading 2，`###` 使用 Heading 3；列表识别继续保持保守，只接受行首明确 `- item`、`* item`、`1. item`、`1) item`、`(1) item`；中文标签行如“学生要做什么：”“思考提示：”“教师可调整点：”输出为加粗普通段落，不转 bullet；fenced code block 改为单列表格单元格，单元格填充 `EFEFEF` 浅灰底，代码使用 `Consolas` 并保留换行；新增 standalone SQL 行识别，仅对独立成行且以 `SELECT`、`INSERT`、`UPDATE`、`DELETE`、`TRUNCATE`、`CREATE`、`ALTER`、`DROP` 开头的行输出为灰底代码表格。
- 仍未支持的复杂 Markdown 能力：表格完整转换、复杂嵌套列表、代码块语法高亮、图片、超链接、HTML、脚注、数学公式和复杂样式模板。
- 新增或调整测试：加强 `test_guide_low_can_download_docx_with_basic_markdown`，检查页眉包含系统名和 AI 草稿提示；正文 Title 为真实标题且不再把 `智学导评 V0.2` 作为 Title；中文标签行与自然段不使用列表样式；明确 `-` / 数字 / `(1)` 列表仍使用 List 样式；fenced code block 与 standalone SQL 生成表格灰底并使用 `Consolas`；SQL 前置中文说明不误判为代码段；继续覆盖加粗、行内代码、异常反引号、MIME、文件名和关键文本。
- 施工前测试结果：已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `163 passed in 32.47s`。
- 施工后测试结果：已运行 `PYTHONPATH=. ../.venv/bin/pytest -q tests/test_exports_routes.py`，结果 `5 passed in 2.83s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`，结果 `163 tests collected in 0.83s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `163 passed in 32.46s`；已运行 `git diff --check`，无输出。
- 未完成 / 待确认：本轮未引入 Pandoc、pypandoc、mammoth 或系统级依赖；未做 HTML 转 DOCX、完整 Markdown 解析、表格完整转换、语法高亮、图片 / 链接 / 脚注 / 数学公式转换或模板系统；未做 Word / WPS 人工打开验收；未 commit、未 push。
- 风险点：standalone SQL 识别只处理独立成行、以常见 SQL 关键词开头的行；行内 Markdown 仍只支持简单闭合标记；表格灰底在 Word / WPS 中应比段落底纹更稳定，但仍建议人工重新下载含页眉、正文标题、标签行、列表、fenced code block 和 standalone SQL 的 DOCX 验收。
- 下一轮建议：如视觉仍需提高，建议单独进入 DOCX 模板样式系统；若 V0.1 已可接受，可回到 Phase 2 导出失败中文提示或 AI fallback 提示小步施工。

### 2026-06-08 13:24 +08｜Day 12.1d 小修：fenced code block 多语言与行内代码底纹

- 日期时间：2026-06-08 13:24 +08
- 本轮目标：在 Day 12.1d 基础上补充小修，明确通用代码展示以 Markdown fenced code block 为主，standalone SQL 仅作为裸写兼容；同时增强行内代码的视觉区分。
- 本轮修改范围：`backend/app/services/exports/docx_exporter.py`、`backend/tests/test_exports_routes.py`、`docs/worklog.md`；未修改 route、模板、AI、上传、数据库、README、审计文档或依赖配置。
- 已完成内容：fenced code block 继续按 fence 解析，不按语言标记分支，`python` / `c` / `sql` / `markdown` 等语言标记均被忽略且不作为正文输出；代码块内容保留换行、使用 `Consolas`，并继续放入 `EFEFEF` 浅灰底表格单元格；standalone SQL 行识别保留为独立成行 SQL 兼容逻辑，未扩展到 Python / C / Markdown 关键词猜测；行内代码 run 继续保持在原段落内，使用 `Consolas`，并新增 run 级 `EFEFEF` 浅灰底纹，不把整段改为代码块或代码字体。
- 仍未支持的复杂 Markdown 能力：表格完整转换、复杂嵌套列表、代码块语法高亮、图片、超链接、HTML、脚注、数学公式、复杂样式模板、跨行行内代码和反引号嵌套。
- 新增或调整测试：在 `test_guide_low_can_download_docx_with_basic_markdown` 中补充 `python`、`c`、`markdown` fenced code block 样本，断言代码内容保留、语言标记不作为独立正文段落输出、三反引号不残留、代码块仍在灰底表格中；补充行内代码样本 `SELECT * FROM student;`、`print("hello")`、`int main()`，断言反引号移除、代码 run 使用 `Consolas` 且 run XML 存在 `w:fill="EFEFEF"`，同段普通中文说明仍为普通字体；保留 standalone SQL 兼容断言。
- 施工前测试结果：已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `163 passed in 32.67s`。
- 施工后测试结果：已运行 `PYTHONPATH=. ../.venv/bin/pytest -q tests/test_exports_routes.py`，结果 `5 passed in 2.92s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`，结果 `163 tests collected in 0.75s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `163 passed in 32.57s`；已运行 `git diff --check`，无输出。
- 未完成 / 待确认：未引入 Pandoc、pypandoc、mammoth 或系统级依赖；未做 HTML 转 DOCX、完整 Markdown 解析、语法高亮或模板系统；未做 Word / WPS 人工打开验收；未 commit、未 push。
- 风险点：run 级底纹在不同 Word / WPS 版本的显示仍建议人工确认；standalone SQL 仍只识别常见 SQL 关键词开头的独立行，其他裸写语言必须使用 fenced code block 才会被当作代码块。
- 下一轮建议：若视觉验收通过，可停止 DOCX V0.1 小修并进入收尾或提交准备；若仍需进一步控制版式，建议单独进入 DOCX 模板样式系统。

### 2026-06-08 13:41 +08｜Day 12.1e：DOCX 标题去重极小收口

- 日期时间：2026-06-08 13:41 +08
- 本轮目标：在 Day 12.1d 基础上做极小收口，只修正文 DOCX Title 生成逻辑，避免 draft 标题已包含课次编号或课次标题时再次拼接导致重复。
- 本轮修改范围：`backend/app/services/exports/docx_exporter.py`、`backend/tests/test_exports_routes.py`、`docs/worklog.md`；未修改 route、模板、AI、上传、数据库、依赖配置、README 或审计文档。
- 已完成内容：新增 `_build_document_title` 和 `_title_contains_lesson_identity`，当 draft 标题已包含完整课次 label、lesson_code 或 lesson_title 时直接使用 draft 标题；否则仍按 `课次标识｜草稿标题` 生成正文 Title。页眉保持 `智学导评 V0.2｜AI 输出为教师草稿，需教师审阅确认后使用` 不变。
- 新增或调整测试：调整 `test_guide_low_can_download_docx_with_basic_markdown`，将测试 draft 标题设为已包含课次信息的 `0401-光敏传感器数据采集｜全班通用导学案`，断言正文 Title 不生成 `0401-光敏传感器数据采集｜0401-光敏传感器数据采集｜全班通用导学案`。
- 测试结果：已运行 `PYTHONPATH=. ../.venv/bin/pytest -q tests/test_exports_routes.py`，结果 `5 passed in 2.42s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`，结果 `163 tests collected in 0.79s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `163 passed in 32.64s`；已运行 `git diff --check`，无输出。
- 未完成 / 待确认：未做 Word / WPS 人工打开验收；未扩大 Markdown 支持范围；未 commit、未 push。
- 风险点：标题去重以字符串包含关系判断 lesson_code、lesson_title 和完整课次 label，能覆盖当前人工验收发现的重复拼接场景；如后续出现更复杂标题规范，可再单独收束。
- 下一轮建议：人工重新下载已发现重复标题的 DOCX 样例，确认正文 Title 显示为 `课次｜导学案类型` 且不重复。

### 2026-06-08 14:51 +08｜Phase 2.3a：AI fallback reason 与 P0 中文提示统一

- 日期时间：2026-06-08 14:51 +08
- 本轮目标：统一知识主干、课前学情测试 / 学生导学案、备课参考建议在无 DeepSeek API Key 与 DeepSeek 调用失败两类 P0 fallback 场景下的教师可见中文提示，并让知识主干在 DeepSeek 失败时也生成本地结构化草稿。
- 本轮修改范围：`backend/app/services/ai/fallback.py`、`backend/app/services/ai/provider.py`、`backend/app/services/ai/lesson_draft_ai_service.py`、`backend/app/services/teaching_prep_reference_service.py`、`backend/app/routes/outlines.py`、`backend/app/routes/drafts.py`、`backend/app/templates/knowledge_outline.html`、`backend/app/templates/lesson_materials_outline_v2.html`、相关测试文件和 `docs/worklog.md`；未修改 `backend/app/main.py`、上传、导出、数据库、依赖配置、README 或审计文档。
- fallback reason 设计：新增最小 helper `app.services.ai.fallback`，只定义 `missing_api_key`、`provider_error` 两类短 reason，以及两条教师可见文案；导学案和备课参考服务返回兼容旧二元解包的 `FallbackGenerationResult`，同时提供 `fallback_reason` 属性；知识主干 `GeneratedOutline` 增加可选 `fallback_reason`。
- 无 API Key 提示：知识主干、课前学情测试 / 学生导学案、备课参考建议均显示“当前未设置 DeepSeek API Key，已生成本地结构化草稿。”；无 Key 时不触发真实 DeepSeek 调用。
- DeepSeek 调用失败提示：知识主干、课前学情测试 / 学生导学案、备课参考建议均显示“AI 服务暂时不可用，系统已提供本地草稿，可稍后重试。”；不展示底层异常字符串、traceback、API Key、完整 prompt 或上传材料全文。
- 覆盖情况：知识主干 provider 复用本地结构化草稿生成路径，并在 DeepSeek provider error 时保存 `local-structured-draft`；导学案 / 学情测试保留原本地 fallback 与 upsert 语义；备课参考建议生成后通过 redirect query 在 V2 资料整理页显示 fallback 提示；正常 AI 成功路径不追加 fallback reason，不显示 fallback 提示。
- 新增或调整测试：新增 V2 知识主干无 Key 提示、导学案 provider_error 提示、导学案成功无提示、备课参考 provider_error 提示、备课参考成功无提示等 5 个测试；调整知识主干无 Key、知识主干 DeepSeek 失败、导学案无 Key、备课参考无 Key和服务层 reason 断言。
- 施工前测试结果：已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`，结果 `163 tests collected in 1.25s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `163 passed in 32.90s`。
- 施工后测试结果：已运行受影响测试集 `PYTHONPATH=. ../.venv/bin/pytest -q tests/test_demo_fallback.py tests/test_lesson_draft_ai_generation.py tests/test_deepseek_timeout_and_material_budget.py tests/test_outlines_provider_fallback.py tests/test_lesson_materials_outline_v2_ui.py tests/test_drafts_routes.py tests/test_teaching_prep_reference_suggestions.py`，结果 `49 passed in 17.94s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`，结果 `168 tests collected in 1.14s`，比施工前新增 5 个测试；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `168 passed in 47.88s`。
- `git diff --check` 结果：已运行，结果无输出。
- 未完成 / 待确认：本轮未处理 return_to 非法提示、学习通导出失败、Markdown 下载失败、DOCX 下载失败、上传错误、账号体系、部署或全局异常页面；未做浏览器人工页面验收；未 commit、未 push。
- 风险点：V2 资料整理页的 fallback 提示通过安全短 query reason 直接在模板读取展示，避免修改本轮禁止的 `materials.py`；建议人工分别在无 Key 和模拟 DeepSeek 失败场景下检查知识主干、课前学情测试、学生导学案和备课参考建议页面提示位置是否符合预期。
- 下一轮建议：继续按 Phase 2 审计拆分小步处理，优先选择导出失败中文提示或 return_to 非法提示，不要与 AI fallback 再混合施工。

### 2026-06-10 14:22 +08｜Phase 2.3b：AI fallback 提示样式收束

- 日期时间：2026-06-10 14:22 +08
- 本轮目标：只修 Phase 2.3a 人工验收发现的 AI fallback 提示视觉语义，将无 DeepSeek API Key 与 DeepSeek provider error 的教师可见提示从绿色成功态收束为 warning / notice 提示态。
- 本轮修改范围：`backend/app/templates/knowledge_outline.html`、`backend/app/templates/lesson_materials_outline_v2.html`、`backend/app/templates/diagnostic_probe_v2.html`、`backend/app/templates/learning_guides_v2.html`、`backend/app/templates/lesson_drafts.html`、`backend/tests/test_lesson_materials_outline_v2_ui.py`、`backend/tests/test_outlines_provider_fallback.py`、`backend/tests/test_drafts_routes.py`、`backend/tests/test_teaching_prep_reference_suggestions.py`、`docs/worklog.md`。
- 已完成内容：复用项目已有 `.notice` 浅黄 warning 样式，为所有 fallback 提示增加 `ai-fallback-notice` 标识；legacy 知识主干页、V2 资料主干页、课前学情测试 V2 页、学生导学案 V2 页、legacy 导学草稿页和备课参考建议所在的 V2 资料整理页均不再用 `.alert` 渲染 fallback 提示；学习通导出成功提示和导学案依赖提示未纳入本轮 fallback 样式调整。
- 文案与业务逻辑：`missing_api_key` 文案仍为“当前未设置 DeepSeek API Key，已生成本地结构化草稿。”；`provider_error` 文案仍为“AI 服务暂时不可用，系统已提供本地草稿，可稍后重试。”；未修改 fallback reason、AI 生成逻辑、API Key 存储、DeepSeek 调用、route、service、数据库、上传或导出逻辑。
- 新增或调整测试：调整现有 fallback UI 断言，确认 missing_api_key / provider_error 提示包含 `notice ai-fallback-notice`、不再以 `<p class="alert">...` 渲染；正常 AI 成功路径继续断言不显示两类 fallback 文案，且不出现 `ai-fallback-notice`。本轮未新增测试数量。
- 施工前测试结果：已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `168 passed in 55.28s`。
- 施工后测试结果：已运行受影响测试集 `PYTHONPATH=. ../.venv/bin/pytest -q tests/test_lesson_materials_outline_v2_ui.py tests/test_outlines_provider_fallback.py tests/test_drafts_routes.py tests/test_teaching_prep_reference_suggestions.py`，结果 `36 passed in 19.16s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest --collect-only -q`，结果 `168 tests collected in 1.20s`；已运行 `cd backend && PYTHONPATH=. ../.venv/bin/pytest -q`，结果 `168 passed in 50.42s`。
- `git diff --check` 结果：已运行，结果无输出。
- 未完成 / 待确认：未做浏览器人工页面验收；未处理 return_to 非法提示、学习通导出失败、Markdown / DOCX 下载失败、上传错误、账号体系或部署问题；未 commit、未 push。
- 风险点：本轮未改 CSS，仅复用 `.notice` 现有样式；如人工希望 V2 页面有更独立的 info/warning 视觉，可后续单独补极小 CSS，但当前已避免 fallback 呈现为绿色成功态。
- 下一轮建议：人工分别查看无 Key 和模拟 provider_error 场景下的知识主干、课前学情测试、学生导学案和备课参考建议提示位置与视觉是否符合预期。

### 2026-06-14 10:43 +08｜Phase 2.4：return_to 非法回退提示

- 日期时间：2026-06-14 10:43 +08
- 本轮目标：只处理 `return_to` 非法时的教师可见中文提示，保持开放跳转防护，不处理导出失败、AI fallback、上传错误、账号体系、部署或全局异常页面。
- 本轮修改范围：`backend/app/main.py`、`backend/app/routes/courses.py`、`backend/app/routes/course_plans.py`、`backend/app/routes/materials.py`、`backend/app/routes/outlines.py`、`backend/app/routes/drafts.py`、`backend/app/routes/exports.py`、`backend/app/templates/courses_v2.html`、`backend/tests/test_ai_settings_routes.py`、`backend/tests/test_course_plans_routes.py`、`backend/tests/test_lesson_materials_outline_v2_ui.py`、`docs/worklog.md`。
- return_to 非法提示实现方式：保留原 `sanitize_next_path` 兼容语义，新增 `sanitize_next_path_with_status(...)` 返回 `(safe_path, was_invalid)`；新增 `resolve_return_to_path(...)`，在非空 `return_to` 非法时统一回退 `/ui-v2/courses?return_to_invalid=1`；课程中心 V2 页面根据安全短标记显示固定文案“返回地址无效，已返回课程中心。”。
- 开放跳转防护保持情况：继续拒绝外部 URL、协议相对 URL、反斜杠路径、控制字符、带 scheme / netloc 的 URL；非法原始 URL 不进入重定向目标，不进入页面展示；合法站内 `return_to` 保持原路径返回；空 `return_to` 继续走各 route 原默认页面。
- 新增或调整测试：扩展 sanitizer/helper 断言；调整授课计划上传页非法 `return_to` 测试，从静默回退改为课程中心提示；将课次资料提交非法 `return_to` 测试参数化覆盖 `https://evil.example/path`、`//evil.example/path`、`/\\evil`；合法 V2 `return_to` 测试新增“不显示非法提示”断言。
- pytest collect-only 结果：施工前 `168 tests collected in 1.40s`；施工后 `170 tests collected in 0.66s`，比施工前增加 2 个参数化非法 `return_to` 场景。
- 完整 pytest 结果：施工前 `168 passed in 34.46s`；施工后 `170 passed in 35.89s`。
- `git diff --check` 结果：已运行，结果无输出。
- 未完成 / 待确认：未做浏览器人工页面验收；未处理学习通导出失败、Markdown 下载失败、DOCX 下载失败、授课计划上传大小限制、AI fallback、上传格式、账号体系、部署或全局异常页面。
- 风险点：非法 `return_to` 现在统一回 V2 课程中心提示；这符合本轮目标文案，但部分 legacy route 的非法返回不再停留在原 legacy 默认页。合法 return_to 与空 return_to 未改变。
- 下一轮建议：继续按 Phase 2 审计小步处理，优先单独安排导出 / 下载失败中文提示，不要与 return_to 或 AI fallback 混合。
- 提交状态：未 commit，未 push。
