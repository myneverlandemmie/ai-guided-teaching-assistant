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
