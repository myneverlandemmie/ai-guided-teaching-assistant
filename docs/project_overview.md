# 智学导评 V0.2 项目总览

更新时间：2026-06-03

## 项目定位

- 项目名称：智学导评 V0.2 / ai-guided-teaching-assistant。
- 仓库目录名当前仍为 `ai-guided-sql-assessment`。
- 项目面向中职教师，定位为 AI 辅助教学设计分析与导学案生成系统。
- 系统服务教师备课、资料整理、知识主干生成、课前学情测试草稿和学生导学案草稿准备。
- 本项目不是学生端系统、自动备课系统、自动批阅平台、教师能力评价系统，也不直接替代教师教学设计。
- 所有 AI 输出和本地 fallback 输出均为教师草稿，必须由教师审阅、修改、确认后再使用。

## 当前阶段目标

- 当前阶段：案例材料已提交后的产品化改进与工程重构阶段。
- 保持 V0.2 教师端主流程稳定，继续完善本地演示和教师草稿生成链路。
- 持续拆分 `backend/app/main.py` 中的业务 route，使入口文件回归 FastAPI app 初始化、公共依赖初始化、静态文件和模板挂载、router 注册、必要启动逻辑。
- 建立项目手账和 QA 检查表，降低后续多轮 Codex 施工的交接风险。
- 生产部署、正式权限体系、正式数据库方案和对外真实班级使用边界：待确认。

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
- 题卡预览、单题编辑、单题删除和学习通习题文件导出。
- 学生导学案 V2：`/ui-v2/lessons/{lesson_id}/learning-guides`。
- 全班通用导学案、巩固提升任务包、拓展探究任务包和 Markdown 下载。
- 教师编辑保存草稿。
- 本地结构化草稿与 fallback，用于演示不中断和教师初稿准备。

## 当前已完成的 Route 拆分

- `backend/app/routes/ai_settings.py`：AI 设置、保存、清除相关 route。
- `backend/app/routes/courses.py`：根入口、课程列表、V2 课程中心、课程创建、重命名、删除相关 route。
- `backend/app/routes/course_plans.py`：授课计划上传、上传结果预览、确认生成正式课次相关 route。
- `backend/app/routes/lessons.py`：课程下正式课次列表、正式课次详情相关 route。
- `backend/app/routes/materials.py`：课程资料整理 V2、课次资料提交、课次资料删除相关 route。

## 当前待拆模块

- `backend/app/routes/outlines.py`：知识主干生成、知识主干页、知识主干保存相关 route。
- `backend/app/routes/drafts.py`：课前学情测试页、学生导学案页、草稿列表、草稿生成、草稿保存相关 route。
- `backend/app/routes/exports.py`：学习通习题文件导出、导出文件下载、Markdown 下载相关 route。

## 暂缓模块

- 完整注册 / 登录 / 权限体系。
- 学生端。
- 学习通 API 直连或自动发布。
- 作业批阅后端、自动评分 route、自动发布评语、学生成绩统计。
- 教师能力评价。
- OCR、PDF、图片、扫描件、旧版 `.doc/.ppt`、`xls` 解析。
- 面向外部真实班级的公开生产服务。
- 复杂 Vue / React 前端重构。
- API Key 长期加密存储和多用户密钥管理。

## 工程约束

- `backend/app/main.py` 只负责 FastAPI app 初始化、公共依赖初始化、静态文件和模板挂载、router 注册、必要启动逻辑。
- 新 route 放在 `backend/app/routes/`。
- 业务编排和可复用逻辑优先放在 `backend/app/services/`。
- 导出相关逻辑优先放在 `backend/app/services/exports/` 或 `backend/app/routes/exports.py`。
- Prompt 模板和提示词文档放在 `docs/prompts/`。
- `main.py` 路由拆分必须一轮只迁移一组 route。
- 每轮必须保持 route path、模板名称、表单字段、redirect 行为不变。
- 每轮不得改变数据库结构、已有测试夹具和演示数据语义。
- 代码施工轮不得顺手修改 README、报告、prompt 文档或其他 `docs/` 文件；追加 `docs/worklog.md` 作为交接记录除外。
- 每轮开始前查看 `git status`，施工后按本轮性质运行测试或明确说明未运行原因，并追加工作手账。

## 当前风险

- `backend/app/main.py` 仍保留 outlines、drafts、exports 相关业务 route 和辅助逻辑，后续拆分需要逐组迁移并防止 path、模板、表单字段、redirect 行为变化。
- 部分历史文档仍可能保留旧阶段表述，后续如需统一口径应单独安排文档治理轮次。
- 当前默认本地 SQLite 和 `create_all` 更适合开发 / 演示，生产数据库、迁移和部署策略待确认。
- DeepSeek 调用依赖教师提供的 API Key 和外部网络；生成失败时可能进入本地结构化草稿或 fallback，需要在演示和文档中明确边界。
- 本地运行数据、上传文件和导出文件属于运行产物，清理脚本具有破坏性，施工中不得擅自删除或改写。
- 完整权限、安全审计、备份、日志和多用户数据隔离方案尚未实现，不应作为已完成能力对外描述。
