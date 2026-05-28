"""课前学情测试与学生导学案生成 Prompt。"""

from __future__ import annotations

from app.models.knowledge_outline import KnowledgeOutline
from app.models.lesson import Lesson
from app.services.ai.sanitizer import sanitize_text_for_outline


LESSON_DRAFT_SYSTEM_MESSAGE = """
你是面向中职课堂的 AI 教学助理，只生成教师可编辑的草稿。
边界：
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
7. 最后给出“导学案复杂度建议”，使用“基础版建议 / 提升版建议 / 拓展版建议”；
8. 明确写出“本前测用于判断学习起点，不作为正式考试成绩”。
""".strip()

    guide_labels = {
        "guide_low": ("基础版导学案", "步骤更细、示例更多、提示更充分"),
        "guide_mid": ("提升版导学案", "保留关键提示，增加分析、比较、解释类任务"),
        "guide_high": ("拓展版导学案", "增加迁移应用、方案设计、排错和优化思考"),
    }
    if draft_type not in guide_labels:
        raise ValueError("不支持的导学草稿类型")

    label, version_focus = guide_labels[draft_type]
    return f"""
{common_context}

请生成“{label}草稿”。它是学生学习单，不是教师教案摘要。

版本要求：
- {version_focus}；
- 只使用基础版、提升版、拓展版这类温和命名；
- 不暗示学生端提交或自动评分已上线。

必须使用以下 Markdown 结构：

# {lesson_name}｜{label}草稿

## 学习导航
- 本课学习目标；
- 本课完成后能做什么；
- 教师确认提示。

## 任务导入
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
