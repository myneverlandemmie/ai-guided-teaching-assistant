# AI Guided SQL Assessment Platform / 智学导评：AI 导学与 SQL 自动批阅系统

## 中文说明

本项目是“智学导评 V0.2”的工程仓库，用于建设一个面向中职数据库课程的 AI 导学与 SQL 自动批阅系统。

V0.2 版本聚焦数据库 / SQL / MySQL 入门教学，目标是在半个月内完成一个可演示、可部署、可用于案例申报的教学闭环系统。

核心流程：

1. 教师上传课程授课计划 Excel；
2. 系统解析授课计划并自动拆解课次；
3. 教师上传某一课次的教案或 PPT 文本；
4. AI 生成知识主干、小测题和分层导学案；
5. 学生查看导学案并提交 SQL 作业；
6. 系统自动批阅 SQL；
7. 教师复核并修正批阅结果；
8. 系统生成学生学习总结。

当前版本以 SQL / MySQL 为主线，Python 自动批阅与 OCR 拍照纠错作为后续版本扩展。

## English Summary

This repository contains the V0.2 implementation of an AI-guided SQL learning and assessment platform for vocational database courses.

The current version focuses on SQL / MySQL. Python grading and OCR-based screenshot correction are reserved for future versions.

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
- AI model / AI 模型：DeepSeek V4 Flash by default, V4 Pro as fallback / 默认 DeepSeek V4 Flash，V4 Pro 作为备用
- Deployment / 部署：Alibaba Cloud ECS for project demo; private deployment for real use / 项目演示用阿里云 ECS，真实使用建议私有部署
- Demo lesson / 演示课：SELECT + WHERE
- Documentation / 文档：Chinese-first bilingual documentation / 中文优先的双语文档

## 首次 Git 命令 / First Git Commands

```bash
git init
git add README.md .gitignore .env.example docs/ backend/ data/ deployment/ scripts/ tests/
git commit -m "chore: initialize bilingual project structure"
```
