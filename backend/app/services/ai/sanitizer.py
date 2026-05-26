"""AI 生成前的教学材料脱敏工具。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Protocol

SENSITIVE_FIELD_NAMES = (
    "学校",
    "学校名称",
    "院校",
    "单位",
    "教师",
    "任课教师",
    "授课教师",
    "任课老师",
    "主讲教师",
    "班级",
    "授课班级",
    "教学班",
    "行政班",
    "教研组",
    "授课地点",
    "授课日期",
    "学号",
    "姓名",
    "手机号",
    "身份证号",
    "API Key",
    "Api Key",
    "Token",
    "密码",
)
_FIELD_PATTERN_TEXT = "|".join(re.escape(field) for field in sorted(SENSITIVE_FIELD_NAMES, key=len, reverse=True))
SENSITIVE_FIELD_LINE_PATTERN = re.compile(
    rf"^\s*(?:{_FIELD_PATTERN_TEXT})\s*(?:[:：|\-—\s\t　]+).+",
    re.IGNORECASE,
)
SENSITIVE_INLINE_PATTERN = re.compile(
    rf"(?:{_FIELD_PATTERN_TEXT})\s*(?:[:：|\-—\s\t　]+)\S+",
    re.IGNORECASE,
)
PHONE_PATTERN = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
ID_CARD_PATTERN = re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")
CLASS_NAME_PATTERN = re.compile(r"(?<![A-Za-z0-9])\d{2,4}[\u4e00-\u9fa5A-Za-z]{1,20}\d*班(?![A-Za-z0-9])")
TEACHER_NAME_PATTERN = re.compile(r"(?<![\u4e00-\u9fa5])[\u4e00-\u9fa5]{1,3}老师")
API_KEY_PATTERN = re.compile(r"\b(?:sk|sk-ant|ds)-[A-Za-z0-9_-]{8,}\b", re.IGNORECASE)
TOKEN_PATTERN = re.compile(r"\b(?:token|bearer)\s+['\"]?[A-Za-z0-9._-]{12,}['\"]?", re.IGNORECASE)
PASSWORD_INLINE_PATTERN = re.compile(r"(?:密码|password)\s*(?:[:：=|\-—\s\t　]+)\S+", re.IGNORECASE)


class LessonLike(Protocol):
    """知识主干生成需要的课次字段。"""

    lesson_code: str
    title: str
    content_summary: str


class MaterialLike(Protocol):
    """知识主干生成需要的材料字段。"""

    content: str


@dataclass(frozen=True)
class SanitizedLessonContext:
    """脱敏后的课次上下文。"""

    lesson_code: str
    title: str
    content_summary: str


@dataclass(frozen=True)
class SanitizedMaterialContext:
    """脱敏后的材料上下文。"""

    content: str


def sanitize_text_for_outline(text: str | None) -> str:
    """过滤不应进入 AI prompt 的行政信息和个人信息。"""

    sanitized_lines: list[str] = []
    for raw_line in (text or "").splitlines():
        line = re.sub(r"[ \t　]+", " ", raw_line.strip())
        if not line:
            continue
        # 常见于教案封面、表格左列或表格提取后的“字段 | 内容”格式，整行删除更安全。
        if SENSITIVE_FIELD_LINE_PATTERN.match(line):
            continue
        line = API_KEY_PATTERN.sub("[疑似密钥已移除]", line)
        line = TOKEN_PATTERN.sub("[疑似 Token 已移除]", line)
        line = PASSWORD_INLINE_PATTERN.sub("[密码信息已移除]", line)
        line = PHONE_PATTERN.sub("[已过滤手机号]", line)
        line = ID_CARD_PATTERN.sub("[已过滤身份证号]", line)
        line = CLASS_NAME_PATTERN.sub("某班级", line)
        line = TEACHER_NAME_PATTERN.sub("某教师", line)
        line = SENSITIVE_INLINE_PATTERN.sub("[已过滤行政信息]", line)
        sanitized_lines.append(line)
    return "\n".join(sanitized_lines)


def sanitize_lesson_for_outline(lesson: LessonLike) -> SanitizedLessonContext:
    """生成不会修改原始 Lesson 的脱敏课次上下文。"""

    return SanitizedLessonContext(
        lesson_code=sanitize_text_for_outline(getattr(lesson, "lesson_code", "")),
        title=sanitize_text_for_outline(getattr(lesson, "title", "")),
        content_summary=sanitize_text_for_outline(getattr(lesson, "content_summary", "")),
    )


def sanitize_materials_for_outline(materials: Iterable[MaterialLike]) -> list[SanitizedMaterialContext]:
    """生成不会修改原始 LessonMaterial 的脱敏材料上下文。"""

    return [
        SanitizedMaterialContext(content=sanitize_text_for_outline(getattr(material, "content", "")))
        for material in materials
    ]
