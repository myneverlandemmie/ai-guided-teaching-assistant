# Phase 2 错误提示与异常处理统一：只读审计报告

## 1. 审计范围

本轮为 Phase 2 第一轮只读审计，未修改业务代码、模板、静态文件、测试文件、README、数据库、上传文件或导出文件。

重点阅读范围：

- `backend/app/main.py`
- `backend/app/routes/ai_settings.py`
- `backend/app/routes/courses.py`
- `backend/app/routes/course_plans.py`
- `backend/app/routes/lessons.py`
- `backend/app/routes/materials.py`
- `backend/app/routes/outlines.py`
- `backend/app/routes/drafts.py`
- `backend/app/routes/exports.py`
- `backend/app/services/`
- `backend/app/templates/`
- `backend/app/static/`

说明：仓库根目录下未发现独立 `templates/`、`static/` 目录；当前模板和静态资源实际位于 `backend/app/templates/` 与 `backend/app/static/`。

本轮重点搜索了：

- `HTTPException`、`raise`、`except`、`status_code=500`、`traceback`、`logger`
- `return_to`、`message`、`error`
- `DeepSeek`、`fallback`
- `UploadFile`、`xlsx`、`docx`、`pptx`
- `export`、下载与文件写入路径

## 2. 当前总体结论

- 已有中文提示的场景较多：课程名称为空、授课计划非 `.xlsx`、授课计划解析失败、课次资料不支持格式、`.docx` / `.pptx` / `.xlsx` 提取失败、导学案依赖顺序、导学案生成 fallback、AI 设置页空 Key 和非法模型等均已有中文文案。
- 可能直接 500 的重点路径集中在文件系统和未捕获异常：课次资料大文件读取、上传目录 / 导出目录创建失败、学习通 xlsx 写出失败、Markdown 写出失败、导出文件读取失败、数据库提交异常、部分 openpyxl 读取异常之外的运行时异常。
- 已有 fallback 但教师看不到明确提示的路径包括：知识主干未设置 API Key 时生成本地结构化草稿、备课参考建议无 Key 或 DeepSeek 失败时本地 fallback。导学案和前测页面已有 `draft_fallback=1` 提示，但文案把“未设置 Key”和“DeepSeek 失败”混在一起，不能精确对应 P0 目标文案。
- DeepSeek 调用失败在不同模块行为不一致：知识主干生成失败时显示错误并不生成本地 fallback；导学案和备课参考建议服务会 fallback，但 route 层提示不一致。
- `return_to` 已有安全清洗，非法地址会回退到默认站内地址，但当前基本是静默回退，教师看不到“返回地址无效，已返回课程中心”这类提示。
- 本轮未发现 `logger`、`logging`、`traceback`、`print()`、`status_code=500` 或自定义异常 handler。当前主要风险不是主动日志泄露，而是缺少统一的教师可见错误落点。
- 暂不建议 Phase 2 抢跑全局复杂异常系统、账号体系、部署层 500 页、数据库结构、DOCX 导出或学生端能力；建议先在已有 route / service 小步补齐目标场景。

## 3. 场景逐项审计表

| 优先级 | 场景 | 当前入口/文件 | 当前行为 | 是否可能 500 | 是否已有中文提示 | 建议处理方式 | 建议施工轮次 |
|---|---|---|---|---|---|---|---|
| P0 | API Key 未设置 | `routes/outlines.py`、`routes/drafts.py`、`services/ai/provider.py`、`services/ai/lesson_draft_ai_service.py`、`services/teaching_prep_reference_service.py` | 知识主干无 Key 时生成 `local-structured-draft` 并直接跳转；导学案无 Key 时 fallback 并部分页面显示 `draft_fallback`；备课参考建议无 Key 时 fallback 但不显示提示。 | 一般不 500 | 部分有。导学案有泛化提示，知识主干和备课建议缺少生成后的明确提示。 | 区分“未设置 Key”和“AI 调用失败”两类 fallback 原因；生成后在目标 V2 页面显示“当前未设置 DeepSeek API Key，已生成本地结构化草稿。” | Phase 2.3 |
| P0 | DeepSeek 调用失败 | `services/ai/deepseek_client.py`、`routes/outlines.py`、`services/ai/lesson_draft_ai_service.py`、`services/teaching_prep_reference_service.py` | 知识主干捕获 `DeepSeekProviderError` 后显示错误，不生成本地草稿；导学案和备课建议捕获后 fallback。 | 部分未预期异常仍可能 500 | 有中文错误或泛化 fallback 提示，但不统一。 | 知识主干也应 fallback 到本地结构化草稿，或至少按产品目标统一为“AI 服务暂时不可用，系统已提供本地草稿，可稍后重试。” | Phase 2.3 |
| P0 | 上传格式不支持 | `routes/materials.py`、`services/lesson_materials/document_text_extractor.py`、`routes/course_plans.py` | 课次材料仅允许 `.txt/.md/.docx/.pptx/.xlsx`，`.xls` 有单独中文提示；授课计划仅允许 `.xlsx`。 | 否 | 已有，且较完整。 | 保持现有格式判断，Phase 2.1 只统一目标文案，优先让 V2 上传错误仍回到 V2 页面。 | Phase 2.1 |
| P1 | xlsx 空表 | `services/lesson_materials/document_text_extractor.py`、`routes/materials.py` | 空表会抛出“未从 .xlsx 中提取到可用文本”，route 拼接文件名和补充粘贴建议后展示。 | 否 | 已有，但不完全符合目标文案。 | 文案调整为“表格内容为空或未读取到有效文本，请检查后重新上传。”并保持粘贴补充建议。 | Phase 2.2 |
| P1 | 文件过大 | `routes/materials.py`、`routes/course_plans.py` | 课次材料使用 `await uploaded_file.read()` 一次性读入内存；授课计划使用 `shutil.copyfileobj` 保存；未发现上传大小限制或中文提示。 | 是 | 无 | 增加上传大小上限、流式或分块校验，超限时删除临时文件并提示“文件过大，请拆分资料后上传。” | Phase 2.1 |
| P1 | `return_to` 非法 | `main.py:sanitize_next_path`、多 route、模板隐藏字段 | 已清洗非法路径并回退默认地址，避免开放跳转；当前静默回退。 | 否 | 无 | 保持安全清洗，增加非法标志或 query message；课程中心相关回退显示“返回地址无效，已返回课程中心。” | Phase 2.4 |
| P2 | 学习通导出失败 | `routes/exports.py`、`services/ai/lesson_draft_service.py` | `mkdir`、`write_chaoxing_template_xlsx`、`workbook.save` 未捕获异常；非法草稿类型用 `HTTPException`。 | 是 | 只有 400/404 detail；真实写出失败无教师友好提示。 | 捕获导出写文件异常，返回原页面或重定向附带“习题文件导出失败，请检查题卡内容后重试。”并补测试。 | Phase 2.5 |
| P2 | Markdown 下载失败 | `routes/exports.py` | `mkdir`、`write_text` 未捕获异常；下载本身直接返回 `draft.content`。 | 是 | 只有 400/404 detail；写出失败无教师友好提示。 | 捕获写出异常；考虑 Markdown 下载不强依赖落盘，失败时返回友好页面或重定向提示“下载文件生成失败，请重新生成或稍后再试。” | Phase 2.5 |

## 4. Route / Service 风险点

### ai_settings.py

- API Key 只保存在服务端内存 session store，不入库、不回显完整 Key，模板展示掩码，当前边界合理。
- 空 Key 保存已有中文提示“请输入有效的 DeepSeek API Key。”，非法模型也有中文提示。
- `next` 使用 `sanitize_next_path`，非法时静默置空；适合安全，但如果 Phase 2 统一 `return_to` 文案，需要考虑 AI 设置页是否也显示非法返回地址提示。
- `require_same_origin` 失败会抛 `HTTPException(403)`，当前没有 HTML 友好错误页；这不是本轮目标表格里的核心 P0/P1，但属于公共异常体验缺口。

### course_plans.py

- 非 `.xlsx` 授课计划上传已有中文错误，且留在上传页。
- `import_course_plan` 会捕获解析异常并写入 `CoursePlanUpload.error_message`，预览页展示中文或异常文本；对业务解析失败较稳。
- 上传文件大小没有限制；保存文件和数据库提交异常会冒泡，可能 500。
- `return_to` 非法时静默回退 `/courses`；没有“返回地址无效”的教师可见提示。

### materials.py

- 课次材料上传格式提示最完整，支持 `.txt/.md/.docx/.pptx/.xlsx`，明确不支持 `.xls`、PDF、图片、扫描件、旧版 `.doc/.ppt`。
- `.docx`、`.pptx`、`.xlsx` 提取失败均转为 `LessonMaterialExtractionError`，route 会展示中文提示并删除失败上传文件。
- `.xlsx` 空表已有“未从 .xlsx 中提取到可用文本”，建议改为目标文案。
- 未发现文件大小上限；`await uploaded_file.read()` 会把整个文件读入内存，过大文件可能导致内存压力、磁盘压力或 500。
- V2 页面提交资料出错时，当前 route 统一渲染 `lesson_detail.html`，不是 `lesson_materials_outline_v2.html`；教师可能从 V2 流程掉回 legacy 页面。Phase 2.1 处理上传错误时建议一起收束。

### outlines.py

- 无 API Key 时 `provider.py` 会返回本地结构化草稿，但 route 只保存并跳转，页面没有明确提示“当前未设置 DeepSeek API Key”。
- 有 API Key 但 DeepSeek 失败时，route 捕获 `DeepSeekProviderError` 并显示 `exc.user_message`，不会 fallback 到本地结构化草稿；这与 Phase 2 目标“AI 服务暂时不可用，系统已提供本地草稿”不一致。
- 错误展示区已存在：legacy `knowledge_outline.html` 和 V2 `lesson_materials_outline_v2.html` 均可承载 `error_message`。后续施工可小步复用，不需要新建复杂全局异常系统。
- `require_same_origin` 的 403 仍是默认 HTTPException 体验。

### drafts.py

- 课前学情测试、学生导学案和 legacy drafts 页面已有 `fallback_message` 展示，能覆盖无 Key、超时、调用失败等情况，但文案目前过于泛化。
- `generate_tiered_lesson_draft_route` 能根据 `used_fallback` 给 `return_to` 追加 `draft_fallback=1`；V2 页面可以展示。
- `generate_teaching_prep_reference_route` 调用服务时接收 `_used_fallback` 但没有把 fallback 状态带回页面；教师看不到无 Key 或 DeepSeek 失败时使用了本地结构化草稿。
- 导学案依赖顺序已有中文提示并通过 query 参数展示，当前可保留。
- 未捕获非 `DeepSeekProviderError` 的意外异常，例如数据库提交失败、prompt 构造或 service 内部运行时错误，仍可能 500。

### exports.py

- 学习通导出成功后会带 `chaoxing_file` 回到原页面，页面已有“学习通题库模板已生成”下载提示。
- 学习通导出写文件失败没有捕获，`mkdir`、`Workbook.save`、磁盘权限 / 空间问题都可能直接 500。
- 下载学习通文件时非法文件名和文件不存在会抛 404 `HTTPException`，不是教师友好页面。
- Markdown 下载会写入 `data/exports/guides`，但返回内容来自 `draft.content`；写出失败仍会阻断下载并可能 500。可以考虑后续让下载不依赖落盘，或捕获写出失败后给出目标中文提示。

### main.py / 公共依赖

- `sanitize_next_path` 安全边界清晰：只允许站内相对路径，拒绝 `//`、反斜杠、控制字符、scheme 和 netloc。
- 当前 `sanitize_next_path` 只返回路径或 `None`，无法告诉 route “输入曾经非法”；如果要显示 return_to 非法提示，需要新增轻量 helper 或返回额外标志。
- `_safe_export_filename` 能限制导出下载文件名，避免路径穿越；当前只返回 `None`，错误体验由调用方决定。
- 未发现全局 `exception_handler`、自定义 500 页面或 `debug=True`。
- `main.py` 当前主要负责 app 初始化、公共 helper 和 router 注册。Phase 2 不建议把大段业务异常逻辑重新塞回 `main.py`。

## 5. 日志与隐私边界审计

本轮检查项：

- 日志记录 API Key
- 日志记录教师上传材料全文
- 日志记录完整 prompt
- 异常页面暴露技术栈
- 500 页面直接展示 traceback

本轮结论：

- 未发现 `logger`、`logging`、`traceback`、`print()` 调用。
- 未发现主动记录 API Key、教师上传材料全文或完整 prompt 的代码。
- `session_key_store.py` 中 `SessionApiKeyRecord.api_key` 使用 `field(repr=False)`，AI 设置页只展示掩码；API Key 不写 cookie，只保存 session id。
- prompt 构造前已有敏感信息过滤和材料长度限制；本轮未发现 prompt 被写日志。
- 未发现自定义 500 页面或 exception handler。生产环境若由 Uvicorn / Starlette 默认错误页处理，需继续确认部署时 debug 关闭，避免 traceback 暴露。
- 本轮未发现上述日志与隐私泄露风险，但后续施工需继续保持：不得记录完整 API Key、上传全文、完整 prompt、服务器绝对路径或 traceback。

## 6. 建议分轮施工计划

### Phase 2.1：上传格式与文件大小提示

- 修改范围：优先 `backend/app/routes/materials.py`、必要时新增小型 service/helper；如处理授课计划大小，再涉及 `backend/app/routes/course_plans.py`。
- 目标：保留现有不支持格式中文提示，新增“文件过大，请拆分资料后上传。”；V2 上传错误应回到 V2 资料整理页，不掉回 legacy 详情页。
- 是否需要新增测试：需要。覆盖不支持格式、超限文件、V2 return_to 下错误页面。
- 风险等级：中。涉及上传保存、失败清理和 V2 / legacy 页面分流。
- 验收方式：pytest；手工在 V2 资料整理页上传 `.pdf`、`.xls`、超限文件，确认中文提示和页面位置。

### Phase 2.2：xlsx 空表提示

- 修改范围：`backend/app/services/lesson_materials/document_text_extractor.py`、`backend/app/routes/materials.py` 文案或错误映射。
- 目标：将空表提示统一为“表格内容为空或未读取到有效文本，请检查后重新上传。”。
- 是否需要新增测试：需要。新增空 `.xlsx` 或仅空单元格 `.xlsx` 上传测试。
- 风险等级：低。
- 验收方式：pytest；手工上传空 xlsx，确认提示。

### Phase 2.3：AI Key 缺失与 DeepSeek fallback 提示

- 修改范围：`backend/app/routes/outlines.py`、`backend/app/routes/drafts.py`、`backend/app/services/ai/provider.py`、`backend/app/services/ai/lesson_draft_ai_service.py`、`backend/app/services/teaching_prep_reference_service.py`，必要时新增小型结果结构表示 fallback reason。
- 目标：区分无 Key 和 DeepSeek 调用失败；知识主干、前测、导学案、备课建议都能显示对应 P0 文案；知识主干 DeepSeek 失败时按产品目标提供本地草稿。
- 是否需要新增测试：需要。覆盖无 Key、DeepSeekProviderError、V2 页面提示、legacy 页面不破坏。
- 风险等级：中到高。涉及 AI 生成语义和现有测试断言。
- 验收方式：pytest；手工清空 Key 生成知识主干 / 前测 / 导学案 / 备课建议，再模拟错误或使用无效 Key 验证提示。

### Phase 2.4：return_to 非法回退提示

- 修改范围：`backend/app/main.py` 公共 helper 轻量扩展或在 route 层增加检测；相关 route 为 `courses.py`、`course_plans.py`、`materials.py`、`outlines.py`、`drafts.py`、`exports.py`。
- 目标：保持开放跳转防护，同时让教师看到“返回地址无效，已返回课程中心。”或对应页面提示。
- 是否需要新增测试：需要。覆盖外部 URL、`//evil`、反斜杠、控制字符。
- 风险等级：中。多 route 共用，需避免一次改太多。
- 验收方式：pytest；手工构造非法 `return_to` 表单提交。

### Phase 2.5：导出与下载失败提示

- 修改范围：`backend/app/routes/exports.py`，必要时小幅拆到 `backend/app/services/exports/`。
- 目标：学习通导出失败显示“习题文件导出失败，请检查题卡内容后重试。”；Markdown 下载失败显示“下载文件生成失败，请重新生成或稍后再试。”。
- 是否需要新增测试：需要。monkeypatch 写文件失败、目录创建失败、非法草稿类型。
- 风险等级：中。涉及文件下载响应和 redirect 行为。
- 验收方式：pytest；手工导出前测 xlsx、下载 Markdown。

### Phase 2.6：日志脱敏与统一 helper 收束

- 修改范围：仅在前几轮稳定后考虑，优先小 helper，不做全局复杂异常系统。
- 目标：固化安全错误文案、fallback reason、上传错误、导出错误和非法 return_to 的复用方式；继续保持不记录 Key / prompt / 全文材料。
- 是否需要新增测试：视前几轮覆盖缺口补充。
- 风险等级：中。
- 验收方式：pytest；代码审计确认无敏感日志。

## 7. 本轮不建议处理的内容

Phase 2 不建议抢跑以下内容：

- 账号体系、登录注册、权限模型、多用户隔离。
- DOCX 导出。
- 学生端。
- 自动批阅平台、自动评分、自动发布评语。
- 教师能力评价。
- 全局复杂异常系统或一次性替换所有 `HTTPException`。
- 部署、Docker、Nginx、生产错误页治理。
- 数据库结构调整、迁移脚本或运行数据清理。
- 学习通 API 直连或自动发布。
