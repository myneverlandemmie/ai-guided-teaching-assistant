# main.py 路由拆分收尾审计报告

## 1. 审计结论

- `backend/app/main.py` 的业务 route 拆分已基本完成。审计命令 `grep -n "@app." backend/app/main.py` 未发现 `@app.*` route 装饰器。
- `main.py` 已基本回归入口文件职责：FastAPI app 创建、生命周期初始化、静态文件和模板挂载、公共依赖 / 常量定义、router 注册和少量跨模块 helper 注入。
- 当前不建议继续立刻大规模拆分 `main.py` 中剩余 helper 或抽 service。更稳妥的做法是先进入下一阶段产品化改进，并用现有测试与人工验收保护知识主干、草稿、导出等关键路径。

## 2. 当前文件规模

本轮统计命令：

```text
wc -l backend/app/main.py backend/app/routes/*.py
```

当前行数：

| 文件 | 行数 |
| --- | ---: |
| `backend/app/main.py` | 362 |
| `backend/app/routes/__init__.py` | 1 |
| `backend/app/routes/ai_settings.py` | 136 |
| `backend/app/routes/course_plans.py` | 170 |
| `backend/app/routes/courses.py` | 158 |
| `backend/app/routes/drafts.py` | 331 |
| `backend/app/routes/exports.py` | 107 |
| `backend/app/routes/lessons.py` | 100 |
| `backend/app/routes/materials.py` | 266 |
| `backend/app/routes/outlines.py` | 192 |
| 合计 | 1823 |

与原审计报告中 `main.py` 约 1492 行相比，当前 `main.py` 为 362 行，减少约 1130 行，约为原规模的 24.3%。这说明主要业务 route 已从入口文件中移出，入口文件体量已显著下降。

## 3. 已拆分 route 模块

- `ai_settings.py`：AI 设置页面、会话级 DeepSeek API Key 保存、清除、模型选择和 same-origin 校验相关 route。
- `courses.py`：根入口、课程列表、V2 课程中心、课程创建、重命名、删除相关 route。
- `course_plans.py`：授课计划上传、解析结果预览、确认生成正式课次相关 route。
- `lessons.py`：课程下正式课次列表、正式课次详情页相关 route。
- `materials.py`：课程资料整理 V2、课次资料提交、课次资料删除、资料标题和类别展示相关 route。
- `outlines.py`：知识主干生成、知识主干查看、教师编辑保存相关 route。
- `drafts.py`：备课参考建议、课前学情测试 V2、学生导学案 V2、草稿列表、草稿生成、草稿保存相关 route。
- `exports.py`：学习通习题文件导出、学习通导出文件下载、Markdown 下载相关 route。

## 4. main.py 当前剩余职责

当前 `main.py` 仍承担以下职责：

- FastAPI app 创建：`app = FastAPI(...)`。
- 启动初始化：`lifespan` 中调用 `create_database_tables(engine)`，用于本地开发和演示环境默认建表。
- 静态文件和模板挂载：`/static` 挂载、`Jinja2Templates` 初始化，以及 `basename` / `splitext` 模板过滤器注册。
- 路由注册：通过 8 组 `app.include_router(...)` 注册已拆分 router。
- 公共目录常量：项目根路径、模板目录、静态目录、授课计划上传目录、课次资料上传目录、学习通导出目录、导学案 Markdown 导出目录。
- 页面标签常量：资料类型、课次状态、知识主干状态、草稿状态、草稿下载文件名片段、默认资料标题、资料类别选项。
- 公共 helper：站内跳转路径清洗、same-origin 校验、知识主干 / 草稿读取、草稿 upsert、导出文件名校验、查询参数拼接、诊断题分布计算和 V2 前测页面上下文构造。
- 兼容测试和跨 router 注入：`get_db` 保持从 `main` 可访问，`run_in_threadpool` 通过 lambda 注入，以兼容既有测试 monkeypatch；导出目录也通过 lambda 注入，以兼容测试中覆盖 `main.CHAOXING_EXPORT_DIR` / `main.GUIDE_EXPORT_DIR` 的行为。
- demo 数据兜底：本轮审计未在 `main.py` 中看到显式 demo 数据生成 route；当前启动兜底主要是默认数据库表初始化。

## 5. main.py 中仍保留的 helper / 常量

### 继续留在 main.py

- `PROJECT_ROOT`、`TEMPLATE_DIR`、`STATIC_DIR`：入口初始化直接使用，留在 `main.py` 清晰。
- `COURSE_PLAN_UPLOAD_DIR`、`LESSON_MATERIAL_UPLOAD_DIR`、`CHAOXING_EXPORT_DIR`、`GUIDE_EXPORT_DIR`：当前通过 router 工厂注入，且测试会覆盖部分目录常量；短期留在 `main.py` 可降低风险。
- `templates`、模板过滤器注册、`app.mount("/static", ...)`：属于入口文件职责。
- `lifespan`：当前只做建表初始化，放在入口文件可接受。
- `require_same_origin`、`sanitize_next_path`：多个 router 复用，且属于横切安全边界；短期继续由入口注入较稳。
- `ai_provider` 引用和 `run_in_threadpool` 注入：保留可兼容既有测试和已经拆出的 router。

### 后续可考虑移动到 utils/

- `_safe_export_part`、`_safe_export_filename`、`_append_query_param`：更偏通用工具，可在后续单独迁移到路径 / 文件名工具模块。
- `_distribution`：属于页面统计轻量 helper，可考虑迁移到草稿或 V2 视图相关 utility。
- `_lesson_material_category_label`：与资料展示相关，可考虑放到 materials route 或轻量 presenter/helper。
- 各类 label 映射常量：后续可统一放入展示配置模块，但需要确认模板和测试引用方式后再迁移。

### 暂不建议移动

- `_get_latest_knowledge_outline`、`_get_lesson_drafts`、`_get_lesson_draft_by_type`、`_upsert_lesson_drafts`：这些 helper 虽然有 service 化空间，但影响知识主干、草稿生成、导出显示等多条路径。建议先稳定一段时间，再单独安排数据访问 / 草稿服务重构。
- `_learning_guide_dependency_message`：属于导学案生成依赖规则，移动时容易和产品规则调整混在一起，当前不建议在收尾阶段移动。
- `_diagnostic_probe_view_context`：依赖诊断题解析和页面上下文字段，移动时需要谨慎保护模板字段不变。

## 6. 风险与注意事项

- 不建议立刻继续大规模抽 service。当前 route 拆分已经降低 `main.py` 体量，继续大拆会提高回归风险。
- 不建议在收尾阶段同时改 UI、数据库、测试或模板字段。route 拆分刚完成，应该先保持行为稳定。
- `backend/tests/test_course_plan_pages.py` 等测试文件目前较大，但建议等 `main.py` 拆分稳定后，再单独做测试文件拆分专项。
- 下载 / 导出、fallback、`LessonDraft` upsert、知识主干生成失败返回 V2 上下文等行为仍需靠自动化测试和人工验收保护。
- 导出目录、文件名校验、下载响应头不应放宽；避免暴露服务器绝对路径。
- 当前阶段不应混入学生端、自动批阅、教师能力评价、学习通 API 直连或自动发布等暂缓功能。
- 仍需提醒：所有 AI 输出和本地 fallback 输出均为教师草稿，必须由教师审阅、修改、确认后再使用。

## 7. 下一阶段建议

1. Phase 2：中文错误提示与异常处理统一。
2. Phase 3：DOCX 导出。
3. Phase 4：草稿版本保护。
4. 测试文件拆分专项。
5. 轻量访问控制与部署文档。

## 8. 本轮审计命令记录

- `git status --short --branch`
  - 结果摘要：输出 `## refactor/main-routes`，开始审计时工作区无未提交改动。
- `wc -l backend/app/main.py backend/app/routes/*.py`
  - 结果摘要：`main.py` 362 行；routes 文件合计加 `main.py` 为 1823 行。
- `grep -n "@app." backend/app/main.py`
  - 结果摘要：无输出，命令返回 1；`main.py` 中未发现 `@app.*` route 装饰器。
- `grep -n "include_router" backend/app/main.py`
  - 结果摘要：发现 8 处 include_router 调用，位于第 291、292、293、294、303、319、334、351 行。
- `ls -la backend/app/routes`
  - 结果摘要：routes 目录包含 `ai_settings.py`、`courses.py`、`course_plans.py`、`lessons.py`、`materials.py`、`outlines.py`、`drafts.py`、`exports.py` 和 `__init__.py`。
- `sed -n '1,420p' backend/app/main.py`
  - 结果摘要：用于简要查看 `main.py` 当前职责；确认当前主要为 app 初始化、模板 / 静态挂载、公共 helper / 常量、router 注册和启动建表逻辑。
- `mkdir -p docs/audit`
  - 结果摘要：确保审计报告目录存在。
- `date '+%Y-%m-%d %H:%M %z'`
  - 结果摘要：记录本轮审计时间为 `2026-06-04 15:02 +0800`。

本轮未运行 pytest。原因：本轮仅文档审计，未修改业务代码、模板、测试或依赖配置。
