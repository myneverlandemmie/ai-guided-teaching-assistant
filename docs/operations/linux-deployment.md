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

## 后续待补充 / To Be Added

- Systemd service file
- Nginx reverse proxy config
- HTTPS certificate setup
- Database migration commands
- Backup and restore procedure
