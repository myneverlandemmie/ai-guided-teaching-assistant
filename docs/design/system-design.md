# System Design / 系统设计

## 中文说明

V0.2 采用轻量化 Web 架构，以 FastAPI 为后端核心。系统优先完成“课次材料 → 课程知识主干 → 课前学情测试 → 学生导学案 → 教师编辑确认”的教学设计辅助闭环，不追求复杂前端和大型平台化功能。

## English Summary

V0.2 uses a lightweight web architecture with FastAPI as the backend core. The goal is to complete an AI-assisted teaching design analysis and learning-guide generation workflow rather than building a complex frontend or a large platform.

## 架构概览 / Architecture Overview

```text
Browser / 浏览器
        ↓
FastAPI + Jinja2
        ↓
Business Services / 业务服务
        ↓
Database / 数据库
        ↓
AI Services / Knowledge Outline + Draft Generation
```

## 主要模块 / Main Modules

1. Course plan import / 课程计划导入：已实现。
2. Lesson management / 课次管理：已实现 planned lessons 确认、正式课次列表和详情页。
3. Lesson material management / 课次材料管理：已实现粘贴文本、`.txt` / `.md`、`.docx`、实验性 `.pptx`、多文件上传、删除和默认标题。
4. Knowledge outline / 课程知识主干：已实现真实 DeepSeek 生成、Mock 测试模式、编辑、保存和基础行政信息过滤。
5. User and class management / 用户与班级管理：待实现。
6. Diagnostic probe / 课前学情测试：已实现教师端草稿和学习通题库模板导出。
7. Student learning guide / 学生导学案：已实现本地结构化草稿、教师编辑保存和 Markdown 下载。
8. Automatic grading / 自动批阅：规划中 / 编程类课程实验性方向。
9. Student-side workflow / 学生端：待实现。
10. Learning platform integration / 学习平台 API：待实现。

## Current Runtime Context / 当前运行上下文

当前开发阶段使用 demo course / demo teacher 作为临时上下文，目的是串联课程计划、课次、材料、知识主干、课前学情测试和学生导学案页面。该方式不是最终试用方式。

V0.2 演示 / 部门内试用阶段应补齐：

- 测试教师账号；
- 测试学生账号；
- 演示班级 / 测试班级；
- 教师创建测试班级；
- 学生使用测试账号进入班级查看导学内容或提交演示作业。

学生不需要填写 API Key。

## AI Boundary / AI 边界

当前真实 AI 只接入课程知识主干生成。Mock 输出仅用于自动化测试或显式开发模式，不可作为最终案例中的真实 AI 生成成果。

当前课前学情测试和学生导学案由本地结构化草稿生成，不调用真实 API。后续如接入真实导学案或其他生成链路，仍必须坚持“AI 输出由教师审核、修改、确认后使用”。教师使用自己的 API Key，平台不提供公共 Token，不做 Token 转售。

V0.2 推荐会话级临时 API Key：

- 教师登录后临时输入；
- 服务端内存保存；
- 退出 / 清除 / 服务重启后失效；
- 不明文入库；
- 不写日志；
- 不提交到 Git。

## 数据库策略 / Database Strategy

- 云端演示与私有部署：MySQL；
- Windows 单机体验：SQLite 兼容模式；
- 当前开发和测试可使用 SQLite；
- 当前使用 SQLAlchemy `create_all` 初始化，暂未引入 Alembic；
- 自动批阅：规划中 / 实验性方向，不作为当前核心主线；
- SQL、Python、C 等编程类课程评分后续应按受控环境分别设计，不在当前系统设计主线中展开。

## Material Parsing Boundary / 材料解析边界

当前已实现：

- 粘贴文本；
- `.txt` / `.md`；
- `.docx` 段落和表格单元格基础提取；
- `.pptx` 文本框和表格单元格实验性提取；
- 多文件上传；
- 删除材料；
- 页面隐藏服务器绝对路径。

当前不实现：

- OCR；
- PDF 解析；
- 图片识别；
- 扫描件识别；
- 旧版 `.doc/.ppt` 解析；
- 复杂 Vue / React 前端。
