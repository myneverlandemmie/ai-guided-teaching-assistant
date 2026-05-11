# Project Structure / 项目目录结构

## 中文说明

本项目采用英文目录名，便于 GitHub、Codex、部署脚本和工程协作；文档正文采用中文优先、英文补充的双语写法，便于同时服务教学案例申报和工程施工。

注意：Markdown 文件的一级标题采用“英文 / 中文”同一行写法，不再使用两个连续一级标题，避免 Typora 转 PDF 时因主题设置产生分页。

## English Summary

The project uses English directory names for GitHub, Codex, deployment scripts, and general engineering collaboration. Documentation is written in a Chinese-first bilingual style.

H1 titles should use one line with English / Chinese separated by a slash, rather than two consecutive H1 headings, to avoid unwanted page breaks when exporting PDFs with Typora.

```text
ai-guided-sql-assessment/
├── README.md
├── .gitignore
├── .env.example
├── docs/
│   ├── project/          # 项目总览 / Project overview
│   ├── requirements/     # 需求文档 / Requirements
│   ├── design/           # 系统设计 / System design
│   ├── prompts/          # AI 与 Codex 提示词 / Prompts
│   ├── decisions/        # 决策记录 / Decision records
│   ├── case-materials/   # 案例申报材料 / Case materials
│   ├── operations/       # 部署与运维 / Operations
│   └── demo/             # 演示课材料 / Demo lesson
├── backend/
│   ├── app/
│   │   ├── api/          # API 路由 / API routes
│   │   ├── core/         # 核心配置 / Core settings
│   │   ├── db/           # 数据库连接 / Database
│   │   ├── models/       # 数据模型 / ORM models
│   │   ├── schemas/      # 数据校验 / Schemas
│   │   ├── services/     # 业务服务 / Business services
│   │   │   ├── ai/       # AI 调用 / AI service
│   │   │   ├── course_plan/ # 授课计划解析 / Course plan parsing
│   │   │   └── grading/  # SQL 批阅 / SQL grading
│   │   ├── templates/    # 页面模板 / Templates
│   │   └── static/       # 静态资源 / Static files
│   ├── tests/
│   └── scripts/
├── data/
│   ├── sample-course-plans/
│   ├── sample-sql-assignments/
│   ├── demo-data/
│   └── uploads/
├── deployment/
│   ├── nginx/
│   ├── systemd/
│   └── docker/
├── scripts/
└── tests/
```

## 命名规则 / Naming Rules

- 目录和文件名使用英文。Use English directory and file names.
- 避免使用拼音命名。Avoid pinyin names.
- Markdown 文档文件使用 kebab-case，例如 `windows-quickstart.md`。
- Python 模块使用 snake_case，例如 `course_plan_parser.py`。
- 编码前以文档为准。Keep docs as the source of truth before coding.
