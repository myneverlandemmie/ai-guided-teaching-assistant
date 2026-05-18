# Database Schema V0.2 / V0.2 数据库结构设计

## 1. Purpose / 文档目的

本文档用于说明“智学导评 V0.2”的数据库结构设计，为后续 FastAPI、SQLAlchemy、课程计划导入、AI 生成、SQL 自动批阅和教师复核功能提供数据基础。

This document defines the V0.2 database schema for the AI Guided SQL Assessment Platform.

## 2. Design Principles / 设计原则

V0.2 数据库设计遵循以下原则：

1. 教学流程优先，先服务课程计划导入、课次管理、导学案生成、SQL 作业批阅和学习总结。
2. 保留教师最终控制权，AI 生成内容和自动批阅结果都必须可编辑、可确认、可追溯。
3. 支持三层使用模式，包括云端演示、Windows 单机体验和 Linux / 私有服务器部署。
4. V0.2 可使用 MySQL 作为正式部署数据库，同时保留 SQLite 兼容演示模式。
5. 不在 V0.2 中实现完整 Python 批阅和 OCR 拍照纠错，但表结构应避免阻碍后续扩展。
6. 所有涉及学生数据的表都应使用演示数据或私有部署数据，不在公开仓库中存放真实学生信息。

## 3. Database Modes / 数据库使用模式

### 3.1 Cloud Demo Mode / 云端演示模式

项目方阿里云 ECS 上部署演示系统，使用脱敏演示数据。

建议数据库：

- MySQL；
- 演示班级；
- 演示学生；
- 演示课程计划；
- Mock 或少量真实 AI 调用。

### 3.2 Windows Local Demo Mode / Windows 单机体验模式

普通教师本地体验系统核心流程。

建议数据库：

- SQLite；
- 内置演示班级；
- 内置演示学生；
- Mock AI 模式；
- SQLite 兼容 SQL 批阅模式。

### 3.3 Private Server Deployment Mode / 私有服务器部署模式

教师或学校部署到自有服务器，用于真实课堂。

建议数据库：

- MySQL；
- 使用方自行管理学生数据；
- 使用方自行配置 API Key；
- 可根据学校要求配置备份与访问控制。

## 4. Entity Overview / 实体概览

V0.2 主要包含以下数据实体：

| 实体 | 含义 |
|---|---|
| users | 用户 |
| classes | 班级 |
| class_members | 班级成员 |
| courses | 课程 |
| course_plan_uploads | 授课计划上传记录 |
| planned_lessons | 解析后的计划课次 |
| lessons | 正式课次 |
| lesson_materials | 课次教学材料 |
| knowledge_outlines | 知识主干 |
| quizzes | 小测题 |
| guidebooks | 分层导学案 |
| assignments | 作业 |
| submissions | 学生提交 |
| grading_results | 批阅结果 |
| learning_summaries | 学习总结 |
| ai_generation_logs | AI 生成记录 |

## 5. Tables / 数据表设计

## 5.1 users / 用户表

用于保存教师、学生和管理员账号。

| 字段名 | 类型建议 | 含义 |
|---|---|---|
| id | integer / bigint | 用户 ID |
| username | varchar | 登录用户名 |
| password_hash | varchar | 密码哈希 |
| role | varchar | teacher / student / admin |
| real_name | varchar | 真实姓名或演示姓名 |
| email | varchar | 邮箱，可选 |
| is_active | boolean | 是否启用 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

说明：

- V0.2 至少支持 teacher 和 student 两类角色。
- 演示账号可以使用 `demo_teacher`、`demo_student_01` 等形式。
- 公开仓库中不得出现真实学生账号和真实密码。

## 5.2 classes / 班级表

用于保存教师创建的班级。

| 字段名 | 类型建议 | 含义 |
|---|---|---|
| id | integer / bigint | 班级 ID |
| name | varchar | 班级名称 |
| teacher_id | integer / bigint | 创建教师 ID |
| invite_code | varchar | 班级邀请码，可选 |
| is_demo | boolean | 是否为演示班级 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

说明：

- V0.2 默认创建一个“演示班级”。
- 正常功能预留教师创建真实班级的能力。
- 项目方演示服务器只使用演示班级，不承接外部真实班级大规模试用。

## 5.3 class_members / 班级成员表

用于保存学生与班级之间的关系。

| 字段名 | 类型建议 | 含义 |
|---|---|---|
| id | integer / bigint | 记录 ID |
| class_id | integer / bigint | 班级 ID |
| student_id | integer / bigint | 学生用户 ID |
| level | varchar | A / B / C 学习层级 |
| joined_at | datetime | 加入时间 |

说明：

- level 字段用于分层导学案发布。
- V0.2 可以由教师手动设置层级，也可以先默认所有演示学生为 B 层。
- 后续版本可根据小测和作业结果自动辅助建议层级。

## 5.4 courses / 课程表

用于保存课程基本信息。

| 字段名 | 类型建议 | 含义 |
|---|---|---|
| id | integer / bigint | 课程 ID |
| class_id | integer / bigint | 所属班级 ID |
| title | varchar | 课程名称 |
| semester | varchar | 学期 |
| teacher_id | integer / bigint | 任课教师 ID |
| status | varchar | draft / active / archived |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

说明：

- 示例课程可命名为“数据库应用与数据分析”。
- 一门课程可以有一个或多个授课计划上传记录。
- 一门课程下可以包含多个正式课次。

## 5.5 course_plan_uploads / 授课计划上传表

用于保存教师上传授课计划 Excel 的记录。

| 字段名 | 类型建议 | 含义 |
|---|---|---|
| id | integer / bigint | 上传记录 ID |
| course_id | integer / bigint | 所属课程 ID |
| uploaded_by | integer / bigint | 上传教师 ID |
| original_filename | varchar | 原始文件名 |
| file_path | varchar | 文件保存路径 |
| parsed_status | varchar | pending / success / failed |
| error_message | text | 解析错误信息 |
| created_at | datetime | 上传时间 |

说明：

- 上传后应先保存原始文件，再进行解析。
- 即使解析失败，也应保留错误信息，便于教师排查。
- V0.2 不要求兼容所有教务模板，优先支持当前样例格式。

## 5.6 planned_lessons / 计划课次表

用于保存从授课计划中解析出的课次预览数据。

| 字段名 | 类型建议 | 含义 |
|---|---|---|
| id | integer / bigint | 计划课次 ID |
| course_plan_upload_id | integer / bigint | 来源上传记录 ID |
| course_id | integer / bigint | 所属课程 ID |
| week | varchar | 周次 |
| lesson_no | varchar | 课次序号 |
| hours | numeric / varchar | 学时 |
| lesson_code | varchar | 课次编码，如 0401 |
| lesson_title | varchar | 课次标题 |
| content_raw | text | 原始教学内容 |
| tools | text | 教学用具 |
| homework | text | 作业 |
| notes | text | 备注 |
| status | varchar | pending / confirmed / skipped |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

说明：

- planned_lessons 是“预览与确认层”，不是正式课次。
- 教师确认后，系统才将其写入 lessons 表。
- status 为 skipped 的记录不生成正式课次。
- 解析异常但仍可展示的行可以保留为 pending，由教师手动确认。

## 5.7 lessons / 正式课次表

用于保存教师确认后的正式课次。

| 字段名 | 类型建议 | 含义 |
|---|---|---|
| id | integer / bigint | 课次 ID |
| course_id | integer / bigint | 所属课程 ID |
| planned_lesson_id | integer / bigint | 来源计划课次 ID，可选 |
| week | varchar | 周次 |
| lesson_no | varchar | 课次序号 |
| hours | numeric / varchar | 学时 |
| lesson_code | varchar | 课次编码 |
| title | varchar | 课次标题 |
| content_summary | text | 教学内容摘要 |
| homework_hint | text | 默认作业提示 |
| status | varchar | draft / published / archived |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

说明：

- 后续知识主干、小测题、导学案、作业都挂接到 lessons。
- planned_lesson_id 用于追溯来源。
- 教师也可以手动创建不来自授课计划的课次。

## 5.8 lesson_materials / 课次教学材料表

用于保存教师上传或粘贴的教案、PPT 文本、课堂材料等。

| 字段名 | 类型建议 | 含义 |
|---|---|---|
| id | integer / bigint | 材料 ID |
| lesson_id | integer / bigint | 所属课次 ID |
| material_type | varchar | lesson_plan / ppt / text / other |
| title | varchar | 材料标题 |
| content | text | 文本内容 |
| file_path | varchar | 文件路径，可选 |
| uploaded_by | integer / bigint | 上传教师 ID |
| created_at | datetime | 创建时间 |

说明：

- V0.2 优先支持粘贴文本或上传可解析文本。
- PPT 原文件解析可以后续增强，当前可以先要求教师提供 PPT 文本或摘要。
- AI 生成知识主干时应引用该表内容。

## 5.9 knowledge_outlines / 知识主干表

用于保存 AI 生成并经教师确认的本节课知识主干。

| 字段名 | 类型建议 | 含义 |
|---|---|---|
| id | integer / bigint | 知识主干 ID |
| lesson_id | integer / bigint | 所属课次 ID |
| ai_raw_output | text | AI 原始输出 |
| edited_content | text | 教师编辑后内容 |
| status | varchar | draft / reviewed / published |
| generated_by_model | varchar | 使用模型 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

说明：

- ai_raw_output 和 edited_content 应同时保留。
- 学生端只能看到教师确认后的内容。
- 后续小测题和导学案生成应优先基于 edited_content。

## 5.10 quizzes / 小测题表

用于保存课前或课堂小测题。

| 字段名 | 类型建议 | 含义 |
|---|---|---|
| id | integer / bigint | 题目 ID |
| lesson_id | integer / bigint | 所属课次 ID |
| level | varchar | basic / medium / advanced |
| question_type | varchar | single_choice / fill_blank |
| question | text | 题干 |
| options | text / json | 选项 |
| answer | text | 标准答案 |
| explanation | text | 解析 |
| status | varchar | draft / published |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

说明：

- V0.2 先支持单选题和填空题。
- options 字段在 MySQL 中可用 JSON 或 text 存储；SQLite 演示模式可使用 text。
- 所有 AI 生成题目必须允许教师编辑。

## 5.11 guidebooks / 分层导学案表

用于保存 A / B / C 三层导学案。

| 字段名 | 类型建议 | 含义 |
|---|---|---|
| id | integer / bigint | 导学案 ID |
| lesson_id | integer / bigint | 所属课次 ID |
| level | varchar | A / B / C |
| ai_raw_output | text | AI 原始输出 |
| edited_content | text | 教师编辑后内容 |
| status | varchar | draft / reviewed / published |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

说明：

- A 层面向基础薄弱学生，内容更细。
- B 层面向一般学生，按标准节奏展开。
- C 层面向掌握较好学生，增加拓展任务。
- 教师可以选择统一发布某一版，也可以按学生层级发布不同版本。

## 5.12 assignments / 作业表

用于保存教师创建的 SQL 作业。

| 字段名 | 类型建议 | 含义 |
|---|---|---|
| id | integer / bigint | 作业 ID |
| lesson_id | integer / bigint | 所属课次 ID |
| title | varchar | 作业标题 |
| description | text | 作业说明 |
| assignment_type | varchar | sql |
| init_schema | text | 初始化表结构 |
| init_data | text | 初始化数据 |
| standard_sql | text | 标准 SQL，可选 |
| expected_result | text / json | 标准结果 |
| compare_mode | varchar | exact / ignore_order / row_count / custom |
| max_score | integer | 满分 |
| status | varchar | draft / published / archived |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

说明：

- V0.2 assignment_type 只实现 sql。
- Python 作业类型后续版本再加入。
- Windows 单机体验模式可使用 SQLite 兼容 SQL 题目。
- 私有部署模式后续可增强 MySQL 批阅能力。

## 5.13 submissions / 学生提交表

用于保存学生作业提交内容。

| 字段名 | 类型建议 | 含义 |
|---|---|---|
| id | integer / bigint | 提交 ID |
| assignment_id | integer / bigint | 作业 ID |
| student_id | integer / bigint | 学生 ID |
| content | text | 学生提交内容 |
| submitted_at | datetime | 提交时间 |
| status | varchar | submitted / graded / reviewed / published |
| attempt_no | integer | 第几次提交 |

说明：

- V0.2 可以先支持每名学生一次提交。
- 后续可扩展多次提交与提交历史。
- 学生提交的 SQL 不应直接拼接到业务数据库中执行，应通过批阅引擎隔离执行。

## 5.14 grading_results / 批阅结果表

用于保存系统自动批阅和教师复核结果。

| 字段名 | 类型建议 | 含义 |
|---|---|---|
| id | integer / bigint | 批阅结果 ID |
| submission_id | integer / bigint | 提交 ID |
| auto_score | integer | 系统初评分 |
| final_score | integer | 教师确认分 |
| execution_output | text | 执行输出 |
| error_message | text | 错误信息 |
| auto_feedback | text | 系统反馈 |
| teacher_feedback | text | 教师反馈 |
| reviewed_by | integer / bigint | 复核教师 ID |
| reviewed_at | datetime | 复核时间 |
| status | varchar | auto_graded / reviewed / published |

说明：

- auto_score 不等于最终成绩。
- final_score 由教师确认后生效。
- 学生端只能看到 published 状态的结果。
- 错误信息应转化为教学性反馈，避免只显示生硬报错。

## 5.15 learning_summaries / 学习总结表

用于保存每名学生每个课次的学习总结。

| 字段名 | 类型建议 | 含义 |
|---|---|---|
| id | integer / bigint | 总结 ID |
| lesson_id | integer / bigint | 所属课次 ID |
| student_id | integer / bigint | 学生 ID |
| ai_summary | text | AI 总结初稿 |
| teacher_summary | text | 教师确认总结 |
| status | varchar | draft / reviewed / published |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

说明：

- 学习总结应基于小测、作业、批阅和教师反馈。
- 教师确认前不得直接发布给学生。
- 总结语言应具体、温和、可执行。

## 5.16 ai_generation_logs / AI 生成记录表

用于保存 AI 调用记录，便于追溯和控制成本。

| 字段名 | 类型建议 | 含义 |
|---|---|---|
| id | integer / bigint | 记录 ID |
| user_id | integer / bigint | 发起用户 ID |
| lesson_id | integer / bigint | 关联课次 ID，可选 |
| task_type | varchar | outline / quiz / guidebook / feedback / summary |
| model_name | varchar | 使用模型 |
| prompt_snapshot | text | 提示词快照 |
| output_snapshot | text | 输出快照 |
| is_mock | boolean | 是否 Mock AI |
| token_usage | text / json | Token 使用量，可选 |
| created_at | datetime | 创建时间 |

说明：

- V0.2 可以先简化 token_usage。
- Mock AI 模式也应记录 is_mock，便于区分真实调用和演示输出。
- 公开仓库不得包含真实 API Key 或真实调用日志。

## 6. Relationships / 表关系

主要关系如下：

| 关系 | 说明 |
|---|---|
| users 1 - N classes | 一个教师可以创建多个班级 |
| classes 1 - N class_members | 一个班级有多个学生 |
| classes 1 - N courses | 一个班级可以有多门课程 |
| courses 1 - N course_plan_uploads | 一门课程可多次上传授课计划 |
| course_plan_uploads 1 - N planned_lessons | 一次上传可解析出多个计划课次 |
| planned_lessons 1 - 0..1 lessons | 一个计划课次确认后生成一个正式课次 |
| courses 1 - N lessons | 一门课程有多个正式课次 |
| lessons 1 - N lesson_materials | 一个课次可有多个教学材料 |
| lessons 1 - N knowledge_outlines | 一个课次可有多个知识主干版本 |
| lessons 1 - N quizzes | 一个课次可有多个小测题 |
| lessons 1 - N guidebooks | 一个课次可有 A / B / C 多份导学案 |
| lessons 1 - N assignments | 一个课次可有多个作业 |
| assignments 1 - N submissions | 一个作业有多个学生提交 |
| submissions 1 - 1 grading_results | 一个提交对应一个主要批阅结果 |
| lessons + students 1 - N learning_summaries | 每名学生每个课次可有学习总结 |
| users / lessons 1 - N ai_generation_logs | AI 生成记录关联用户和课次 |

## 7. Status Values / 状态值约定

### 7.1 General Status / 通用状态

| 状态 | 含义 |
|---|---|
| draft | 草稿 |
| pending | 待处理 |
| reviewed | 已审核 |
| published | 已发布 |
| archived | 已归档 |
| failed | 失败 |
| skipped | 跳过 |

### 7.2 Submission Status / 提交状态

| 状态 | 含义 |
|---|---|
| submitted | 已提交 |
| graded | 已自动批阅 |
| reviewed | 教师已复核 |
| published | 已发布给学生 |

### 7.3 Planned Lesson Status / 计划课次状态

| 状态 | 含义 |
|---|---|
| pending | 待确认 |
| confirmed | 已确认 |
| skipped | 已跳过 |

## 8. V0.2 Simplifications / V0.2 简化策略

V0.2 为了保证半个月内可落地，采用以下简化策略：

1. 用户权限只区分 teacher、student、admin，不做复杂组织架构。
2. 学生账号可先由教师创建，不做复杂注册审核。
3. 授课计划导入先支持固定格式 Excel。
4. AI 生成内容先通过文本字段保存，不做复杂富文本结构。
5. Windows 单机体验模式可使用 SQLite。
6. SQL 批阅先覆盖 SELECT、WHERE、AS 和简单计算字段。
7. Python 批阅和 OCR 拍照纠错不进入当前版本。
8. 外部教师真实使用应自行部署，不使用项目方演示服务器。

## 9. Security and Privacy Notes / 安全与隐私说明

1. 公开仓库不得提交 `.env` 文件。
2. 公开仓库不得提交真实 API Key。
3. 公开仓库不得提交真实学生信息。
4. 公开仓库只保留演示班级、虚构学生和脱敏样例数据。
5. 项目方演示服务器不承接外部真实班级大规模试用。
6. 私有部署时，使用方应自行负责学生数据与 API Key 的管理。
7. SQL 批阅执行环境应与业务数据库隔离，避免学生 SQL 影响系统数据。

## 10. Next Step / 下一步

完成本文档后，可让 Codex 先只读文档，输出项目理解、问题清单和第一阶段施工计划。

在 Codex 理解确认无误后，第一轮正式施工建议聚焦：

- course_plan_parser；
- 授课计划字段识别；
- 课次编码解析；
- planned_lessons 数据结构；
- 解析单元测试；
- 最小课程计划上传与预览页面。
## 11. Programming Assignment Extension / 编程作业扩展预留

V0.2 当前 SQL 主线可以先沿用现有 `assignments`、`submissions`、`grading_results` 三张表完成 SQL 作业、提交和教师复核。不要为了 Python 加分原型强行推翻已有设计。

如果后续需要同时支持 SQL 和 Python 等编程类作业，可以逐步抽象为统一的 `programming_*` 表。该设计用于扩展预留，不要求在 V0.2 主线中一次性全部实现。

### 11.1 programming_assignments / 编程作业表

用于统一保存 SQL / Python 等编程类作业。

| 字段名 | 类型建议 | 含义 |
|---|---|---|
| id | integer / bigint | 编程作业 ID |
| lesson_id | integer / bigint | 所属课次 ID |
| assignment_type | varchar | sql / python |
| title | varchar | 作业标题 |
| description | text | 作业说明 |
| starter_code | text | 起始代码，可选 |
| test_cases | text / json | 测试用例 |
| expected_outputs | text / json | 期望输出 |
| max_score | integer | 满分 |
| status | varchar | draft / published / archived |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

说明：

- SQL 主线仍可使用当前 `assignments` 表。
- Python 基础题原型如需落库，可以先复用 `assignments.assignment_type`，后续再迁移到 `programming_assignments`。
- Python 原型只面向单文件 `.py` 和简单输入输出题，不记录多文件项目结构。

### 11.2 programming_submissions / 编程提交表

用于统一保存 SQL / Python 等编程类提交。

| 字段名 | 类型建议 | 含义 |
|---|---|---|
| id | integer / bigint | 提交 ID |
| assignment_id | integer / bigint | 编程作业 ID |
| student_id | integer / bigint | 学生 ID |
| submitted_code | text | 学生提交代码 |
| submitted_at | datetime | 提交时间 |
| status | varchar | submitted / graded / reviewed / published |
| attempt_no | integer | 第几次提交 |

说明：

- 当前 `submissions.content` 可先保存 SQL 或 Python 提交内容。
- 后续统一为 `submitted_code` 时，应保留旧数据迁移路径。
- Python 提交不得包含真实学生身份信息，也不得提交到公开仓库。

### 11.3 grading_annotations / 批阅与标注表

用于保存自动批阅结果、教师复核结果和学习错误数据标注。

| 字段名 | 类型建议 | 含义 |
|---|---|---|
| id | integer / bigint | 标注 ID |
| submission_id | integer / bigint | 提交 ID |
| auto_score | integer | 系统初评分 |
| final_score | integer | 教师最终评分 |
| stdout | text | 标准输出 |
| stderr | text | 标准错误 |
| error_type_auto | varchar | 系统自动识别错误类型 |
| error_type_teacher | varchar | 教师修正错误类型 |
| auto_feedback | text | 系统反馈 |
| teacher_feedback | text | 教师反馈 |
| need_followup | boolean | 是否需要后续辅导 |
| can_enter_dataset | boolean | 是否可作为脱敏样本进入教学错误数据集 |
| reviewed_by | integer / bigint | 复核教师 ID |
| reviewed_at | datetime | 复核时间 |
| status | varchar | auto_graded / reviewed / published |

说明：

- 当前 `grading_results` 已能保存自动分、最终分、执行输出、错误信息和教师反馈。
- V0.2 可先在 `grading_results` 上扩展错误类型字段，或在后续版本新增 `grading_annotations`。
- `can_enter_dataset` 只能在脱敏、授权和教学用途明确的前提下使用。
- 数据标注不是为了监控学生，而是为了帮助教师理解常见错误、优化导学案和改进教学。

## 12. Error Type Tags / 错误类型标签

### 12.1 Python Error Tags / Python 错误标签

Python 基础题批阅原型只识别入门级错误标签。

| 标签 | 含义 |
|---|---|
| SyntaxError | 语法错误 |
| NameError | 变量未定义 |
| TypeError | 类型错误 |
| ValueError | 值错误 |
| IndexError | 索引错误 |
| ZeroDivisionError | 除零错误 |
| Timeout | 运行超时 |
| WrongAnswer | 答案错误 |
| FormatError | 输出格式错误 |
| LogicError | 疑似逻辑错误 |
| FunctionCallError | 函数调用错误 |
| ParameterError | 形参与实参理解错误 |
| InputOutputError | 输入输出理解错误 |

### 12.2 SQL Error Tags / SQL 错误标签

SQL 主线可先覆盖基础查询错误标签，后续随教学内容扩展。

| 标签 | 含义 |
|---|---|
| SqlSyntaxError | SQL 语法错误 |
| TableNameError | 表名错误 |
| ColumnNameError | 字段名错误 |
| ConditionError | 条件筛选错误 |
| OrderByError | 排序错误 |
| AggregationError | 聚合错误 |
| GroupByError | 分组错误 |
| JoinError | 连接错误 |
| WrongAnswer | 结果错误 |
| FormatError | 结果格式错误 |

## 13. Learning Data Annotation Notes / 学习数据标注说明

系统在自动批阅与教师复核过程中，可以同步沉淀学习过程数据，包括：

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

约束：

- 数据标注不是为了监控学生，而是为了帮助教师理解常见错误、优化导学案和改进教学；
- 公开仓库不得包含真实学生数据；
- 案例材料中只能使用演示数据或脱敏数据；
- 数据集建设是后续拓展方向，V0.2 只做开端；
- 项目方演示服务器不得沉淀外部真实班级数据。

## 14. Confirmed Annotation Defaults / 已确认标注默认值

V0.2 学习错误标注的默认规则：

1. 教师标注采用主错误类型单选，字段可使用 `error_type_teacher`。
2. 教师补充说明使用文本字段，可复用 `teacher_feedback` 或后续扩展单独说明字段。
3. V0.2 不实现多标签错误类型。
4. `can_enter_dataset` 必须默认 `false`。
5. 只有教师手动勾选后，样本才允许作为脱敏样本进入教学错误数据集。

该默认值是数据安全边界的一部分，不能在演示服务器或公开样例中默认打开。
