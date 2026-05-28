# AI Guided Teaching Design Assistant / 智学导评：AI 辅助教学设计分析与导学案生成系统

## 中文说明

本项目是“智学导评 V0.2”的工程仓库，用于建设一个面向中职教师的 AI 辅助教学设计分析与导学案生成系统。

V0.2 版本聚焦“教师上传材料 → 系统提炼课程知识主干 → 生成课前学情测试 → 生成学生导学案 → 教师编辑确认后用于课堂”的演示闭环。系统不是 AI 自动备课系统，也不是一键生成完整教案或自动批阅作业的平台。

截至当前文档基线，代码已经完成课程计划导入、课次确认、正式课次管理、课次材料上传与基础文本提取、会话级 API Key 管理、DeepSeek Provider、真实知识主干生成、课前学情测试草稿、学生导学案草稿、学习通题库模板导出和导学案 Markdown 下载。自动批阅、学生端、学习通 API、完整登录注册仍属于规划中或实验性方向。

核心流程：

1. 教师上传课程授课计划 Excel；
2. 系统解析授课计划并自动拆解课次；
3. 教师上传某一课次的教案或 PPT 文本；
4. 教师设置当前会话 DeepSeek API Key；
5. DeepSeek 生成课程知识主干初稿，教师可编辑保存；
6. 系统基于知识主干生成课前学情测试草稿；
7. 系统生成学生导学案草稿；
8. 教师查看、编辑、确认后用于课堂；
9. 学习通题库模板导出和 Markdown 下载作为辅助输出。

自动批阅相关能力统一作为编程类课程后续实验性方向，不作为 V0.2 当前核心主线。

## English Summary

This repository contains the V0.2 implementation of an AI-assisted teaching design analysis and learning-guide generation system for vocational teachers.

The current codebase has implemented course plan import, lesson confirmation, lesson material upload, basic `.docx` / `.pptx` text extraction, session-level API Key handling, real DeepSeek-based knowledge outline generation, diagnostic probe drafts, student learning guide drafts, Chaoxing import-template export, and Markdown download. Auto grading, student-side workflows, external learning-platform APIs, and full authentication are still planned work.

## 三层使用模式 / Three Usage Modes

本项目不建议让外部教师直接带真实学生使用项目方演示服务器。推荐采用三层模式：

1. 云端演示模式：项目方阿里云 ECS 仅用于案例展示和视频录制；
2. Windows 单机体验模式：普通教师可在本机体验核心流程；
3. Linux / 私有服务器部署模式：学校或教师可部署到自有服务器，数据与 API Key 自主管理。

This project does not encourage external teachers to use the project owner's demo server with real student data. Instead, it provides three modes:

1. Cloud demo mode for case demonstration only;
2. Windows local demo mode for low-barrier teacher trial;
3. Linux / private server deployment for real classroom use.

## 主要技术决策 / Main Technical Decisions

- Backend / 后端：FastAPI
- Frontend / 前端：simple server-rendered pages first / 优先使用简单模板页面
- Database / 数据库：MySQL for deployment, SQLite-compatible demo mode for Windows trial / 部署使用 MySQL，Windows 体验模式支持 SQLite 兼容演示
- AI model / AI 模型：DeepSeek V4 Flash by default, V4 Pro optional / 默认 DeepSeek V4 Flash，可选择 V4 Pro
- Deployment / 部署：Alibaba Cloud ECS for project demo; private deployment for real use / 项目演示用阿里云 ECS，真实使用建议私有部署
- Demo lesson / 演示课：SELECT + WHERE
- Documentation / 文档：Chinese-first bilingual documentation / 中文优先的双语文档

## Current Baseline / 当前实现基线

已实现：

- `.xlsx` 授课计划上传；
- Excel 课程计划解析，样例计划可解析出 28 个 planned lessons；
- planned lessons 预览；
- planned lessons 确认 / 跳过；
- 批量生成正式 Lesson；
- 正式课次列表；
- 正式课次详情页；
- 课次材料添加；
- 粘贴文本材料；
- `.txt` / `.md` 材料读取；
- `.docx` 基础文本提取，包括段落和表格单元格；
- `.pptx` 实验性文本提取，包括文本框和表格文本；
- 多文件上传；
- 删除课次材料；
- 默认材料标题；
- 教师页面不显示服务器绝对路径；
- Mock AI 知识主干生成，仅用于测试或显式开发模式；
- 会话级 DeepSeek API Key 设置、掩码显示和清除；
- DeepSeek Provider；
- 真实 DeepSeek 知识主干生成；
- AI 设置页支持教师选择当前会话 DeepSeek 模型；
- 知识主干生成使用固定 Prompt 模板，包含课程思政与职业素养融入点、可测知识点与题型蓝图、补充内容建议和 AI 草稿声明；
- 知识主干编辑和保存；
- 知识主干生成前对学校、教师、班级等行政信息做基础过滤；
- 课前学情测试草稿生成；
- 学生导学案草稿生成；
- 学习通题库模板导出；
- 导学案 Markdown 下载；
- 教师编辑保存草稿；
- 课次任务面板。

当前未实现：

- 完整注册 / 登录；
- 教师账号、学生账号、班级管理；
- 真实 API 生成导学案；
- SQL 作业提交与自动批阅；
- Python 批阅；
- 学生端；
- 学习通 API；
- 统计分析；
- OCR、PDF、图片或扫描件解析；
- 复杂 Vue / React 前端。

当前开发阶段暂用 demo course / demo teacher 作为临时上下文，不作为最终试用方式。

## Trial and Account Strategy / 试用账号策略

开发阶段：

- 暂用 demo course / demo teacher；
- 不作为最终部门内试用或外部演示方式。

V0.2 演示 / 部门内试用阶段：

- 提供测试教师账号；
- 提供测试学生账号；
- 第一个班级使用“演示班级”或“测试班级”；
- 教师可创建测试班级；
- 学生使用测试账号进入班级查看导学内容或提交演示作业；
- 学生不需要填写 API Key。

API Key 策略：

- 教师使用自己的 API Key；
- 平台不提供公共 Token；
- 平台不做 Token 转售；
- API Key 不应明文入库、写入日志或提交到 Git；
- API Key 不能只存 hash，因为 hash 无法还原，不能用于真实 API 调用；
- V0.2 已实现“会话级临时 API Key”，浏览器 cookie 只保存 `session_id`，服务端内存临时保存 `session_id -> api_key`，清除 / 服务重启后失效；
- 若后续需要长期保存 Key，应另行设计加密存储方案，不在当前阶段实现。

## AI Settings / AI 设置

开发或演示时，教师进入：

```text
/ai/settings
```

填写自己的 DeepSeek API Key。页面只显示掩码，例如 `sk-****abcd`，不会回显完整 Key。

教师需要自行准备 DeepSeek API Key，并确认 DeepSeek 账户有可用余额。`.env.example` 不包含真实 Key，不要把真实 Key 写入 `.env.example`、日志或 Git。

教师可在 AI 设置页选择知识主干生成使用的 DeepSeek 模型。模型选择是当前浏览器会话级设置，只保存在服务端内存中，不写入数据库、不写入 cookie、不写入日志；清除 API Key 时会同时清除模型选择。

环境变量示例：

```env
AI_PROVIDER=deepseek
DEEPSEEK_BASE_URL="https://api.deepseek.com"
DEEPSEEK_ALLOWED_MODELS=deepseek-v4-flash,deepseek-v4-pro
DEEPSEEK_DEFAULT_MODEL=deepseek-v4-flash
AI_REQUEST_TIMEOUT_SECONDS=60
AI_SESSION_COOKIE_SECURE=false
AI_SESSION_KEY_IDLE_TIMEOUT_SECONDS=14400
AI_SESSION_KEY_MAX_ENTRIES=200
AI_PROMPT_MATERIAL_MAX_CHARS=12000
```

如 DeepSeek 官方模型名称变化，管理员可更新 `DEEPSEEK_ALLOWED_MODELS` 和 `DEEPSEEK_DEFAULT_MODEL` 后重启服务。`/ai/settings` 页面只显示配置说明、建议配置路径和官方文档链接，不读取、不打开、不下载、不展示真实 `.env` 内容。本地开发通常在项目根目录 `.env` 中配置，示例变量见 `.env.example`。

测试环境不得真实请求 DeepSeek；应使用 monkeypatch / fake provider 或显式 `AI_PROVIDER=mock`。学生账号不需要 API Key。

配置说明：

- `DEEPSEEK_ALLOWED_MODELS`：允许教师在 AI 设置页选择的 DeepSeek 模型，逗号分隔；
- `DEEPSEEK_DEFAULT_MODEL`：默认模型，必须属于允许模型列表，否则回退到安全默认值；
- `deepseek-v4-pro`：更适合知识主干生成、课程思政与职业素养融入点、正式案例展示和争议样本复核；
- `deepseek-v4-flash`：更适合日常快速预览、批量反馈初稿、调试 Prompt 和验证页面流程；
- 知识主干正式演示建议优先使用 `deepseek-v4-pro`，批量反馈或调试建议优先使用 `deepseek-v4-flash`；
- `AI_SESSION_COOKIE_SECURE=true`：公网 HTTPS 部署时启用，本地开发可保持 `false`；
- `AI_SESSION_KEY_IDLE_TIMEOUT_SECONDS=14400`：当前会话 API Key 空闲 4 小时后自动失效；
- `AI_SESSION_KEY_MAX_ENTRIES=200`：单进程内存最多保留 200 个会话 Key，超限会清理过期或最久未使用项；
- `AI_PROMPT_MATERIAL_MAX_CHARS=12000`：构造知识主干 prompt 时使用的材料字符上限；
- Mock 只用于自动化测试或显式 `AI_PROVIDER=mock` 的本地开发模式；
- 真实 AI 目前只接入知识主干生成；
- 当前方案是 V0.2 本地开发 / 部门内试用级临时方案，不是生产级凭据管理系统。

知识主干生成使用固定 Prompt 模板。输出是教师审阅用草稿，不是自动定稿内容；其中包含课程思政与职业素养融入点、可测知识点与题型蓝图、补充内容建议和 AI 草稿声明。课程思政内容必须有依据，严禁编造政策文件、政策原文、标准编号、真实企业案例或真实数据来源。“可测知识点与题型蓝图”只作为后续小测设计参考，不生成正式测评，且需包含至少 1 条课程思政 / 职业素养相关测试方向。“补充内容建议”仅为参考方向，必须由教师人工筛选、修改和确认。

## 首次 Git 命令 / First Git Commands

```bash
git init
git add README.md .gitignore .env.example docs/ backend/ data/ deployment/ scripts/ tests/
git commit -m "chore: initialize bilingual project structure"
```
