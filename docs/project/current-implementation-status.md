# Current Implementation Status / 当前实现状态

## Purpose / 文档目的

本文档记录当前代码已经真实实现的功能、尚未实现的范围、测试基线和下一步施工优先级。它用于避免后续文档、演示稿或 Codex 施工提示把计划功能误写成已完成功能。

## Implemented / 已实现

当前代码已经实现：

1. 授课计划上传；
2. Excel 课程计划解析；
3. planned lessons 预览；
4. planned lessons 确认 / 跳过；
5. 批量生成正式 Lesson；
6. 正式课次列表；
7. 正式课次详情页；
8. 课次材料添加；
9. 支持粘贴文本；
10. 支持 `.txt` / `.md`；
11. 支持 `.docx` 基础文本提取；
12. 支持 `.pptx` 实验性文本提取；
13. 支持多文件上传；
14. 支持删除课次材料；
15. 支持默认材料标题；
16. 页面不显示服务器绝对路径；
17. Mock AI 知识主干生成仅限测试 / 显式开发模式；
18. 知识主干可编辑和保存；
19. 知识主干生成前对学校、教师、班级等行政信息做基础过滤；
20. 会话级 DeepSeek API Key 设置、掩码显示和清除；
21. DeepSeek Provider 抽象；
22. 真实 DeepSeek 知识主干生成；
23. 没有 API Key 时阻止真实生成并提示先设置 Key；
24. 第 8.1 轮真实 AI 接入后的安全、稳定性与边界加固；
25. AI 设置页支持安全 `next` 返回来源页面；
26. 课程列表页提供“查看正式课次”入口；
27. AI 设置页支持教师选择当前会话 DeepSeek 模型；
28. DeepSeek 模型选项由 `DEEPSEEK_ALLOWED_MODELS` 配置，默认模型由 `DEEPSEEK_DEFAULT_MODEL` 配置；
29. 知识主干生成使用固定 Prompt 模板，包含课程思政与职业素养融入点、可测知识点与题型蓝图、补充内容建议和 AI 草稿声明；
30. 当前自动化测试最后一次运行结果为 `75 passed`。

## Current Development Context / 当前开发上下文

当前没有完整注册 / 登录功能。代码暂用 demo course / demo teacher 作为开发临时上下文，用于串联课程、课次、材料和知识主干流程。

该方式不是最终试用方式。V0.2 演示 / 部门内试用阶段应提供：

- 测试教师账号；
- 测试学生账号；
- 演示班级或测试班级；
- 教师创建测试班级的能力；
- 学生使用测试账号进入班级查看导学内容或提交演示作业的能力。

学生不需要填写 API Key。

## Not Implemented Yet / 尚未实现

当前尚未实现：

- 完整注册 / 登录；
- 测试教师账号、测试学生账号、测试班级；
- 真实 AI API 在导学案、小测题、总结和批阅链路中的接入；
- 真实导学案生成；
- 小测题生成；
- SQL 作业提交；
- SQL 自动批阅；
- 教师复核批阅结果；
- 学生反馈页；
- 学习总结；
- Python 批阅；
- OCR；
- PDF、图片、扫描件、旧版 `.doc/.ppt` 解析；
- 复杂 Vue / React 前端；
- 完整教务系统；
- 外部教师真实班级在项目方服务器上的大规模试用。

## AI Boundary / AI 边界

当前真实 AI 只接入“知识主干生成”。正式页面路径默认使用 DeepSeek Provider；如果当前会话没有 API Key，系统会提示教师先到 `/ai/settings` 设置 Key，不会静默 fallback 到 Mock。

Mock AI 仅用于自动化测试或显式设置 `AI_PROVIDER=mock` 的本地开发环境，不应保存为案例正式生成成果。

教师可在 `/ai/settings` 为当前浏览器会话选择知识主干生成模型。模型选择只保存在服务端内存中，不写数据库、不写 cookie、不写日志；清除 API Key 时会同时清除模型选择。模型列表来自 `DEEPSEEK_ALLOWED_MODELS`，默认模型来自 `DEEPSEEK_DEFAULT_MODEL`。如果 DeepSeek 官方模型名称变化，可由管理员修改环境变量后重启服务。

知识主干生成使用固定 Prompt 模板。AI 输出是教师审阅用草稿，不是自动定稿内容。模板要求输出课程思政与职业素养融入点，并要求内容有依据，严禁编造政策文件、政策原文、标准编号、真实企业案例或真实数据来源。模板中的“可测知识点与题型蓝图”只作为后续小测设计参考，不生成正式测评，且需包含至少 1 条课程思政 / 职业素养相关测试方向。“补充内容建议”仅为 AI 生成的参考方向，必须由教师人工筛选、修改和确认。

小测题生成、导学案生成、SQL 批阅、Python 批阅尚未接入真实 AI。后续真实导学案、小测题、学习总结等应接入真实 API，并继续坚持“AI 输出必须由教师编辑确认后使用”。

## V0.2 Round 8.1 Hardening / 第 8.1 轮安全加固

第 8.1 轮已完成真实 AI 接入后的安全、稳定性与边界加固：

- 共享脱敏逻辑扩展；
- Mock 与 DeepSeek 复用共享 sanitizer；
- DeepSeek prompt 构造前脱敏；
- DeepSeek HTTP 异常链脱敏，不保留可能携带 Authorization 的 httpx request；
- 知识主干生成路由使用 `run_in_threadpool`；
- 关键 POST 路由增加 same-origin 防护；
- `POST /ai/settings` 先校验 `Origin` / `Referer`，再读取 form；
- API Key 自动过期；
- API Key 容量上限；
- `session_key_store` 线程锁；
- `session_id` cookie 格式校验；
- 清除 API Key 时删除临时 session cookie；
- DeepSeek 模型 allowlist；
- 非法 `AI_PROVIDER` / timeout / model 安全处理；
- 轻量 prompt 材料选择；
- API Key 不入库测试增强；
- fake provider 测试不捕获完整 API Key。

当前 API Key 方案是 V0.2 本地开发 / 部门内试用级方案，不是生产级凭据管理系统。多 worker / 多实例部署时，单进程内存 Key 不共享。生产化如需多实例部署，应改用 Redis 等服务端临时存储，并配合加密、过期、轮换和审计机制。

## Material Parsing Boundary / 材料解析边界

当前材料解析支持：

- 粘贴文本；
- `.txt` / `.md`；
- `.docx` 段落和表格单元格基础提取；
- `.pptx` 文本框和表格单元格实验性提取。

当前材料解析不支持：

- PDF；
- 图片；
- 扫描件；
- OCR；
- 旧版 `.doc/.ppt`；
- 图片中的文字；
- 公式、复杂图表、动画或 SmartArt 的结构化还原。

## Privacy Baseline / 隐私基线

课次材料原文可保存在教师上传的材料记录中，但知识主干生成前会对学校、教研组、任课教师、授课班级、授课地点、授课日期、学号、姓名、手机号、身份证号等信息做基础过滤。

过滤只作用于生成知识主干时的输入，不修改原始 `LessonMaterial.content`。

公开仓库不得包含真实学生数据、真实教师 API Key、真实学校内部材料或未授权教案 / PPT 原文。

## Recommended Next Step / 下一步建议

最优先补齐：

1. 测试教师账号；
2. 测试学生账号；
3. 演示班级 / 测试班级；
4. 围绕真实知识主干生成继续补齐导学案、小测题和 SQL 作业演示闭环。

理由：当前课程计划、课次材料、知识主干已经形成教师端演示骨架，下一步应补齐可试用的账号与班级上下文，再扩展真实 AI 到导学案和小测题。
