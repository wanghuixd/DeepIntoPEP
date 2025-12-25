#!/usr/bin/env python3
"""
Build a simple PDF document from repository Markdown files.

Default input: README.md (+ LICENSE if exists)
Default output: docs/DeepIntoPep.pdf
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
)


DEFAULT_CJK_FONT_PATHS: tuple[str, ...] = (
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
)


def _pick_first_existing(paths: tuple[str, ...]) -> str | None:
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def _register_font(font_name: str = "CJKFont") -> str:
    """
    Register a font that can render Chinese characters.
    Prefer TTF. TTC also works with recent reportlab (subfontIndex=0).
    """

    font_path = _pick_first_existing(DEFAULT_CJK_FONT_PATHS)
    if not font_path:
        # Fall back to Helvetica; will likely not render CJK well.
        return "Helvetica"

    if font_path.endswith(".ttc"):
        pdfmetrics.registerFont(TTFont(font_name, font_path, subfontIndex=0))
    else:
        pdfmetrics.registerFont(TTFont(font_name, font_path))
    return font_name


@dataclass(frozen=True)
class MdBlock:
    kind: str  # heading1/heading2/heading3/para/bullets/code/quote
    lines: list[str]


def parse_markdown(md: str) -> list[MdBlock]:
    blocks: list[MdBlock] = []
    lines = md.splitlines()

    i = 0
    in_code = False
    code_lines: list[str] = []

    def flush_para(buf: list[str]) -> None:
        if not buf:
            return
        text = " ".join(s.strip() for s in buf).strip()
        if text:
            blocks.append(MdBlock("para", [text]))
        buf.clear()

    para_buf: list[str] = []
    bullet_buf: list[str] = []
    quote_buf: list[str] = []

    def flush_bullets() -> None:
        nonlocal bullet_buf
        if bullet_buf:
            blocks.append(MdBlock("bullets", bullet_buf))
            bullet_buf = []

    def flush_quotes() -> None:
        nonlocal quote_buf
        if quote_buf:
            blocks.append(MdBlock("quote", [" ".join(quote_buf).strip()]))
            quote_buf = []

    while i < len(lines):
        raw = lines[i]
        s = raw.rstrip("\n")

        if s.strip().startswith("```"):
            if in_code:
                blocks.append(MdBlock("code", code_lines))
                code_lines = []
                in_code = False
            else:
                flush_para(para_buf)
                flush_bullets()
                flush_quotes()
                in_code = True
            i += 1
            continue

        if in_code:
            code_lines.append(s)
            i += 1
            continue

        if not s.strip():
            flush_para(para_buf)
            flush_bullets()
            flush_quotes()
            i += 1
            continue

        if s.startswith("# "):
            flush_para(para_buf)
            flush_bullets()
            flush_quotes()
            blocks.append(MdBlock("heading1", [s[2:].strip()]))
            i += 1
            continue
        if s.startswith("## "):
            flush_para(para_buf)
            flush_bullets()
            flush_quotes()
            blocks.append(MdBlock("heading2", [s[3:].strip()]))
            i += 1
            continue
        if s.startswith("### "):
            flush_para(para_buf)
            flush_bullets()
            flush_quotes()
            blocks.append(MdBlock("heading3", [s[4:].strip()]))
            i += 1
            continue

        if s.lstrip().startswith("- "):
            flush_para(para_buf)
            flush_quotes()
            bullet_buf.append(s.lstrip()[2:].strip())
            i += 1
            continue

        if s.lstrip().startswith("> "):
            flush_para(para_buf)
            flush_bullets()
            quote_buf.append(s.lstrip()[2:].strip())
            i += 1
            continue

        # default paragraph
        flush_bullets()
        flush_quotes()
        para_buf.append(s)
        i += 1

    flush_para(para_buf)
    flush_bullets()
    flush_quotes()

    return blocks


@dataclass(frozen=True)
class PdfStyles(object):
    font_name: str
    base: ParagraphStyle
    h1: ParagraphStyle
    h2: ParagraphStyle
    h3: ParagraphStyle
    quote: ParagraphStyle
    code: ParagraphStyle


def _make_styles() -> PdfStyles:
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
    return PdfStyles(
        font_name=font_name, base=base, h1=h1, h2=h2, h3=h3, quote=quote, code=code
    )


def _append_markdown(story: list[object], markdown_text: str, title: str) -> None:
    s = _make_styles()
    blocks = parse_markdown(markdown_text)

    # Ensure a title at top if Markdown doesn't start with heading1.
    if not blocks or blocks[0].kind != "heading1":
        story.append(Paragraph(title, s.h1))
        story.append(Spacer(1, 4))

    for b in blocks:
        if b.kind == "heading1":
            story.append(Paragraph(b.lines[0], s.h1))
        elif b.kind == "heading2":
            story.append(Paragraph(b.lines[0], s.h2))
        elif b.kind == "heading3":
            story.append(Paragraph(b.lines[0], s.h3))
        elif b.kind == "para":
            story.append(Paragraph(_escape_for_paragraph(b.lines[0]), s.base))
        elif b.kind == "quote":
            story.append(Paragraph(_escape_for_paragraph(b.lines[0]), s.quote))
        elif b.kind == "code":
            story.append(Preformatted("\n".join(b.lines).rstrip(), s.code))
        elif b.kind == "bullets":
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


def _append_text_as_code(story: list[object], text: str, section_title: str) -> None:
    s = _make_styles()
    story.append(Spacer(1, 10))
    story.append(Paragraph(section_title, s.h2))
    story.append(Preformatted(text.rstrip(), s.code))


def build_pdf_from_files(input_paths: list[Path], output_path: Path, title: str) -> None:
    # Register font once (idempotent). Styles creation will reuse it.
    _register_font()

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

    story: list[object] = []

    first = True
    for p in input_paths:
        if not p.exists():
            continue
        content = p.read_text(encoding="utf-8", errors="replace")
        if not first:
            story.append(Spacer(1, 14))
        first = False

        if p.name.upper() == "LICENSE":
            _append_text_as_code(story, content, "LICENSE")
        else:
            _append_markdown(story, content, title=p.name)

    doc.build(story)


def _escape_for_paragraph(text: str) -> str:
    # reportlab Paragraph uses a mini-HTML parser; escape basic characters.
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\t", "    ")
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        action="append",
        help="Input file. Repeatable. If omitted, uses README.md (+ LICENSE if exists).",
    )
    parser.add_argument(
        "--output",
        default="docs/DeepIntoPep.pdf",
        help="PDF output path (default: docs/DeepIntoPep.pdf)",
    )
    parser.add_argument("--title", default="DeepIntoPep", help="PDF title")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    output_path = (repo_root / args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.input:
        input_paths = [(repo_root / p).resolve() for p in args.input]
    else:
        input_paths = [(repo_root / "README.md").resolve()]
        license_path = (repo_root / "LICENSE").resolve()
        if license_path.exists():
            input_paths.append(license_path)

    build_pdf_from_files(input_paths, output_path, args.title)
    print(f"Wrote: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

