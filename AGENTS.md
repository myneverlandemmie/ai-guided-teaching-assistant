# Codex Project Rules

## 项目定位
- 本项目是面向中职教师的 AI 辅助教学设计分析与导学案生成系统。
- 当前实际项目名称为“智学导评 V0.2 / ai-guided-teaching-assistant”，仓库目录名仍为 `ai-guided-sql-assessment`。
- 当前阶段为案例材料已提交后的产品化改进与工程重构阶段，不再使用“案例提交前”作为当前阶段表述。
- 本项目不是学生端系统、自动备课系统、自动批阅平台或教师能力评价系统。
- 所有 AI 输出均为教师草稿，必须由教师审阅、修改、确认后再使用。

## 工程边界
- `backend/app/main.py` 只负责 FastAPI app 初始化、公共依赖初始化、静态文件和模板挂载、router 注册、必要启动逻辑。
- 不得在 `backend/app/main.py` 中新增大段业务逻辑或新增功能 route。
- 新 route 应放在 `backend/app/routes/`。
- 业务编排和可复用逻辑优先放在 `backend/app/services/`。
- 导出相关逻辑优先放在 `backend/app/services/exports/` 或 `backend/app/routes/exports.py`。
- Prompt 模板和提示词文档放在 `docs/prompts/`，不要散落进 route 文件。

## 当前重构纪律
- `backend/app/main.py` 路由拆分必须一轮只迁移一组 route。
- 每轮必须保持 route path 不变。
- 每轮必须保持模板名称、表单字段、redirect 行为不变。
- 每轮不得改变数据库结构。
- 每轮不得改变已有测试夹具和演示数据语义。
- 每轮不得同时改 UI、后端、数据库和文档。

## 文档治理与手账
- 每轮施工前应阅读 `docs/project_overview.md`、`docs/worklog.md` 最新记录和 `docs/qa_checklist.md`。
- 每轮施工后应追加 `docs/worklog.md`，记录本轮目标、完成内容、修改文件、测试结果、未完成 / 待确认、风险点和下一轮建议。
- 追加 `docs/worklog.md` 属于交接记录，不视为“同时修改功能文档”；但代码施工轮不得顺手修改 README、报告、prompt 文档或其他 `docs/` 文件，除非用户明确要求。

## 测试命令
代码变更后必须运行：

```bash
cd backend && PYTHONPATH=. ../.venv/bin/pytest -q
```

仅文档变更时，可以不运行 pytest，但收工汇报必须明确说明原因。

## Codex 协作规则
- 每轮开始前先查看 `git status`。
- 每轮只做用户明确要求的一件事。
- 不要主动 commit。
- 完成后必须汇报：
  1. 修改了哪些文件；
  2. 做了什么；
  3. pytest 结果；
  4. 是否有风险点；
  5. 是否需要人工手工验收。
- 如发现任务需要修改禁止范围内的文件，应先停止并说明原因，不要擅自扩大范围。
