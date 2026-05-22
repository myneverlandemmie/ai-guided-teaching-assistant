# Open Source Release Plan / 开源发布与脱敏说明

## 中文说明

本项目建议提供 GitHub 开源仓库和本地源码压缩包，体现案例的可复制、可修改、可传播价值。

但开源必须脱敏。公开仓库只放源码、文档、演示数据和部署说明，不放真实学生数据、API Key 或学校内部资料。

## 公开仓库可以包含 / Allowed in Public Repository

- README
- LICENSE
- `.env.example`
- docs
- backend
- deployment
- scripts
- tests
- demo course plan
- demo class data
- fictional student accounts
- generated sample `.docx` / `.pptx` files used only in tests

## 公开仓库不得包含 / Not Allowed in Public Repository

- 真实学生姓名 / Real student names
- 真实成绩 / Real grades
- 真实班级名单 / Real class lists
- API Key
- `.env`
- 服务器 IP、密码或密钥 / Server IP, passwords, or private keys
- 学校内部未公开资料 / Internal school materials
- 未授权 PPT 或教案原文 / Unauthorized PPT or lesson plan content
- 运行时上传文件 / Runtime uploaded files
- 本地 SQLite / MySQL 数据库文件
- 真实教师 API Key 或 Token

## Current Baseline for Release Notes / 当前发布说明基线

公开发布说明应真实写明当前已完成：

- 授课计划上传与 Excel 解析；
- planned lessons 预览、确认、跳过；
- 批量生成正式课次；
- 正式课次列表和详情页；
- 课次材料粘贴 / 上传；
- `.txt` / `.md`；
- `.docx` 基础文本提取；
- `.pptx` 实验性文本提取；
- 多文件上传；
- 删除课次材料；
- 默认材料标题；
- 页面不显示服务器绝对路径；
- Mock AI 知识主干生成；
- 知识主干编辑和保存；
- 知识主干生成前对学校、教师、班级等行政信息做基础过滤。

公开发布说明也必须真实写明当前未完成：

- 完整注册 / 登录；
- 测试教师账号、测试学生账号、测试班级；
- 真实 AI API 接入；
- 导学案生成；
- 小测题生成；
- SQL 作业提交和自动批阅；
- Python 批阅；
- OCR；
- PDF、图片、扫描件、旧版 `.doc/.ppt` 解析；
- 复杂 Vue / React 前端。

Mock AI 知识主干只能描述为流程演示，不得描述为最终案例中的真实 AI 生成成果。

## Trial Data and Account Boundary / 试用数据与账号边界

V0.2 演示 / 部门内试用阶段可以提供测试教师账号、测试学生账号和“演示班级 / 测试班级”。账号、班级和学生数据必须使用虚构或脱敏数据。

学生不需要填写 API Key。教师如需真实 AI 功能，应使用自己的 API Key。平台不提供公共 Token，不做 Token 转售。API Key 不得明文入库、写入日志或提交到 Git。

## 推荐许可证 / Recommended License

建议使用 MIT License，便于其他教师复制、修改和二次开发。

MIT License is recommended for easy reuse and modification by other teachers.
