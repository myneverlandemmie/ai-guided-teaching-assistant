# Codex Build Prompt / Codex 施工提示词

## 中文说明

请你帮助构建“智学导评 V0.2：AI 辅助教学设计分析与导学案生成系统”。

当前版本的目标是完成一个面向中职教师的 AI 辅助教学设计分析与导学案生成闭环，不要扩展到完整自动批阅、学生端、OCR 拍照纠错或复杂前端工程。

## English Instruction

You are helping build the V0.2 version of an AI-assisted teaching design analysis and learning-guide generation system for vocational teachers.

The current version should focus on the teacher-side workflow from lesson materials to knowledge outline, diagnostic probe, and student learning guide. Do not expand the project into full grading, OCR screenshot correction, student-side workflows, or complex frontend engineering.

## 硬性约束 / Hard Constraints

1. Use FastAPI as the backend framework.  
   后端框架使用 FastAPI。

2. Use simple server-rendered pages first.  
   前端优先使用简单模板页面。

3. Keep all code understandable for teaching.  
   代码要便于教学理解。

4. Add Chinese comments for important business logic.  
   关键业务逻辑添加中文注释。

5. Update docs when decisions or behavior change.  
   决策或行为变化时同步更新文档。

6. Make small, verifiable commits.  
   每次提交保持小步、可验证。

7. Do not implement Python grading or OCR in V0.2.  
   V0.2 不实现 Python 自动批阅和 OCR 拍照纠错。

8. Do not design the project owner's demo server as a public production service.  
   不要把项目方演示服务器设计成对外生产服务。

9. Provide Windows local demo support as a low-barrier trial mode.  
   预留 Windows 单机体验支持，降低普通教师试用门槛。

10. Support Mock AI mode to avoid unnecessary API costs during local trials.  
    支持 Mock AI 模式，避免本地体验时产生不必要 API 成本。

## 第一阶段施工目标 / First Construction Target

历史第一阶段目标是实现课程计划导入模块。当前该阶段已完成，并已继续完成到课程知识主干、课前学情测试和学生导学案草稿生成。

后续 Codex 施工应基于当前实现状态继续，不要重复施工已完成模块。

### 功能要求 / Required Behavior

1. Upload `.xlsx` course plan.  
   上传 `.xlsx` 授课计划。

2. Parse columns including week, lesson number, hours, teaching content, tools, homework, and notes.  
   解析周次、课次、学时、教学内容、教学用具、作业和备注。

3. Extract lesson code and lesson title from teaching content when possible.  
   尽量从教学内容中提取课次编码和标题。

4. Show a preview table before saving.  
   保存前展示解析预览表。

5. Let the teacher confirm, edit, or skip planned lessons.  
   支持教师确认、编辑或跳过课次。

6. Save confirmed lessons into the database.  
   将确认后的课次写入数据库。

## 每轮汇报格式 / Report Format After Each Round

1. Files added or modified / 新增或修改的文件
2. What works now / 当前已实现内容
3. How to test / 测试方法
4. Known limitations / 已知限制
5. Next recommended step / 下一步建议

## Current Baseline for Future Codex Rounds / 后续施工当前基线

当前已实现：

- 授课计划上传；
- Excel 课程计划解析；
- planned lessons 预览；
- planned lessons 确认 / 跳过；
- 批量生成正式 Lesson；
- 正式课次列表；
- 正式课次详情页；
- 课次材料添加；
- 粘贴文本；
- `.txt` / `.md`；
- `.docx` 基础文本提取；
- `.pptx` 实验性文本提取；
- 多文件上传；
- 删除课次材料；
- 默认材料标题；
- 页面不显示服务器绝对路径；
- Mock AI 知识主干生成；
- 知识主干可编辑和保存；
- 知识主干生成前对学校、教师、班级等行政信息做基础过滤；
- 课前学情测试草稿生成；
- 学生导学案草稿生成；
- 学习通题库模板导出；
- 导学案 Markdown 下载；
- 课次任务面板。

测试状态以当前自动化测试结果为准。

当前未实现，后续施工不得误称已完成：

- 完整注册 / 登录；
- 测试教师账号、测试学生账号、测试班级；
- 真实 API 生成导学案；
- 自动批阅；
- 学生端；
- 学习通 API；
- 统计分析；
- SQL 作业提交和自动批阅；
- Python 批阅；
- OCR；
- PDF、图片、扫描件、旧版 `.doc/.ppt` 解析；
- 复杂 Vue / React 前端。

## Account and API Key Rules / 账号与 API Key 规则

当前开发阶段暂用 demo course / demo teacher，不作为最终试用方式。

V0.2 演示 / 部门内试用阶段必须提供：

- 测试教师账号；
- 测试学生账号；
- 演示班级 / 测试班级；
- 学生无需填写 API Key。

真实 API Key 策略：

- 教师使用自己的 API Key；
- 平台不提供公共 Token；
- 平台不做 Token 转售；
- API Key 不应明文入库；
- API Key 不应写入日志；
- API Key 不应提交到 Git；
- API Key 不能只存 hash，因为 hash 无法还原，不能用于真实 API 调用；
- V0.2 推荐“教师登录后，会话级临时 API Key”，服务端内存临时保存，退出 / 清除 / 服务重启后失效；
- 长期保存 Key 需要另行设计加密存储方案，不在当前阶段实现。

## Add-on Boundary / 加分原型边界

自动批阅不是当前 V0.2 主线。SQL、Python、C 等编程类评分只能作为后续实验性方向出现，不得影响课程计划上传、课次材料、知识主干、课前学情测试、学生导学案、教师编辑确认和辅助导出的交付。

如实现 Python 基础题批阅 MVP，必须严格限制在中职学生入门题范围：

- 单文件 `.py`；
- 在线粘贴代码或上传 `.py`；
- 简单输入输出题；
- 固定测试用例；
- 捕获 `stdout` / `stderr`；
- 超时控制；
- 基础错误类型识别；
- 教师复核。

不要实现：

- 多文件项目；
- 第三方库；
- 图形界面；
- 网络访问；
- 数据库访问；
- 文件读写题；
- 复杂单元测试框架；
- 长时间运行程序；
- 自动代写答案。

Python 基础题批阅推荐流程：

```text
学生提交 Python 代码
→ 系统在受限环境中运行
→ 输入测试用例
→ 捕获 stdout / stderr
→ 判断输出是否匹配
→ 识别错误类型
→ 生成初步反馈
→ 教师复核
→ 学生查看最终反馈
→ 记录学习错误数据
```

## Learning Data Annotation / 学习数据标注要求

SQL 批阅和 Python 基础题批阅原型都应为学习错误数据标注预留字段。标注目标不是监控学生，而是帮助教师理解共性错误、优化导学案和改进教学反馈。

可以记录：

- 学生提交内容；
- 作业类型；
- 测试用例结果；
- `stdout`；
- `stderr`；
- 自动识别错误类型；
- 系统初评；
- 教师最终评分；
- 教师修正反馈；
- 教师标注的错误类型；
- 是否需要后续辅导；
- 是否可作为脱敏样本进入教学错误数据集。

隐私要求：

- 不得把真实学生数据写入公开仓库；
- 不得把真实成绩、真实班级名单或可识别学生身份的信息作为案例数据提交；
- 演示只能使用虚构数据或脱敏数据。

## Confirmed Python MVP Decisions / Python MVP 已确认决策

如果后续施工 Python 基础题批阅 MVP，必须遵守以下已确认范围：

1. 只演示 1-2 道基础题。
2. 题目一：`input + if` 判断，例如输入成绩，判断是否及格。
3. 题目二：`for` 循环求和，例如输入 `n`，计算 `1` 到 `n` 的和。
4. 教师标注只做“主错误类型单选 + 教师补充说明文本”。
5. V0.2 不做多标签错误标注。
6. `can_enter_dataset` 默认必须为 `false`。
7. 只有教师手动勾选后，样本才允许进入脱敏教学错误数据集。

不要继续扩展 Python 题型，不要加入列表综合题、文件读写、多文件项目、第三方库、图形界面、网络访问或数据库访问。
