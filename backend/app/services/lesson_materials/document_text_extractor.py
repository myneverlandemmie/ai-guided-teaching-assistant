"""课次教学材料文本提取工具。

只做教师常见教学材料的基础文本提取，不做 OCR、PDF 解析或版式还原。
"""

from __future__ import annotations

import re
from pathlib import Path

try:
    from docx import Document
    from docx.table import Table, _Cell
    from docx.text.paragraph import Paragraph
except ImportError:  # pragma: no cover - 缺依赖时由调用方显示错误
    Document = None
    Table = None
    _Cell = None
    Paragraph = None

try:
    from pptx import Presentation
except ImportError:  # pragma: no cover - 缺依赖时由调用方显示错误
    Presentation = None


SUPPORTED_MATERIAL_SUFFIXES = {".txt", ".md", ".docx", ".pptx"}
FOOTER_PATTERNS = (
    re.compile(r"©\s*Microsoft Corporation", re.IGNORECASE),
    re.compile(r"All rights reserved", re.IGNORECASE),
    re.compile(r"^\d{4}[/-]\d{1,2}[/-]\d{1,2}(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?$"),
    re.compile(r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?$"),
)


class LessonMaterialExtractionError(ValueError):
    """教学材料文本提取失败。"""


def clean_extracted_text(text: str) -> str:
    """清洗提取文本，减少模板噪声但保留教学内容。

    Args:
        text: 从文档中提取的原始文本。

    Returns:
        清理空白、明显页脚、重复空行和整行重复后的文本。

    Raises:
        不主动抛出业务异常。
    """

    cleaned_lines: list[str] = []
    previous_line = ""
    previous_blank = False
    for raw_line in text.splitlines():
        line = re.sub(r"[ \t\f\v]+", " ", raw_line).strip()
        # Word 表格标签常被拆成“重 点”“难 点”，这里仅规范化明确的教学栏目名。
        line = re.sub(r"^重\s*点\s*([:：])?", "重点：", line)
        line = re.sub(r"^难\s*点\s*([:：])?", "难点：", line)
        if any(pattern.search(line) for pattern in FOOTER_PATTERNS):
            continue
        if not line:
            if cleaned_lines and not previous_blank:
                cleaned_lines.append("")
            previous_blank = True
            previous_line = ""
            continue
        if line == previous_line:
            continue
        cleaned_lines.append(line)
        previous_line = line
        previous_blank = False

    return "\n".join(cleaned_lines).strip()


def _iter_docx_blocks(document: object):
    """按 Word 文档主体顺序产出段落和表格。"""

    if Paragraph is None or Table is None:
        return
    for child in document.element.body.iterchildren():
        if child.tag.endswith("}p"):
            yield Paragraph(child, document)
        elif child.tag.endswith("}tbl"):
            yield Table(child, document)


def _extract_docx_cell_text(cell: object) -> str:
    """提取 Word 表格单元格内的多段文本。"""

    paragraphs = [paragraph.text.strip() for paragraph in cell.paragraphs if paragraph.text.strip()]
    return "\n".join(paragraphs).strip()


def _extract_docx_table_text(table: object) -> list[str]:
    """提取 Word 表格文本，按行组织并仅在行内跳过合并单元格重复。"""

    parts: list[str] = []
    for row in table.rows:
        cells: list[str] = []
        seen_cell_xml_in_row: set[str] = set()
        for cell in row.cells:
            cell_key = str(cell._tc.xml)
            if cell_key in seen_cell_xml_in_row:
                continue
            seen_cell_xml_in_row.add(cell_key)
            text = _extract_docx_cell_text(cell)
            if text:
                cells.append(text)
        if not cells:
            continue
        if len(cells) == 2:
            parts.append(f"{cells[0]}：\n{cells[1]}")
        else:
            parts.append("\n---\n".join(cells))
    return parts


def extract_text_from_docx(file_path: str | Path) -> str:
    """从 `.docx` 中提取段落和表格单元格文本。

    Args:
        file_path: `.docx` 文件路径。

    Returns:
        清洗后的文本。

    Raises:
        LessonMaterialExtractionError: 缺少依赖、文件无法解析或未提取到文本。
    """

    if Document is None:
        raise LessonMaterialExtractionError("缺少 python-docx 依赖，无法解析 .docx。")

    try:
        document = Document(str(file_path))
    except Exception as exc:  # noqa: BLE001 - 需要转成教师可理解的错误
        raise LessonMaterialExtractionError(".docx 文本提取失败，请复制 Word 中的文字粘贴到文本框。") from exc

    parts: list[str] = []
    for block in _iter_docx_blocks(document):
        if Paragraph is not None and isinstance(block, Paragraph):
            if block.text.strip():
                parts.append(block.text)
        elif Table is not None and isinstance(block, Table):
            # Word 教案常把教学目标、过程等内容放在表格中，按表格出现位置提取。
            parts.extend(_extract_docx_table_text(block))

    text = clean_extracted_text("\n".join(parts))
    if not text:
        raise LessonMaterialExtractionError("未从 .docx 中提取到可用文本，请复制 Word 中的文字粘贴到文本框。")
    return text


def _extract_text_from_pptx_shape(shape: object) -> list[str]:
    """提取单个 PPT shape 中的文本。"""

    parts: list[str] = []
    if getattr(shape, "has_text_frame", False):
        text = getattr(shape, "text", "").strip()
        if text:
            parts.append(text)
    if getattr(shape, "has_table", False):
        for row in shape.table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                parts.append("\t".join(cells))
    return parts


def extract_text_from_pptx(file_path: str | Path) -> str:
    """从 `.pptx` 中按幻灯片顺序提取文本框和表格文本。

    Args:
        file_path: `.pptx` 文件路径。

    Returns:
        清洗后的文本，每页包含 `【Slide n】` 标记。

    Raises:
        LessonMaterialExtractionError: 缺少依赖、文件无法解析或未提取到文本。
    """

    if Presentation is None:
        raise LessonMaterialExtractionError("缺少 python-pptx 依赖，无法解析 .pptx。")

    try:
        presentation = Presentation(str(file_path))
    except Exception as exc:  # noqa: BLE001 - 需要转成教师可理解的错误
        raise LessonMaterialExtractionError(".pptx 文本提取失败，请复制 PPT 中的文字粘贴到文本框。") from exc

    slide_blocks: list[str] = []
    for index, slide in enumerate(presentation.slides, start=1):
        slide_parts: list[str] = []
        for shape in slide.shapes:
            slide_parts.extend(_extract_text_from_pptx_shape(shape))
        slide_text = clean_extracted_text("\n".join(slide_parts))
        if slide_text:
            slide_blocks.append(f"【Slide {index}】\n{slide_text}")

    text = clean_extracted_text("\n\n".join(slide_blocks))
    if not text:
        raise LessonMaterialExtractionError("未从 .pptx 中提取到可用文本，请复制 PPT 中的文字粘贴到文本框。")
    return text


def extract_text_from_lesson_material(file_path: str | Path, filename: str) -> str:
    """按文件扩展名提取课次材料文本。

    Args:
        file_path: 已保存的上传文件路径。
        filename: 原始文件名，用于判断扩展名。

    Returns:
        清洗后的文本。

    Raises:
        LessonMaterialExtractionError: 文件类型不支持或解析失败。
    """

    path = Path(file_path)
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_MATERIAL_SUFFIXES:
        raise LessonMaterialExtractionError(
            "当前支持粘贴文本或上传 .txt / .md / .docx / .pptx 文件；暂不支持 PDF、图片、扫描件和旧版 .doc / .ppt。"
        )
    if suffix in {".txt", ".md"}:
        return clean_extracted_text(path.read_text(encoding="utf-8", errors="replace"))
    if suffix == ".docx":
        return extract_text_from_docx(path)
    if suffix == ".pptx":
        return extract_text_from_pptx(path)
    raise LessonMaterialExtractionError("不支持的教学材料文件类型。")
