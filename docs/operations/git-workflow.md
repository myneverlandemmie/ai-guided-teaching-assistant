# Git Workflow for Beginner / Git 入门流程

## 中文说明

这个项目建议从一开始就使用 Git 管理。你不需要一开始就精通 Git，只要先掌握三个动作：

1. `git status`：查看当前状态；
2. `git add`：把文件放入暂存区；
3. `git commit`：保存一个版本。

GitHub 不是 Git 的起点。即使暂时没有 GitHub 仓库，本机 `git commit` 也会把版本保存在项目文件夹里的 `.git` 目录中，可以用于查看历史和回退版本。

## English Summary

This project should use Git from the beginning. Local commits are stored in the `.git` directory and can be used for history tracking and rollback.

## 初始化仓库 / Initialize the Repository

```bash
git init
git status
git add README.md .gitignore .env.example docs/ backend/ data/ deployment/ scripts/ tests/
git commit -m "chore: initialize bilingual project structure"
```

## 日常流程 / Daily Workflow

```bash
git status
git add .
git commit -m "docs: update project requirements"
```

## 让 Codex 写代码前 / Before Asking Codex to Code

```bash
git status
```

确认当前文档已经提交，避免 Codex 在未保存的文档基础上乱改。
