# WSL Development Setup / WSL 开发环境指南

## 中文说明

当前项目施工建议在 WSL / Ubuntu 中进行，Windows 负责浏览器测试、截图和录屏。

这样做的原因是：项目最终部署环境是 Linux 服务器，WSL 与阿里云 ECS 更接近，后续 FastAPI、MySQL、Nginx、部署脚本的环境差异更小。

## 推荐工作模式 / Recommended Workflow

```text
开发施工：WSL / Ubuntu
浏览器测试：Windows
案例演示：阿里云 ECS
教师本地体验：Windows 单机模式
学校正式使用：自有服务器 / 私有部署
```

## 初始化项目目录 / Initialize Project Folder

```bash
mkdir -p ~/projects
cd ~/projects
```

解压项目包后进入目录：

```bash
cd ~/projects/ai-guided-sql-assessment
git init
git add .
git commit -m "chore: initialize bilingual project structure"
```

## Windows 浏览器测试 / Test from Windows Browser

在 WSL 中启动服务：

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

在 Windows 浏览器中打开：

```text
http://127.0.0.1:8000
```
