# Codex Build Prompt / Codex 施工提示词

## 中文说明

请帮助维护“智学导评 V0.2：面向中职教师的 AI 辅助教学设计分析与导学案生成系统”。

当前版本重点是教师端主流程收口：课程管理、课程计划上传、正式课次生成、课次资料整理、知识主干、备课参考建议、课前学情测试、学生导学案、学习通习题文件导出和 Markdown 下载。

不要把项目扩展成学生端、自动备课、一键完整教案、作业全自动处理系统或复杂教务系统。

## 硬性约束

1. 后端框架使用 FastAPI。
2. 前端继续优先使用 Jinja2 服务端模板。
3. V2 页面是推荐演示入口。
4. 旧页面作为 legacy / 兼容页面保留，案例提交前不要移动或删除旧模板。
5. 决策或行为变化时同步更新文档。
6. 每轮改动保持小步、可验证。
7. 不实现学生端。
8. 不实现登录权限体系，除非任务明确要求。
9. 不实现学习通 API。
10. 不实现作业批阅后端或自动评分 route。
11. 不新增数据库表或字段，除非任务明确要求并配套迁移方案。
12. 不改 DeepSeek Provider、AI settings 保存逻辑、`session_key_store`、fallback / upsert 核心逻辑和 `LessonDraft` 存储模型，除非任务明确要求。
13. 不把项目方演示服务器设计成公开生产服务。
14. 不提交 API Key、`backend/app.db`、上传文件、导出文件或用户个人路径。

## 当前已实现主流程

当前代码已实现：

- 课程管理；
- 课程中心 V2：`/ui-v2/courses`；
- 授课计划上传；
- Excel 课程计划解析；
- planned lessons 预览、确认、跳过；
- 批量生成正式 Lesson；
- 正式课次列表：`/courses/{course_id}/lessons`；
- 正式课次详情页；
- 课次材料上传、粘贴文本、多文件上传和删除；
- `txt` / `md` / `docx` / `pptx` / `xlsx` 资料文本提取；
- 课程资料整理 V2：`/ui-v2/lessons/{lesson_id}/materials-outline`；
- 知识主干生成、教师编辑和保存；
- 备课参考建议；
- 课前学情测试 V2：`/ui-v2/lessons/{lesson_id}/diagnostic-probe`；
- 题卡预览、单题编辑、单题删除；
- 学习通习题文件导出；
- 学生导学案 V2：`/ui-v2/lessons/{lesson_id}/learning-guides`；
- 全班通用导学案、巩固提升任务包、拓展探究任务包；
- Markdown 下载；
- 会话级 DeepSeek API Key 设置、掩码显示、清除和模型选择；
- 本地结构化草稿与 fallback。

测试状态以当前自动化测试结果为准。

## 当前未实现，后续不得误称已完成

- 完整登录权限体系；
- 学生端；
- 学习通 API；
- 作业批阅后端；
- 自动评分 route；
- 自动发布评语；
- 自动评价学生；
- 统计学生成绩；
- OCR；
- PDF、图片、扫描件、旧版 `.doc/.ppt`、`xls` 解析；
- 面向外部真实班级的公开生产服务。

## 推荐入口

默认演示入口：

```text
/ui-v2/courses
```

V2 主流程：

```text
/ui-v2/courses
→ /courses/{course_id}/lessons
→ /ui-v2/lessons/{lesson_id}/materials-outline
→ /ui-v2/lessons/{lesson_id}/diagnostic-probe
→ /ui-v2/lessons/{lesson_id}/learning-guides
```

## 作业批阅边界

作业批阅仅作为预留功能和后续探索方向。可描述为面向编程类、数据库类作业的规则测试与 AI 辅助评语草稿；结果仅供教师参考，需教师审核确认后使用。

不得写成已完成作业批阅、已实现自动评分、已有学生端、自动发布评语或自动评价学生。

## AI 设置与 API Key 规则

教师在 `/ai/settings` 中填写自己的 DeepSeek API Key，并选择模型：

- `deepseek-v4-flash`：适合快速预览；
- `deepseek-v4-pro`：适合正式生成、任务包和备课参考建议。

API Key 只保存在当前会话的服务端内存中，不写入数据库、不写入 cookie、不写入日志，也不得提交到 Git。

所有 AI 输出和本地结构化草稿都必须由教师审阅、修改、确认后使用。

## 每轮汇报格式

1. 新增或修改的文件；
2. 当前已完成内容；
3. 测试方法与结果；
4. 已知限制；
5. 是否建议人工检查后提交。
