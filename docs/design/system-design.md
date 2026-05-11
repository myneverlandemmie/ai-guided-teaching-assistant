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
AI API + SQL Grading Engine
```

## 主要模块 / Main Modules

1. User and class management / 用户与班级管理
2. Course plan import / 课程计划导入
3. Lesson management / 课次管理
4. AI generation service / AI 生成服务
5. Guidebook and quiz management / 导学案与小测管理
6. SQL assignment and grading / SQL 作业与批阅
7. Teacher review / 教师复核
8. Learning summary / 学习总结

## 数据库策略 / Database Strategy

- 云端演示与私有部署：MySQL；
- Windows 单机体验：SQLite 兼容模式；
- SQL 批阅：V0.2 基础功能先支持 SELECT、WHERE、AS 和简单计算字段；
- 完整 MySQL 题型作为后续增强。
