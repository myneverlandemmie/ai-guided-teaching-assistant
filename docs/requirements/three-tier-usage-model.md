# Three-Tier Usage Model / 三层使用模式

## 中文说明

本项目推广时不建议让其他教师直接带真实学生使用项目方服务器。教师对学生数据安全负有责任，真实使用应优先采用本地体验或私有部署。

## English Summary

The project should not be promoted by asking external teachers to use the project owner's server with real student data. Real classroom use should prefer local trial or private deployment.

## A 层：云端演示模式 / Mode A: Cloud Demo

项目方在阿里云 ECS 上部署一套演示系统，用于案例视频录制、评审展示和功能说明。

边界：

- 只使用演示班级、演示学生和脱敏数据；
- 不承接外部真实学生大规模试用；
- 不对外承诺长期生产服务；
- API Key 由项目方控制，不写入公开仓库。

## B 层：Windows 单机体验模式 / Mode B: Windows Local Demo

普通教师可以在自己的 Windows 电脑上本地运行系统，创建演示班级和少量学生账号，验证核心流程。

目标：

- 不要求安装 WSL2；
- 不要求理解 Linux 运维；
- 可通过 `run-windows.bat` 启动；
- 浏览器访问 `http://127.0.0.1:8000`；
- 支持课程计划上传、课次拆解、Mock AI 生成、SQL 基础批阅演示。

简化策略：

- 系统业务数据可使用 SQLite；
- SQL 批阅使用 SQLite 兼容模式；
- 覆盖 SELECT、WHERE、AS、简单计算字段等基础场景；
- 完整 MySQL 批阅放在服务器部署模式；
- AI 调用默认使用教师自己的 API Key；
- 无 API Key 时可用 Mock AI 模式体验流程。

## C 层：Linux / 私有服务器部署模式 / Mode C: Linux or Private Server Deployment

真实课堂使用建议部署到教师或学校自有服务器。

推荐环境：

- Ubuntu / Debian / 阿里云 ECS；
- FastAPI + MySQL；
- Nginx 反向代理；
- 可选 HTTPS；
- 使用方自行配置 API Key；
- 学生数据保存在使用方自己的服务器上。
