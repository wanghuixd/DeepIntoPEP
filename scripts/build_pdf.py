#!/usr/bin/env python3
"""
Build a simple PDF document from repository Markdown files.

Default input: README.md (+ LICENSE if exists)
Default output: docs/DeepIntoPep.pdf
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Literal

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Flowable,
    ListFlowable,
    ListItem,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

# 默认中文字体路径（按优先级排序）
DEFAULT_CJK_FONT_PATHS: tuple[str, ...] = (
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/PingFang.ttc",  # macOS
    "/usr/share/fonts/truetype/arphic/uming.ttc",  # 文鼎字体
)

# 字体注册缓存
_FONT_REGISTERED: bool = False
_FONT_NAME: str = "Helvetica"


class BlockType(str, Enum):
    """Markdown 块类型枚举"""
    HEADING1 = "heading1"
    HEADING2 = "heading2"
    HEADING3 = "heading3"
    HEADING4 = "heading4"
    HEADING5 = "heading5"
    HEADING6 = "heading6"
    PARAGRAPH = "para"
    BULLETS = "bullets"
    ORDERED_LIST = "ordered_list"
    CODE = "code"
    QUOTE = "quote"


@dataclass(frozen=True)
class MdBlock:
    """Markdown 解析块"""
    kind: BlockType
    lines: list[str]
    language: str | None = None  # 代码块的语言标识符


def _pick_first_existing(paths: tuple[str, ...]) -> str | None:
    """查找第一个存在的路径"""
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def _register_font(font_name: str = "CJKFont") -> str:
    """
    注册中文字体（幂等操作，多次调用只注册一次）。
    
    Args:
        font_name: 注册的字体名称
        
    Returns:
        实际使用的字体名称（如果找不到中文字体则返回 "Helvetica"）
    """
    global _FONT_REGISTERED, _FONT_NAME
    
    if _FONT_REGISTERED:
        return _FONT_NAME
    
    font_path = _pick_first_existing(DEFAULT_CJK_FONT_PATHS)
    if not font_path:
        logger.warning(
            "未找到中文字体，将使用 Helvetica（可能无法正确显示中文）。"
            f"请安装中文字体或设置字体路径。尝试的路径: {DEFAULT_CJK_FONT_PATHS}"
        )
        _FONT_NAME = "Helvetica"
        _FONT_REGISTERED = True
        return _FONT_NAME
    
    try:
        if font_path.endswith(".ttc"):
            pdfmetrics.registerFont(TTFont(font_name, font_path, subfontIndex=0))
        else:
            pdfmetrics.registerFont(TTFont(font_name, font_path))
        logger.info(f"成功注册中文字体: {font_path}")
        _FONT_NAME = font_name
        _FONT_REGISTERED = True
        return font_name
    except Exception as e:
        logger.error(f"注册字体失败 {font_path}: {e}，将使用 Helvetica")
        _FONT_NAME = "Helvetica"
        _FONT_REGISTERED = True
        return "Helvetica"


class MarkdownParser:
    """Markdown 解析器"""
    
    def __init__(self) -> None:
        self.blocks: list[MdBlock] = []
        self.para_buf: list[str] = []
        self.bullet_buf: list[str] = []
        self.ordered_list_buf: list[str] = []
        self.quote_buf: list[str] = []
        self.code_lines: list[str] = []
        self.in_code = False
        self.code_language: str | None = None
    
    def flush_all(self) -> None:
        """刷新所有缓冲区"""
        self.flush_paragraph()
        self.flush_bullets()
        self.flush_ordered_list()
        self.flush_quotes()
    
    def flush_paragraph(self) -> None:
        """刷新段落缓冲区"""
        if not self.para_buf:
            return
        text = " ".join(s.strip() for s in self.para_buf).strip()
        if text:
            self.blocks.append(MdBlock(BlockType.PARAGRAPH, [text]))
        self.para_buf.clear()
    
    def flush_bullets(self) -> None:
        """刷新无序列表缓冲区"""
        if self.bullet_buf:
            self.blocks.append(MdBlock(BlockType.BULLETS, self.bullet_buf.copy()))
            self.bullet_buf.clear()
    
    def flush_ordered_list(self) -> None:
        """刷新有序列表缓冲区"""
        if self.ordered_list_buf:
            self.blocks.append(MdBlock(BlockType.ORDERED_LIST, self.ordered_list_buf.copy()))
            self.ordered_list_buf.clear()
    
    def flush_quotes(self) -> None:
        """刷新引用缓冲区"""
        if self.quote_buf:
            self.blocks.append(MdBlock(BlockType.QUOTE, [" ".join(self.quote_buf).strip()]))
            self.quote_buf.clear()
    
    def parse_heading(self, line: str) -> BlockType | None:
        """解析标题行，返回对应的 BlockType"""
        stripped = line.lstrip()
        if not stripped.startswith("#"):
            return None
        
        level = 0
        for char in stripped:
            if char == "#":
                level += 1
            else:
                break
        
        if level == 0 or level > 6:
            return None
        
        # 确保 # 后面有空格
        if len(stripped) <= level or stripped[level] != " ":
            return None
        
        heading_types = {
            1: BlockType.HEADING1,
            2: BlockType.HEADING2,
            3: BlockType.HEADING3,
            4: BlockType.HEADING4,
            5: BlockType.HEADING5,
            6: BlockType.HEADING6,
        }
        return heading_types[level]
    
    def parse(self, md: str) -> list[MdBlock]:
        """解析 Markdown 文本"""
        lines = md.splitlines()
        i = 0
        
        while i < len(lines):
            raw = lines[i]
            s = raw.rstrip("\n")
            
            # 处理代码块
            if s.strip().startswith("```"):
                if self.in_code:
                    # 结束代码块
                    language = self.code_language if self.code_language else None
                    self.blocks.append(MdBlock(BlockType.CODE, self.code_lines.copy(), language))
                    self.code_lines.clear()
                    self.code_language = None
                    self.in_code = False
                else:
                    # 开始代码块
                    self.flush_all()
                    # 提取语言标识符
                    lang_part = s.strip()[3:].strip()
                    if lang_part:
                        self.code_language = lang_part.split()[0]
                    self.in_code = True
                i += 1
                continue
            
            if self.in_code:
                self.code_lines.append(s)
                i += 1
                continue
            
            # 处理空行
            if not s.strip():
                self.flush_all()
                i += 1
                continue
            
            # 处理标题
            heading_type = self.parse_heading(s)
            if heading_type:
                self.flush_all()
                level = int(heading_type.value[-1])  # heading1 -> 1
                text = s.lstrip("#").lstrip().strip()
                self.blocks.append(MdBlock(heading_type, [text]))
                i += 1
                continue
            
            # 处理无序列表
            if s.lstrip().startswith("- ") or s.lstrip().startswith("* "):
                self.flush_paragraph()
                self.flush_quotes()
                self.flush_ordered_list()
                marker_len = 2
                self.bullet_buf.append(s.lstrip()[marker_len:].strip())
                i += 1
                continue
            
            # 处理有序列表
            stripped = s.lstrip()
            if stripped and stripped[0].isdigit():
                # 检查是否是 "数字. " 格式
                dot_pos = stripped.find(". ")
                if dot_pos > 0 and dot_pos < 10:  # 限制数字长度
                    try:
                        int(stripped[:dot_pos])
                        self.flush_paragraph()
                        self.flush_quotes()
                        self.flush_bullets()
                        self.ordered_list_buf.append(stripped[dot_pos + 2:].strip())
                        i += 1
                        continue
                    except ValueError:
                        pass
            
            # 处理引用
            if s.lstrip().startswith("> "):
                self.flush_paragraph()
                self.flush_bullets()
                self.flush_ordered_list()
                self.quote_buf.append(s.lstrip()[2:].strip())
                i += 1
                continue
            
            # 默认作为段落
            self.flush_bullets()
            self.flush_ordered_list()
            self.flush_quotes()
            self.para_buf.append(s)
            i += 1
        
        # 最后刷新所有缓冲区
        self.flush_all()
        
        return self.blocks


def parse_markdown(md: str) -> list[MdBlock]:
    """解析 Markdown 文本为块列表"""
    parser = MarkdownParser()
    return parser.parse(md)


@dataclass(frozen=True)
class PdfStyles:
    """PDF 样式集合"""
    font_name: str
    base: ParagraphStyle
    h1: ParagraphStyle
    h2: ParagraphStyle
    h3: ParagraphStyle
    h4: ParagraphStyle
    h5: ParagraphStyle
    h6: ParagraphStyle
    quote: ParagraphStyle
    code: ParagraphStyle


# 样式缓存
_STYLES_CACHE: PdfStyles | None = None


def _make_styles() -> PdfStyles:
    """创建 PDF 样式（带缓存）"""
    global _STYLES_CACHE
    
    if _STYLES_CACHE is not None:
        return _STYLES_CACHE
    
    font_name = _register_font()
    styles = getSampleStyleSheet()
    
    base = ParagraphStyle(
        "Base",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=11,
        leading=15,
        spaceAfter=6,
    )
    
    h1 = ParagraphStyle(
        "H1",
        parent=base,
        fontSize=20,
        leading=26,
        spaceBefore=6,
        spaceAfter=12,
    )
    
    h2 = ParagraphStyle(
        "H2",
        parent=base,
        fontSize=15,
        leading=20,
        spaceBefore=10,
        spaceAfter=8,
        textColor=colors.HexColor("#222222"),
    )
    
    h3 = ParagraphStyle(
        "H3",
        parent=base,
        fontSize=12.5,
        leading=17,
        spaceBefore=8,
        spaceAfter=6,
        textColor=colors.HexColor("#333333"),
    )
    
    h4 = ParagraphStyle(
        "H4",
        parent=base,
        fontSize=11.5,
        leading=16,
        spaceBefore=6,
        spaceAfter=5,
        textColor=colors.HexColor("#444444"),
    )
    
    h5 = ParagraphStyle(
        "H5",
        parent=base,
        fontSize=11,
        leading=15,
        spaceBefore=5,
        spaceAfter=4,
        textColor=colors.HexColor("#555555"),
    )
    
    h6 = ParagraphStyle(
        "H6",
        parent=base,
        fontSize=10.5,
        leading=14,
        spaceBefore=4,
        spaceAfter=3,
        textColor=colors.HexColor("#666666"),
    )
    
    quote = ParagraphStyle(
        "Quote",
        parent=base,
        leftIndent=10,
        textColor=colors.HexColor("#555555"),
        backColor=colors.whitesmoke,
        borderPadding=6,
        spaceBefore=6,
        spaceAfter=8,
    )
    
    code = ParagraphStyle(
        "Code",
        parent=base,
        fontName=font_name,
        fontSize=9.5,
        leading=13,
        backColor=colors.HexColor("#f7f7f7"),
        borderPadding=6,
        leftIndent=6,
        rightIndent=6,
        spaceBefore=6,
        spaceAfter=8,
    )
    
    _STYLES_CACHE = PdfStyles(
        font_name=font_name,
        base=base,
        h1=h1,
        h2=h2,
        h3=h3,
        h4=h4,
        h5=h5,
        h6=h6,
        quote=quote,
        code=code,
    )
    
    return _STYLES_CACHE


def _append_markdown(story: list[Flowable], markdown_text: str, title: str) -> None:
    """将 Markdown 文本转换为 PDF 流元素并添加到 story"""
    s = _make_styles()
    blocks = parse_markdown(markdown_text)

    # 如果 Markdown 不以 H1 开头，添加标题
    if not blocks or blocks[0].kind != BlockType.HEADING1:
        story.append(Paragraph(title, s.h1))
        story.append(Spacer(1, 4))

    for b in blocks:
        if b.kind == BlockType.HEADING1:
            story.append(Paragraph(b.lines[0], s.h1))
        elif b.kind == BlockType.HEADING2:
            story.append(Paragraph(b.lines[0], s.h2))
        elif b.kind == BlockType.HEADING3:
            story.append(Paragraph(b.lines[0], s.h3))
        elif b.kind == BlockType.HEADING4:
            story.append(Paragraph(b.lines[0], s.h4))
        elif b.kind == BlockType.HEADING5:
            story.append(Paragraph(b.lines[0], s.h5))
        elif b.kind == BlockType.HEADING6:
            story.append(Paragraph(b.lines[0], s.h6))
        elif b.kind == BlockType.PARAGRAPH:
            story.append(Paragraph(_escape_for_paragraph(b.lines[0]), s.base))
        elif b.kind == BlockType.QUOTE:
            story.append(Paragraph(_escape_for_paragraph(b.lines[0]), s.quote))
        elif b.kind == BlockType.CODE:
            code_text = "\n".join(b.lines).rstrip()
            if b.language:
                # 可以在这里添加语言标识符的显示
                pass
            story.append(Preformatted(code_text, s.code))
        elif b.kind == BlockType.BULLETS:
            items = [
                ListItem(Paragraph(_escape_for_paragraph(x), s.base), leftIndent=0)
                for x in b.lines
            ]
            story.append(
                ListFlowable(
                    items,
                    bulletType="bullet",
                    start="circle",
                    leftIndent=14,
                    bulletFontName=s.font_name,
                )
            )
            story.append(Spacer(1, 2))
        elif b.kind == BlockType.ORDERED_LIST:
            items = [
                ListItem(Paragraph(_escape_for_paragraph(x), s.base), leftIndent=0)
                for x in b.lines
            ]
            story.append(
                ListFlowable(
                    items,
                    bulletType="1",
                    start="1",
                    leftIndent=14,
                    bulletFontName=s.font_name,
                )
            )
            story.append(Spacer(1, 2))


def _append_text_as_code(story: list[Flowable], text: str, section_title: str) -> None:
    """将文本作为代码块添加到 story"""
    s = _make_styles()
    story.append(Spacer(1, 10))
    story.append(Paragraph(section_title, s.h2))
    story.append(Preformatted(text.rstrip(), s.code))


def build_pdf_from_files(input_paths: list[Path], output_path: Path, title: str) -> None:
    """
    从多个文件构建 PDF 文档
    
    Args:
        input_paths: 输入文件路径列表
        output_path: 输出 PDF 路径
        title: PDF 标题
        
    Raises:
        FileNotFoundError: 输入文件不存在
        IOError: 文件读取或 PDF 生成失败
    """
    if not input_paths:
        raise ValueError("至少需要一个输入文件")
    
    # 预注册字体（幂等操作）
    _register_font()
    
    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=title,
        author="DeepIntoPep",
    )

    story: list[Flowable] = []
    processed_count = 0

    for p in input_paths:
        if not p.exists():
            logger.warning(f"文件不存在，跳过: {p}")
            continue
        
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.error(f"读取文件失败 {p}: {e}")
            raise IOError(f"无法读取文件 {p}: {e}") from e
        
        if processed_count > 0:
            story.append(Spacer(1, 14))
        
        if p.name.upper() == "LICENSE":
            _append_text_as_code(story, content, "LICENSE")
        else:
            _append_markdown(story, content, title=p.name)
        
        processed_count += 1
        logger.info(f"已处理文件: {p.name}")

    if processed_count == 0:
        raise ValueError("没有成功处理任何文件")
    
    try:
        doc.build(story)
        logger.info(f"PDF 生成成功: {output_path}")
    except Exception as e:
        logger.error(f"PDF 生成失败: {e}")
        raise IOError(f"PDF 生成失败: {e}") from e


def _escape_for_paragraph(text: str) -> str:
    """
    转义文本中的特殊字符，以便在 reportlab Paragraph 中安全使用。
    reportlab Paragraph 使用迷你 HTML 解析器，需要转义基本字符。
    """
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\t", "    ")
    )


def main() -> int:
    """主函数"""
    parser = argparse.ArgumentParser(
        description="从 Markdown 文件生成 PDF 文档",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input",
        action="append",
        metavar="FILE",
        help="输入文件（可重复指定）。如果未指定，默认使用 README.md（如果存在 LICENSE 也会包含）",
    )
    parser.add_argument(
        "--output",
        default="docs/DeepIntoPep.pdf",
        metavar="PATH",
        help="PDF 输出路径（默认: docs/DeepIntoPep.pdf）",
    )
    parser.add_argument(
        "--title",
        default="DeepIntoPep",
        metavar="TITLE",
        help="PDF 标题（默认: DeepIntoPep）",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="显示详细日志",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    repo_root = Path(__file__).resolve().parents[1]
    output_path = (repo_root / args.output).resolve()

    if args.input:
        input_paths = [(repo_root / p).resolve() for p in args.input]
    else:
        input_paths = [(repo_root / "README.md").resolve()]
        license_path = (repo_root / "LICENSE").resolve()
        if license_path.exists():
            input_paths.append(license_path)

    try:
        build_pdf_from_files(input_paths, output_path, args.title)
        print(f"✓ PDF 已生成: {output_path}")
        return 0
    except (ValueError, IOError, FileNotFoundError) as e:
        logger.error(str(e))
        print(f"✗ 错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.exception("未预期的错误")
        print(f"✗ 未预期的错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

