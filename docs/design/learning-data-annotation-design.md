# Learning Data Annotation Design / 学习错误数据标注设计

## 1. Purpose / 设计目的

学习错误数据标注是后续预留方向，可用于在编程类、数据库类作业的规则测试与教师复核过程中沉淀教学反馈数据。它不是当前已实现功能，也不是为了监控学生，而是为了帮助教师理解常见错误、优化导学案、调整课堂讲解和改进教学反馈。

V0.2 只做数据集开端，不建设完整数据集平台。

## 2. Data Sources / 数据来源

V0.2 可从以下环节沉淀学习错误数据：

- 数据库类作业提交预留；
- 规则测试结果草稿预留；
- Python 基础题批阅原型；
- 教师复核评分；
- 教师修正反馈；
- 学生最终反馈发布记录。

## 3. Data Fields / 标注字段

建议记录字段：

| 字段 | 含义 |
|---|---|
| submitted_content | 学生提交内容 |
| assignment_type | 作业类型，如 sql / python |
| test_case_results | 测试用例结果 |
| stdout | 标准输出 |
| stderr | 标准错误 |
| error_type_auto | 自动识别错误类型 |
| auto_score | 系统初评 |
| final_score | 教师最终评分 |
| teacher_feedback | 教师修正反馈 |
| error_type_teacher | 教师标注的错误类型 |
| need_followup | 是否需要后续辅导 |
| can_enter_dataset | 是否可作为脱敏样本进入教学错误数据集 |

## 4. SQL Error Tags / SQL 错误标签

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

## 5. Python Error Tags / Python 错误标签

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

## 6. Teacher Review / 教师复核

自动识别的错误类型只能作为初步判断，最终教学反馈应由教师确认。

教师复核时可以：

- 修改最终得分；
- 修改反馈语言；
- 修正错误类型；
- 标记是否需要后续辅导；
- 标记是否可进入脱敏教学错误数据集。

## 7. Privacy and Release Rules / 隐私与发布规则

必须遵守以下规则：

- 公开仓库不得包含真实学生数据；
- 公开仓库不得包含真实成绩；
- 公开仓库不得包含真实班级名单；
- 案例材料中只能使用演示数据或脱敏数据；
- 未经授权的学生代码不得作为公开样例；
- 项目方演示服务器不得承接外部真实班级的大规模数据沉淀。

## 8. V0.2 Boundary / V0.2 边界

V0.2 只建立学习错误数据标注的字段、流程和演示样例。后续版本可以扩展：

- 常见错误统计；
- 班级层面的错误趋势；
- 导学案自动优化建议；
- 教师反馈语料库；
- 脱敏教学错误数据集。

这些扩展不应影响 V0.2 SQL 主线交付。

## 9. V0.2 Annotation Decisions / V0.2 标注确认决策

已确认的 V0.2 标注规则：

1. Python MVP 只演示 1-2 道基础题。
2. 推荐题目一：`input + if` 判断，例如输入成绩，判断是否及格。
3. 推荐题目二：`for` 循环求和，例如输入 `n`，计算 `1` 到 `n` 的和。
4. 教师标注采用“主错误类型单选 + 教师补充说明文本”。
5. V0.2 不做多标签错误标注。
6. `can_enter_dataset` 必须默认 `false`。
7. 只有教师手动勾选后，样本才允许进入脱敏教学错误数据集。

这样可以在不增加复杂度的前提下展示输入处理、条件判断、循环、`stdout` 捕获、错误类型识别和教师复核。
