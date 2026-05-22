# System Design / 系统设计

## 中文说明

V0.2 采用轻量化 Web 架构，以 FastAPI 为后端核心。系统优先完成教学流程闭环，不追求复杂前端和大型平台化功能。

## English Summary

V0.2 uses a lightweight web architecture with FastAPI as the backend core. The goal is to complete the teaching workflow rather than building a complex frontend or a large platform.

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
Mock AI / Future Real AI + Future SQL Grading Engine
```

## 主要模块 / Main Modules

1. Course plan import / 课程计划导入：已实现。
2. Lesson management / 课次管理：已实现 planned lessons 确认、正式课次列表和详情页。
3. Lesson material management / 课次材料管理：已实现粘贴文本、`.txt` / `.md`、`.docx`、实验性 `.pptx`、多文件上传、删除和默认标题。
4. Mock AI knowledge outline / Mock AI 知识主干：已实现生成、编辑、保存和基础行政信息过滤。
5. User and class management / 用户与班级管理：待实现。
6. Real AI generation service / 真实 AI 生成服务：待实现。
7. Guidebook and quiz management / 导学案与小测管理：待实现。
8. SQL assignment and grading / SQL 作业与批阅：待实现。
9. Teacher review / 教师复核：待实现。
10. Learning summary / 学习总结：待实现。

## Current Runtime Context / 当前运行上下文

当前开发阶段使用 demo course / demo teacher 作为临时上下文，目的是串联课程计划、课次、材料和知识主干页面。该方式不是最终试用方式。

V0.2 演示 / 部门内试用阶段应补齐：

- 测试教师账号；
- 测试学生账号；
- 演示班级 / 测试班级；
- 教师创建测试班级；
- 学生使用测试账号进入班级查看导学内容或提交演示作业。

学生不需要填写 API Key。

## AI Boundary / AI 边界

当前知识主干由 Mock AI 规则生成，不调用真实 API。Mock 输出用于验证流程，不可作为最终案例中的真实 AI 生成成果。

后续真实导学案、小测题、学习总结应接入真实 API。教师使用自己的 API Key，平台不提供公共 Token，不做 Token 转售。

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
- SQL 批阅：后续 V0.2 基础功能先支持 SELECT、WHERE、AS 和简单计算字段；
- 完整 MySQL 题型作为后续增强。

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
