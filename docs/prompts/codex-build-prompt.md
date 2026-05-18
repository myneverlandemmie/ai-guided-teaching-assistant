# Codex Build Prompt / Codex 施工提示词

## 中文说明

请你帮助构建“智学导评 V0.2：AI 导学与 SQL 自动批阅系统”。

当前版本的目标是完成一个围绕数据库课程的教学闭环，不要扩展到完整 Python 批阅、OCR 拍照纠错或复杂前端工程。

## English Instruction

You are helping build the V0.2 version of an AI-guided SQL assessment platform for vocational database courses.

The current version should focus on a complete SQL teaching workflow. Do not expand the project into full Python grading, OCR screenshot correction, or complex frontend engineering.

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

Implement the course plan import module.

实现“课程计划上传与自动拆解课次”模块。

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

## Add-on Boundary / 加分原型边界

SQL / MySQL 教学闭环仍然是 V0.2 主线。Python 批阅只能作为加分原型出现，不得替代 SQL 主线，不得影响课程计划上传、课次拆解、导学案、小测题、SQL 作业、教师复核和学习总结的交付。

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
