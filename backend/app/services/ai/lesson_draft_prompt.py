"""课前学情测试与学生导学案生成 Prompt。"""

from __future__ import annotations

from app.models.knowledge_outline import KnowledgeOutline
from app.models.lesson import Lesson
from app.services.ai.sanitizer import sanitize_text_for_outline


LESSON_DRAFT_SYSTEM_MESSAGE = """
你是面向中职课堂的 AI 教学助理，只生成教师可编辑的草稿。
边界：
- 必须直接输出正文，不要输出“当然可以”“以下是”“好的”“我将为你”“根据你的要求”等对话式开头；
- 不要解释自己正在做什么；
- 不生成完整教案；
- 不替教师决定教学目标、重难点和教学流程；
- 不评价教师能力；
- 不输出一键备课结果或比赛教案成稿；
- 所有内容只是草稿，必须由教师审核、修改、确认后使用；
- 不编造材料中没有的事实，材料不足时写“仅基于现有材料生成，需教师补充”；
- 不暗示学生端、自动评分或学习通 API 已实现。
""".strip()


def _lesson_name(lesson: Lesson) -> str:
    """生成 prompt 中使用的课次名称。"""

    return f"{lesson.lesson_code}-{lesson.title}" if lesson.lesson_code else lesson.title


def _outline_text(outline: KnowledgeOutline, max_length: int = 5000) -> str:
    """取教师复核后的知识主干，并做基础脱敏和长度控制。"""

    text = sanitize_text_for_outline((outline.edited_content or outline.ai_raw_output or "").strip())
    if len(text) <= max_length:
        return text
    return f"{text[:max_length]}..."


def build_lesson_draft_prompt(lesson: Lesson, outline: KnowledgeOutline, draft_type: str) -> str:
    """构造课前学情测试或学生导学案 prompt。

    Args:
        lesson: 当前课次。
        outline: 最新知识主干。
        draft_type: diagnostic_probe / guide_low / guide_mid / guide_high。

    Returns:
        面向 DeepSeek Chat Completion 的中文 prompt。

    Raises:
        ValueError: draft_type 不受支持。
    """

    lesson_name = sanitize_text_for_outline(_lesson_name(lesson))
    outline_text = _outline_text(outline)
    common_context = f"""
课次：{lesson_name}
教学内容摘要：{sanitize_text_for_outline(lesson.content_summary or "暂无")}

教师确认后的课程知识主干：
{outline_text or "暂无知识主干，需教师补充。"}
""".strip()

    if draft_type == "diagnostic_probe":
        return f"""
{common_context}

请生成“课前学情测试草稿”，用于学习起点诊断，不是正式考试。

要求：
1. 生成 5—8 道题；
2. 题型优先使用单选题、判断题、填空题、简答题；
3. 内容覆盖基础概念、前置知识、任务背景理解、操作步骤、易错判断、安全规范、职业素养、进入本课任务所需的准备知识；
4. 每题必须使用当前系统兼容的 Markdown 格式：

### 题目 1
- 题型：单选题
- 题干：……
- 选项：A. ……；B. ……；C. ……；D. ……
- 参考答案：A
- 简短解析：……
- 诊断点：……
- 难度：基础

5. 判断题写“参考答案：正确”或“参考答案：错误”；
6. 填空题可以写参考答案文本；
7. 最后给出“导学案复杂度建议”，使用“基础版主文档建议 / 提升任务包建议 / 拓展挑战包建议”；
8. 明确写出“本前测用于判断学习起点，不作为正式考试成绩”。
9. 直接从标题正文开始，不要写“当然可以”“以下是”等对话式开头。
""".strip()

    guide_labels = {
        "guide_low": ("基础版导学案", "全班主文档，步骤更细、示例更多、提示更充分"),
        "guide_mid": ("提升任务包", "基础版之后的可选任务包，只生成 3—5 个提升任务"),
        "guide_high": ("拓展挑战包", "基础版之后的可选挑战包，只生成 2—3 个拓展挑战任务"),
    }
    if draft_type not in guide_labels:
        raise ValueError("不支持的导学草稿类型")

    label, version_focus = guide_labels[draft_type]
    if draft_type == "guide_mid":
        return f"""
{common_context}

请生成“提升任务包草稿”。它不是完整导学案，只作为基础版主文档之后的可选任务包。

要求：
- 直接输出正文，不要写“当然可以”“以下是”“好的”“我将为你”等对话式开头；
- 只生成 3—5 个提升任务，不要重复完整导学案结构；
- 适合已完成基础任务的学生；
- 不暗示学生端提交或自动评分已上线；
- 不做自动评分；
- 教师可按前测结果选择使用，不鼓励每节课默认生成所有任务包。

必须使用以下 Markdown 结构：

# {lesson_name}｜提升任务包草稿

## 使用建议
- 说明这是基础版导学案之后的可选补充；
- 提醒教师按需选择，不作为全班统一要求。

## 适用对象
- 已完成基础任务的学生；
- 需要进一步比较、解释、排错或表达的学生。

## 任务 1：变式练习
- 学生要做什么；
- 思考提示；
- 教师可调整点。

## 任务 2：错因分析
- 学生要做什么；
- 思考提示；
- 教师可调整点。

## 任务 3：比较解释
- 学生要做什么；
- 思考提示；
- 教师可调整点。

## 任务 4：小组讨论或排错
- 学生要做什么；
- 思考提示；
- 教师可调整点。

## 教师调整提示
- 本任务包为草稿，需教师审核、修改后使用；
- 不替代基础版导学案。
""".strip()

    if draft_type == "guide_high":
        return f"""
{common_context}

请生成“拓展挑战包草稿”。它不是完整导学案，只作为基础版主文档之后的可选挑战。

要求：
- 直接输出正文，不要写“当然可以”“以下是”“好的”“我将为你”等对话式开头；
- 只生成 2—3 个挑战任务，不要重复完整导学案结构；
- 适合兴趣小组、竞赛苗子或学有余力学生；
- 不暗示学生端提交或自动评分已上线。
- 不做自动评分；
- 教师可按前测结果选择使用，不鼓励每节课默认生成所有挑战包。

必须使用以下 Markdown 结构：

# {lesson_name}｜拓展挑战包草稿

## 使用建议
- 说明这是基础版导学案之后的可选拓展；
- 提醒教师结合课堂时间和学生基础选择使用。

## 适用对象
- 已较快完成基础任务的学生；
- 愿意尝试迁移、方案设计、排错或综合表达的学生。

## 挑战 1：迁移应用
- 问题情境；
- 完成要求；
- 可选提示；
- 教师可调整点。

## 挑战 2：开放问题
- 问题情境；
- 完成要求；
- 可选提示；
- 教师可调整点。

## 挑战 3：综合设计或竞赛启发
- 问题情境；
- 完成要求；
- 可选提示；
- 教师可调整点。

## 教师调整提示
- 本挑战包为草稿，需教师审核、修改后使用；
- 不作为全班统一要求。
""".strip()

    return f"""
{common_context}

请生成“{label}草稿”。它是面向全班学生使用的主文档，不是教师教案摘要。

版本要求：
- {version_focus}；
- 基础版导学案是全班主文档，建议优先生成和复核；
- 不暗示学生端提交或自动评分已上线；
- 直接输出正文，不要写“当然可以”“以下是”“好的”“我将为你”等对话式开头。

必须使用以下 Markdown 结构：

# {lesson_name}｜{label}草稿

## 学习导航
- 本课学习目标；
- 本课完成后能做什么；
- 教师确认提示。

## 学习情境
- 本课要解决什么问题；
- 为什么要学；
- 最后要完成什么任务。

## 知识要点
- 从知识主干中提炼关键概念；
- 用学生能理解的话表达；
- 不写成教师教案摘要。

## 边学边填
- 设计学生可填写的关键概念、步骤、判断题或短答；
- 留有空白或填写提示；
- 不要只有完整答案。

## 例题引路
- 如材料有例题则提取；
- 如材料没有例题，可以生成简单示例；
- 标注“教师可调整”。

## 仿做练习
- 举一反三的小练习；
- 面向课堂练习；
- 不做自动评分。

## 过程记录
- 操作步骤；
- 观察现象；
- 运行结果；
- 错误信息；
- 排查过程；
- 小组讨论结果。

## 重点速记
- 用几句学生容易记住的话总结重点；
- 不写成长篇总结。

## 带回小练
- 课后小练；
- 可作为后续自动批阅实验方向的来源；
- 本轮不实现自动批阅。

## 学习记录
- 学生心得；
- 疑问；
- 困难点；
- 需要教师帮助的问题。

## 学习自评
- [ ] 我能说出本课关键概念；
- [ ] 我能完成基础任务；
- [ ] 我能指出一个易错点；
- [ ] 我能遵守安全 / 规范要求；
- 我还需要老师帮助的是：……

## AI 草稿声明
以上内容为草稿，仅供教师审阅、修改、复制，不会自动发布给学生。教师应结合课程标准、学生基础和课堂实际确认后使用。
""".strip()
