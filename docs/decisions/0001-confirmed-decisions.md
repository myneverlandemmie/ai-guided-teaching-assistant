# Decision Record 0001 / 决策记录 0001

Date / 日期：2026-05-11

## 中文决策记录

1. V0.2 后端框架使用 FastAPI。
2. 前端优先采用简单模板页面，不使用复杂前端工程。
3. 第一节演示课选择 SELECT + WHERE。
4. 高阶练习可以加入 AS 字段别名和简单计算字段 / 函数。
5. 功能按正常班级与学生账号逻辑实现，但第一个班级命名为“演示班级”，并创建演示学生账号。
6. 默认使用 DeepSeek V4 Flash，复杂生成、最终润色或失败重试时使用 DeepSeek V4 Pro。
7. 项目方阿里云 ECS 只用于案例演示，不承接外部真实班级大规模试用。
8. 真实课堂使用应支持教师或学校私有部署，由使用方自行管理学生数据与 API Key。
9. Windows 单机体验模式进入传播设计，用于普通教师本地验证核心流程。
10. 当前施工环境仍建议使用 WSL / Ubuntu，Windows 负责浏览器测试、截图与录屏。
11. 有域名和证书时优先使用 HTTPS；如时间不足，演示阶段可先使用 IP:端口。
12. 案例视频按 8 分钟以内准备。
13. Python 自动批阅和 OCR 拍照纠错暂不进入 V0.2 主线。
14. 文档采用英文目录名 + 中文优先双语正文。
15. Markdown 文档一级标题采用“English / 中文”同一行，避免 Typora 转 PDF 时分页异常。

## English Summary

1. Use FastAPI as the backend framework.
2. Use simple server-rendered pages first.
3. Use SELECT + WHERE as the first demo lesson.
4. Advanced exercises may include AS aliases and simple calculated fields / functions.
5. Implement normal class and student account logic, with a first demo class and demo student accounts.
6. Use DeepSeek V4 Flash as the default model and DeepSeek V4 Pro for complex generation, final polishing, or fallback.
7. The project owner's Alibaba Cloud ECS is for case demonstration only, not for large-scale external classroom trials.
8. Real classroom use should be based on private deployment, with student data and API keys controlled by the teacher or school.
9. Windows local demo mode is included for low-barrier teacher trial.
10. Development should still use WSL / Ubuntu, while Windows is used for browser testing, screenshots, and recording.
11. Prefer HTTPS when possible; otherwise IP:port is acceptable for the demo stage.
12. Keep the case video within 8 minutes.
13. Keep Python grading and OCR correction out of the V0.2 core scope.
14. Use English directory names with Chinese-first bilingual documentation.
15. Use one H1 title with English / Chinese separated by a slash to avoid unwanted PDF page breaks in Typora.
