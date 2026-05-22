# Windows Quickstart / Windows 单机体验指南

## 中文说明

Windows 单机体验模式面向普通教师，用于低门槛验证系统核心流程。它不是正式生产部署方案，而是“先看懂、先跑起来、先验证”的体验路径。

## 目标 / Goals

- 不要求安装 WSL2；
- 不要求掌握 Linux 运维；
- 使用浏览器访问本地系统；
- 可以创建演示班级和演示学生；
- 可以上传授课计划；
- 可以体验 Mock AI 生成流程；
- 可以完成 SELECT + WHERE 基础 SQL 批阅演示。

当前代码已支持的本地体验内容：

- 课程列表和 demo course；
- `.xlsx` 授课计划上传；
- 课程计划解析和 planned lessons 预览；
- planned lessons 确认 / 跳过；
- 生成正式课次；
- 正式课次列表和详情页；
- 粘贴或上传课次材料；
- `.txt` / `.md`；
- `.docx` 基础文本提取；
- `.pptx` 实验性文本提取；
- 多文件上传和删除材料；
- Mock AI 知识主干生成、编辑和保存。

当前尚不支持完整登录、测试教师 / 学生账号、学生端 SQL 作业提交和 SQL 自动批阅。

## 预期启动方式 / Expected Startup

后续版本应提供：

```bat
run-windows.bat
```

教师双击后启动本地服务，然后在浏览器打开：

```text
http://127.0.0.1:8000
```

## 简化策略 / Simplification Strategy

- 本地体验模式可使用 SQLite 存储系统数据；
- SQL 批阅使用 SQLite 兼容模式；
- Mock AI 模式可避免 API 调用费用；
- 如后续接入真实 AI，教师应填写自己的 API Key；
- V0.2 推荐会话级临时 API Key，退出 / 清除 / 服务重启后失效；
- API Key 不应明文入库、写入日志或提交到 Git；
- 完整 MySQL 批阅与多人使用建议部署到自有服务器。

## 注意事项 / Notes

Windows 单机体验模式只适合少量演示账号，不建议用于正式班级长期教学。

当前开发阶段使用 demo course / demo teacher 作为临时上下文。V0.2 演示 / 部门内试用阶段应提供测试教师账号、测试学生账号和演示班级 / 测试班级。学生不需要填写 API Key。
