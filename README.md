# AI Guided SQL Assessment Platform / 智学导评：AI 导学与 SQL 自动批阅系统

## 中文说明

本项目是“智学导评 V0.2”的工程仓库，用于建设一个面向中职数据库课程的 AI 导学与 SQL 自动批阅系统。

V0.2 版本聚焦数据库 / SQL / MySQL 入门教学，目标是在半个月内完成一个可演示、可部署、可用于案例申报的教学闭环系统。

截至当前文档基线，代码已经完成课程计划导入、课次确认、正式课次管理、课次材料上传与基础文本提取，以及会话级 API Key 管理 + DeepSeek Provider + 真实知识主干生成。SQL 自动批阅、真实 AI 导学案生成、小测题生成、学生端作业提交和完整登录注册仍属于后续施工内容。

核心流程：

1. 教师上传课程授课计划 Excel；
2. 系统解析授课计划并自动拆解课次；
3. 教师上传某一课次的教案或 PPT 文本；
4. 教师设置当前会话 DeepSeek API Key；
5. DeepSeek 生成知识主干初稿，教师可编辑保存；
6. 后续接入真实 AI 生成小测题和分层导学案；
7. 后续实现学生查看导学案并提交 SQL 作业；
8. 后续实现系统自动批阅 SQL；
9. 后续实现教师复核、学生反馈和学习总结。

当前版本以 SQL / MySQL 为主线，Python 自动批阅与 OCR 拍照纠错作为后续版本扩展。

## English Summary

This repository contains the V0.2 implementation of an AI-guided SQL learning and assessment platform for vocational database courses.

The current codebase has implemented course plan import, lesson confirmation, lesson material upload, basic `.docx` / `.pptx` text extraction, session-level API Key handling, and real DeepSeek-based knowledge outline generation. SQL grading, student assignment submission, guide generation, quiz generation, and full authentication are still planned work.

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
- AI model / AI 模型：DeepSeek V4 Pro by default, V4 Flash optional / 默认 DeepSeek V4 Pro，可切换 V4 Flash
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
- 知识主干编辑和保存；
- 知识主干生成前对学校、教师、班级等行政信息做基础过滤；
- 当前自动化测试最后一次运行结果为 `68 passed`。

当前未实现：

- 完整注册 / 登录；
- 教师账号、学生账号、班级管理；
- 导学案生成；
- 小测题生成；
- SQL 作业提交与自动批阅；
- Python 批阅；
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

环境变量示例：

```env
AI_PROVIDER=deepseek
DEEPSEEK_BASE_URL="https://api.deepseek.com"
DEEPSEEK_MODEL="deepseek-v4-pro"
AI_REQUEST_TIMEOUT_SECONDS=60
AI_SESSION_COOKIE_SECURE=false
AI_SESSION_KEY_IDLE_TIMEOUT_SECONDS=14400
AI_SESSION_KEY_MAX_ENTRIES=200
AI_PROMPT_MATERIAL_MAX_CHARS=12000
```

如需切换速度优先模型：

```env
DEEPSEEK_MODEL="deepseek-v4-flash"
```

测试环境不得真实请求 DeepSeek；应使用 monkeypatch / fake provider 或显式 `AI_PROVIDER=mock`。学生账号不需要 API Key。

配置说明：

- `AI_SESSION_COOKIE_SECURE=true`：公网 HTTPS 部署时启用，本地开发可保持 `false`；
- `AI_SESSION_KEY_IDLE_TIMEOUT_SECONDS=14400`：当前会话 API Key 空闲 4 小时后自动失效；
- `AI_SESSION_KEY_MAX_ENTRIES=200`：单进程内存最多保留 200 个会话 Key，超限会清理过期或最久未使用项；
- `AI_PROMPT_MATERIAL_MAX_CHARS=12000`：构造知识主干 prompt 时使用的材料字符上限；
- Mock 只用于自动化测试或显式 `AI_PROVIDER=mock` 的本地开发模式；
- 真实 AI 目前只接入知识主干生成；
- 当前方案是 V0.2 本地开发 / 部门内试用级临时方案，不是生产级凭据管理系统。

## 首次 Git 命令 / First Git Commands

```bash
git init
git add README.md .gitignore .env.example docs/ backend/ data/ deployment/ scripts/ tests/
git commit -m "chore: initialize bilingual project structure"
```
