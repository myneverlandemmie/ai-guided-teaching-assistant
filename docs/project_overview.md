# 智学导评 V0.2 项目总览

更新时间：2026-06-15

## 项目定位

- 项目名称：智学导评 V0.2 / ai-guided-teaching-assistant。
- 仓库目录名当前仍可能为 `ai-guided-sql-assessment`。
- 项目面向中职教师，定位为 AI 辅助教学设计分析与导学案生成系统。
- 系统服务教师备课、资料整理、知识主干生成、课前学情测试草稿、学生导学案草稿和备课参考建议准备。
- 本项目不是学生端系统、自动备课系统、自动批阅平台、教师能力评价系统，也不直接替代教师教学设计。
- 所有 AI 输出和本地 fallback 输出均为教师草稿，必须由教师审阅、修改、确认后再使用。

## 当前阶段状态

- 当前阶段：v0.3 closing，准备后续 push main 和打 `v0.3.0` tag。
- 当前测试基线：`174 passed`。
- 当前主流程仍以 V2 教师端页面为默认演示入口：`/ui-v2/courses`。
- 当前工程重点为案例材料已提交后的产品化改进与工程重构。
- 生产部署、正式权限体系、正式数据库方案和对外真实班级使用边界仍待后续版本确认。

## 技术栈

- 后端：Python、FastAPI、Uvicorn。
- 页面渲染：Jinja2 模板。
- 数据访问：SQLAlchemy；默认本地数据库为 SQLite `app.db`。
- 数据库迁移：依赖中包含 Alembic；当前启动逻辑仍使用 `create_all` 支撑本地开发和演示。
- 可选数据库驱动：依赖中包含 PyMySQL；正式数据库使用方式待确认。
- 表单和上传：`python-multipart`。
- 文档和表格解析：`python-docx`、`python-pptx`、`openpyxl`。
- AI Provider：DeepSeek Provider 与会话级 API Key 设置；长期加密存储方案待确认。
- 测试：pytest、httpx。

## 当前已完成模块

- 课程管理与 V2 课程中心：`/ui-v2/courses`。
- 授课计划上传、Excel 解析、预览、确认 / 跳过和正式课次生成。
- 正式课次列表与正式课次详情页。
- 课次资料上传、粘贴文本、多文件上传、删除和基础文本提取。
- 当前资料文本提取支持 `txt`、`md`、`docx`、`pptx`、`xlsx`。
- 会话级 DeepSeek API Key 设置、掩码显示、清除和模型选择。
- 知识主干生成、教师编辑和保存。
- 知识主干生成前的基础行政信息过滤。
- 课程资料整理 V2：`/ui-v2/lessons/{lesson_id}/materials-outline`。
- 备课参考建议。
- 课前学情测试 V2：`/ui-v2/lessons/{lesson_id}/diagnostic-probe`。
- 题卡预览、单题编辑、单题删除和学习通题库模板导出。
- 学生导学案 V2：`/ui-v2/lessons/{lesson_id}/learning-guides`。
- 全班通用导学案、巩固提升任务包、拓展探究任务包。
- Markdown 下载。
- DOCX 下载 V0.1。
- 教师编辑保存草稿。
- 本地结构化草稿与 fallback，用于演示不中断和教师初稿准备。
- 中文友好错误提示，覆盖上传、AI fallback、非法 `return_to`、导出 / 下载失败等核心场景。

## Phase 1 已完成

- `backend/app/main.py` route 拆分已完成。
- `main.py` 已收束为 FastAPI app 初始化、公共依赖初始化、静态文件和模板挂载、router 注册及必要启动逻辑。
- route 已拆入 `backend/app/routes/`：
  - `ai_settings.py`
  - `courses.py`
  - `course_plans.py`
  - `lessons.py`
  - `materials.py`
  - `outlines.py`
  - `drafts.py`
  - `exports.py`
- 测试拆分已完成，原大测试文件已拆分到更明确的 route / feature 测试文件。
- 测试 helper 已迁移为显式复用模块，降低跨测试文件隐式依赖。
- 文档治理已建立：活跃手账 `docs/worklog.md`、归档手账 `docs/worklogs/`、审计记录 `docs/audit/` 和 QA 清单 `docs/qa_checklist.md`。

## Phase 2 已完成

Phase 2 当前目标范围已完成，重点包括：

- 上传格式与大小提示：
  - 课次资料上传保留 `txt`、`md`、`docx`、`pptx`、`xlsx` 支持范围。
  - 课次资料上传超限提示：“文件过大，请拆分资料后上传。”
  - 授课计划上传增加大小限制，超限时失败清理并显示中文提示。
- `.xlsx` 空表提示：
  - 课次资料 `.xlsx` 空表或未读取到有效文本时提示：“表格内容为空或未读取到有效文本，请检查后重新上传。”
- AI fallback P0 提示：
  - 未设置 DeepSeek API Key 时提示：“当前未设置 DeepSeek API Key，已生成本地结构化草稿。”
  - AI 服务不可用时提示：“AI 服务暂时不可用，系统已提供本地草稿，可稍后重试。”
  - 知识主干、课前学情测试 / 学生导学案、备课参考建议均纳入提示范围。
- `return_to` 非法提示：
  - 非法返回地址统一回退课程中心并显示：“返回地址无效，已返回课程中心。”
  - 保持外部 URL、协议相对 URL、反斜杠路径、控制字符等开放跳转防护。
- 导出 / 下载失败提示：
  - 学习通题库模板导出失败提示：“习题文件导出失败，请检查题卡内容后重试。”
  - Markdown / DOCX 下载生成失败提示：“下载文件生成失败，请重新生成或稍后再试。”
- 授课计划上传大小限制：
  - 采用分块保存与大小校验，避免先完整读取超大文件。
  - 超限时删除已创建的目标文件，不创建授课计划上传记录、计划课次或正式课次。

## Day 12.1 已完成

DOCX 下载 V0.1 已完成：

- 支持导学案 / 任务包 / 备课参考建议等草稿下载为 `.docx`。
- 支持标题、普通段落、列表、加粗、行内代码、代码块。
- 生成文档包含系统标识、教师草稿提示、课程 / 课次信息和草稿正文。
- DOCX 为基础可编辑稿，不是精排模板。
- 暂不支持复杂 Markdown 完整转换，例如复杂嵌套列表、表格完整转换、图片、超链接、脚注、数学公式、HTML、代码高亮和复杂模板样式。

## 暂缓模块

- 完整注册 / 登录 / 权限体系。
- 学生端。
- 学习通 API 直连或自动发布。
- 作业批阅后端、自动评分 route、自动发布评语、学生成绩统计。
- 教师能力评价。
- 完整版本历史。
- OCR、PDF、图片、扫描件、旧版 `.doc/.ppt`、`xls` 解析。
- PDF 导出。
- 面向外部真实班级的公开生产服务。
- 复杂 Vue / React 前端重构。
- API Key 长期加密存储和多用户密钥管理。
- 正式部署能力。

## 工程约束

- `backend/app/main.py` 只负责 FastAPI app 初始化、公共依赖初始化、静态文件和模板挂载、router 注册、必要启动逻辑。
- 新 route 放在 `backend/app/routes/`。
- 业务编排和可复用逻辑优先放在 `backend/app/services/`。
- 导出相关逻辑优先放在 `backend/app/services/exports/` 或 `backend/app/routes/exports.py`。
- Prompt 模板和提示词文档放在 `docs/prompts/`。
- 每轮施工必须保持 route path、模板名称、表单字段、redirect 行为不变，除非用户明确要求改变。
- 每轮不得改变数据库结构、已有测试夹具和演示数据语义。
- 代码施工轮不得顺手修改 README、报告、prompt 文档或其他 `docs/` 文件；追加 `docs/worklog.md` 作为交接记录除外。
- 每轮开始前查看 `git status`，施工后按本轮性质运行测试或明确说明未运行原因，并追加工作手账。

## 当前风险

- 当前默认本地 SQLite 和 `create_all` 更适合开发 / 演示，生产数据库、迁移和部署策略待确认。
- DeepSeek 调用依赖教师提供的 API Key 和外部网络；生成失败时可能进入本地结构化草稿或 fallback，需要在演示和文档中明确边界。
- 本地运行数据、上传文件和导出文件属于运行产物，清理脚本具有破坏性，施工中不得擅自删除或改写。
- 完整权限、安全审计、备份、日志和多用户数据隔离方案尚未实现，不应作为已完成能力对外描述。
- DOCX V0.1 仍是基础可编辑稿，复杂 Markdown 或正式排版模板需后续单独建设。
- 学习通能力仅为题库模板文件导出，不是 API 直连或自动发布。

## v0.4-v0.7 建议

- `v0.4`：草稿版本保护。
- `v0.5`：Prompt 校本化与质量校验。
- `v0.6`：轻量访问控制 / 校内局域网试用。
- `v0.7`：部署能力。
