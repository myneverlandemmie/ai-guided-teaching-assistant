# Demo Lesson: SELECT + WHERE / 演示课：SELECT 与 WHERE 条件筛选

## 中文说明

第一节演示课建议选择：

**0401｜简单查询：SELECT 与 WHERE 条件筛选**

该课次适合中职数据库课程入门，知识点清晰，便于展示课程资料整理、知识主干、课前学情测试和学生导学案。数据库类作业批阅仅作为后续探索方向，不作为当前已实现能力展示。

## 核心知识点 / Core Knowledge

```sql
SELECT column_name
FROM table_name
WHERE condition;
```

## 高阶拓展 / Advanced Extension

```sql
SELECT name AS student_name, score + 5 AS adjusted_score
FROM students
WHERE score >= 60;
```

高阶任务可以包括：

- AS 字段别名；
- 计算字段；
- 简单函数。

These should be used as C-level extension tasks, not as the core grading requirement of V0.2.
