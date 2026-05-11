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
