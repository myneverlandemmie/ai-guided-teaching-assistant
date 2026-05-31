# Current Implementation Status / 当前实现状态

## 文档目的

本文档记录当前代码已经真实实现的功能、尚未实现的范围和测试口径，用于避免 README、案例材料或后续 Codex 施工提示把预留功能误写成已完成。

项目定位统一为：面向中职教师的 AI 辅助教学设计分析与导学案生成系统。

## 已实现

当前代码已经实现：

1. 课程管理；
2. 课程中心 V2：`/ui-v2/courses`；
3. 授课计划上传；
4. Excel 课程计划解析；
5. planned lessons 预览、确认、跳过；
6. 批量生成正式 Lesson；
7. 正式课次列表：`/courses/{course_id}/lessons`，作为 V2 过渡入口；
8. 正式课次详情页；
9. 课次资料上传、粘贴文本、多文件上传和删除；
10. `txt` / `md` / `docx` / `pptx` / `xlsx` 资料文本提取；
11. 页面不显示服务器绝对路径；
12. 会话级 DeepSeek API Key 设置、掩码显示、清除和模型选择；
13. DeepSeek Provider；
14. 知识主干生成、编辑和保存；
15. 知识主干生成前基础行政信息过滤；
16. 课程资料整理 V2：`/ui-v2/lessons/{lesson_id}/materials-outline`；
17. 备课参考建议；
18. 课前学情测试 V2：`/ui-v2/lessons/{lesson_id}/diagnostic-probe`；
19. 题卡预览、单题编辑、单题删除；
20. 学习通习题文件导出；
21. 学生导学案 V2：`/ui-v2/lessons/{lesson_id}/learning-guides`；
22. 全班通用导学案、巩固提升任务包、拓展探究任务包；
23. Markdown 下载；
24. 教师编辑保存草稿；
25. 本地结构化草稿与 fallback，用于演示不中断和教师初稿准备。

测试状态以当前自动化测试结果为准。

## 推荐演示入口

- V2 课程中心：`/ui-v2/courses`
- 正式课次列表：`/courses/{course_id}/lessons`
- 课程资料整理 V2：`/ui-v2/lessons/{lesson_id}/materials-outline`
- 课前学情测试 V2：`/ui-v2/lessons/{lesson_id}/diagnostic-probe`
- 学生导学案 V2：`/ui-v2/lessons/{lesson_id}/learning-guides`

旧页面仍作为 legacy / 兼容页面保留，用于兼容入口、测试入口和部分回退入口。案例提交前不建议移动或删除旧模板。

## 尚未实现

当前尚未实现：

- 完整登录权限体系；
- 学生端；
- 学习通 API；
- 作业批阅后端；
- 自动评分 route；
- 新的作业评分数据库表或字段；
- 自动发布评语；
- 自动评价学生；
- 统计学生成绩；
- OCR；
- PDF、图片、扫描件、旧版 `.doc/.ppt`、`xls` 解析；
- 面向外部真实班级的公开生产服务。

## 作业批阅口径

作业批阅只能写为预留功能、后续探索方向。

后续可探索面向编程类、数据库类作业的规则测试与 AI 辅助评语草稿。结果仅供教师参考，需教师审核确认后使用。

不得写成已完成作业批阅、已实现自动评分、已有学生端、自动发布评语或自动评价学生。

## AI Boundary / AI 边界

教师可在 `/ai/settings` 为当前浏览器会话设置 DeepSeek API Key 和模型。

- `deepseek-v4-flash`：适合快速预览和页面流程验证；
- `deepseek-v4-pro`：适合正式生成、任务包和备课参考建议。

API Key 只保存在服务端内存中，不写数据库、不写 cookie、不写日志。清除 API Key 或服务重启后失效。

所有 AI 或本地结构化输出都是教师审阅用草稿，不是自动定稿内容。教师必须审阅、修改、确认后使用。

## 材料解析边界

当前支持：

- `txt`
- `md`
- `docx`
- `pptx`
- `xlsx`

当前不支持：

- `xls`
- PDF
- 图片
- 扫描件
- OCR
- 旧版 `.doc/.ppt`

## 下一步建议

案例提交前优先保持当前 V2 主流程稳定，完善文档、演示材料和测试结果记录。`main.py` 可先生成拆分审计报告，不建议在案例提交前进行大规模 route 重构。
