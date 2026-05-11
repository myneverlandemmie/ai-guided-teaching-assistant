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
- 如教师愿意填写自己的 API Key，可切换为真实 AI 生成；
- 完整 MySQL 批阅与多人使用建议部署到自有服务器。

## 注意事项 / Notes

Windows 单机体验模式只适合少量演示账号，不建议用于正式班级长期教学。
