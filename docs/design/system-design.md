# System Design / 系统设计

## 设计定位

智学导评 V0.2 采用轻量化 Web 架构，服务于“面向中职教师的 AI 辅助教学设计分析与导学案生成系统”这一定位。系统围绕教师端准备流程展开，不建设学生端，不建设完整教务平台，也不把作业批阅描述为已实现能力。

推荐演示入口为 V2 页面，旧页面作为 legacy / 兼容页面保留。

## 架构概览

```text
Browser / 浏览器
        ↓
FastAPI + Jinja2
        ↓
Route handlers in app.main
        ↓
Business Services / 业务服务
        ↓
SQLAlchemy Models + Database / 数据库
        ↓
AI Services / DeepSeek Provider + Local Structured Drafts
```

当前 `backend/app/main.py` 仍集中承载 route 编排、模板渲染和部分表单处理。案例提交前不建议进行大规模 route 重构；后续可按模块逐步拆分。

## 主要模块

1. 课程管理：课程列表、课程创建、重命名、删除，以及 V2 课程中心。
2. 课程计划上传：上传 `.xlsx` 授课计划，解析 planned lessons，预览、确认并生成正式课次。
3. 正式课次：课程下的正式课次列表和课次详情，当前 `/courses/{course_id}/lessons` 作为 V2 过渡入口。
4. 课次资料：支持粘贴文本和上传 `txt`、`md`、`docx`、`pptx`、`xlsx`，不支持 `xls`、PDF、图片、扫描件和 OCR。
5. 课程资料整理 V2：`/ui-v2/lessons/{lesson_id}/materials-outline`。
6. 知识主干：基于课次资料生成知识主干，教师可编辑保存。
7. 备课参考建议：基于已整理内容提供教学准备参考。
8. 课前学情测试 V2：`/ui-v2/lessons/{lesson_id}/diagnostic-probe`，支持题卡预览、单题编辑/删除和学习通习题文件导出。
9. 学生导学案 V2：`/ui-v2/lessons/{lesson_id}/learning-guides`，支持全班通用导学案、巩固提升任务包、拓展探究任务包和 Markdown 下载。
10. AI 设置：`/ai/settings`，支持会话级 DeepSeek API Key 和模型选择。
11. 文件下载与导出：学习通习题文件导出、导学案和任务包 Markdown 下载。

## V2 与 Legacy 页面

V2 页面是当前推荐演示入口：

- `/ui-v2/courses`
- `/courses/{course_id}/lessons`
- `/ui-v2/lessons/{lesson_id}/materials-outline`
- `/ui-v2/lessons/{lesson_id}/diagnostic-probe`
- `/ui-v2/lessons/{lesson_id}/learning-guides`

旧模板仍被 route 或测试引用，承担兼容入口、测试入口和部分回退入口。本轮不移动旧模板，不创建旧 UI 归档目录。后续如完全切换到 V2，可再单独整理 legacy 模板。

## 数据库策略

当前开发和本地演示可使用 SQLite 文件；云端演示或私有部署可使用 MySQL。当前使用 SQLAlchemy `create_all` 初始化，暂未把数据库迁移作为本轮重点。

本轮文档收口不修改数据库结构，不新增表，不新增字段，不改变 `LessonDraft` 存储模型。

## AI 与生成边界

DeepSeek Provider 已接入，教师通过 `/ai/settings` 为当前会话设置 API Key 和模型。Key 只保存在服务端内存中，不写入数据库、不写入 cookie、不写入日志。

如果没有可用 API Key 或生成失败，系统可提供本地结构化草稿或 fallback，目的是保证教师能继续预览结构和编辑，不应包装成真实 AI 生成成果。

所有输出均为教师审阅用草稿。系统不自动发布给学生，不统计学生成绩，不评价教师能力，不替代教学设计。

## 作业批阅边界

作业批阅仅为预留功能和后续探索方向。未来可探索面向编程类、数据库类作业的规则测试与 AI 辅助评语草稿，结果仅供教师参考，需教师审核确认后使用。

当前不实现作业批阅后端、自动评分 route、学生端提交、自动发布评语或自动评价学生。

## 材料解析边界

当前已实现：

- 粘贴文本；
- `txt`；
- `md`；
- `docx` 段落和表格单元格基础提取；
- `pptx` 文本框和表格单元格文本提取；
- `xlsx` 资料文本提取；
- 多文件上传；
- 删除材料；
- 页面隐藏服务器绝对路径。

当前不实现：

- `xls`；
- PDF；
- 图片；
- 扫描件；
- OCR；
- 旧版 `.doc/.ppt`；
- 复杂图表、公式、动画或 SmartArt 的结构化还原。
