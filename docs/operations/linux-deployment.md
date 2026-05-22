# Linux Deployment / Linux 与私有服务器部署指南

## 中文说明

真实课堂使用建议由教师或学校部署到自有服务器。这样学生数据、API Key、课程材料均由使用方自行控制，避免把真实学生数据交给不明第三方服务器。

## 推荐环境 / Recommended Environment

- Ubuntu / Debian / Alibaba Cloud ECS
- Python 3.11+
- FastAPI
- MySQL
- Nginx
- Optional HTTPS
- User-managed API key

## 部署边界 / Deployment Boundary

项目方演示服务器只用于案例展示，不承接外部真实班级大规模试用。

The project owner's demo server is for case demonstration only and should not host large-scale external real classroom use.

当前代码可部署演示的功能包括：

- 授课计划上传与解析；
- planned lessons 预览、确认和跳过；
- 批量生成正式课次；
- 正式课次列表和详情页；
- 课次材料粘贴 / 上传；
- `.txt` / `.md` / `.docx` / `.pptx` 基础文本提取；
- Mock AI 知识主干生成、编辑和保存。

当前部署不应承诺：

- 完整注册 / 登录；
- 完整学生端；
- 真实 AI 导学案生成；
- SQL 自动批阅；
- OCR；
- PDF、图片、扫描件或旧版 `.doc/.ppt` 解析；
- 外部教师真实班级的大规模试用。

## Account and API Key Boundary / 账号与 API Key 边界

V0.2 演示 / 部门内试用阶段应提供测试教师账号、测试学生账号和演示班级 / 测试班级。当前开发阶段的 demo course / demo teacher 不是最终试用方式。

真实 AI API Key 策略：

- 教师使用自己的 API Key；
- 平台不提供公共 Token；
- 平台不做 Token 转售；
- 学生不需要填写 API Key；
- API Key 不应明文入库；
- API Key 不应写入日志；
- API Key 不应提交到 Git；
- API Key 不能只存 hash，因为 hash 无法还原，不能用于真实 API 调用；
- V0.2 推荐“教师登录后，会话级临时 API Key”，服务端内存临时保存，退出 / 清除 / 服务重启后失效；
- 若需长期保存 Key，应另行设计加密存储方案，不在当前阶段实现。

## 后续待补充 / To Be Added

- Systemd service file
- Nginx reverse proxy config
- HTTPS certificate setup
- Database migration commands
- Test teacher / student account initialization
- Session-level API Key input and clearing
- Backup and restore procedure
