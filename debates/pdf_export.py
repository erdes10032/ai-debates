from __future__ import annotations

from pathlib import Path

from django.db.models import QuerySet
from django.utils.text import get_valid_filename
from django.utils.translation import gettext as _
from fpdf import FPDF
from fpdf.enums import XPos, YPos

from debates.markdown_tables import (
    collect_markdown_table,
    is_markdown_table_start,
    is_table_data_row,
    is_table_separator_row,
    parse_md_table_row,
)
from debates.markdown_utils import prepare_debate_markdown
from debates.models import Debate


def build_debate_pdf_filename(*, debate: Debate) -> str:
    topic = debate.topic.strip() or _('no_topic')
    topic_slug = topic.replace(' ', '_')
    topic_slug = get_valid_filename(topic_slug)

    debate_number = (
        Debate.objects.filter(
            user=debate.user,
            topic=debate.topic,
            id__lte=debate.id,
        ).count()
    )
    filename = _(
        'Debates_({topic})_{number}.pdf'
    ).format(
        topic=topic_slug,
        number=debate_number,
    )
    return get_valid_filename(filename)


def render_debate_history_pdf(*, debate: Debate) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    font_path = _resolve_unicode_font_path()
    pdf.add_font('main', style='', fname=str(font_path))
    pdf.set_font('main', size=14)

    content_width = pdf.epw

    pdf.multi_cell(
        content_width,
        8,
        text=_pdf_text(_('Debate history')),
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.set_font('main', size=12)
    pdf.multi_cell(
        content_width,
        7,
        text=_pdf_text(f"{_('Topic')}: {debate.topic}"),
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.multi_cell(
        content_width,
        7,
        text=_pdf_text(
            f"{_('Status')}: {debate.get_status_display()}",
        ),
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(2)

    messages: QuerySet = (
        debate.messages.select_related('round').order_by('round__number', 'created_at')
    )
    current_round: int | None = None
    for message in messages:
        if current_round != message.round.number:
            current_round = message.round.number
            pdf.set_font('main', size=12)
            pdf.ln(2)
            pdf.multi_cell(
                content_width,
                8,
                text=_pdf_text(f"{_('Round')} {current_round}"),
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
        pdf.set_font('main', size=11)
        pdf.multi_cell(
            content_width,
            6,
            text=_pdf_text(
                f"{message.speaker_label} ({message.role_name})"
            ),
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        pdf.multi_cell(
            content_width,
            6,
            text=_pdf_text(message.content),
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        pdf.ln(1)

    if debate.consensus:
        pdf.ln(2)
        _write_markdown_to_pdf(
            pdf,
            title=_('Consensus'),
            markdown_text=debate.consensus,
        )

    raw_content = pdf.output(dest='S')
    if isinstance(raw_content, bytearray):
        return bytes(raw_content)
    if isinstance(raw_content, bytes):
        return raw_content
    return raw_content.encode('latin-1')


def _resolve_unicode_font_path() -> Path:
    module_dir = Path(__file__).resolve().parent
    candidates = (
        module_dir / 'fonts' / 'DejaVuSans.ttf',
        Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
        Path('C:/Windows/Fonts/arial.ttf'),
        Path('C:/Windows/Fonts/segoeui.ttf'),
        Path('/Library/Fonts/Arial Unicode.ttf'),
        Path('/Library/Fonts/Arial.ttf'),
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        'Cannot find a unicode-compatible system font for PDF export.'
    )


def _pdf_text(value: str) -> str:
    """
    Normalize text before putting it into PDF.

    The "missing hyphen" squares are usually not ASCII '-' but one of:
    - en-dash (U+2013), em-dash (U+2014), minus (U+2212)
    Some system fonts or the PDF font subset may not contain them.
    """
    return (
        (value or '')
        .replace('\u00a0', ' ')
        .replace('\u2009', ' ')
        .replace('\u2010', '-')  # hyphen
        .replace('\u2011', '-')  # non-breaking hyphen
        .replace('\u2012', '-')  # figure dash
        .replace('\u2013', '-')  # en dash
        .replace('\u2014', '-')  # em dash
        .replace('\u2212', '-')  # minus sign
        .replace('\ufeff', '')
    )


def _write_markdown_to_pdf(
    pdf: FPDF,
    *,
    title: str,
    markdown_text: str,
) -> None:
    pdf.set_font('main', size=12)
    pdf.multi_cell(
        pdf.epw,
        8,
        text=_pdf_text(title),
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(1)

    lines = prepare_debate_markdown(markdown_text or '').splitlines()
    i = 0
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if not paragraph:
            return
        plain = _strip_inline_markdown('\n'.join(paragraph).strip())
        pdf.set_font('main', size=11)
        pdf.multi_cell(
            pdf.epw,
            6,
            text=_pdf_text(plain),
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        pdf.ln(1)
        paragraph = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith('#'):
            flush_paragraph()
            hashes = len(stripped) - len(stripped.lstrip('#'))
            heading = _strip_inline_markdown(stripped.lstrip('#').strip())
            size = 14 if hashes == 1 else 13 if hashes == 2 else 12
            pdf.set_font('main', size=size)
            pdf.multi_cell(
                pdf.epw,
                7,
                text=_pdf_text(heading),
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
            pdf.ln(1)
            i += 1
            continue

        if is_markdown_table_start(lines, i):
            flush_paragraph()
            table_lines, i = collect_markdown_table(lines, i)
            _draw_markdown_table(pdf, table_lines)
            pdf.ln(2)
            continue

        if not stripped:
            flush_paragraph()
            i += 1
            continue

        paragraph.append(line)
        i += 1

    flush_paragraph()


def _wrap_long_word(
    pdf: FPDF,
    word: str,
    max_width: float,
) -> list[str]:
    chunks: list[str] = []
    current = ''

    for char in word:
        candidate = f'{current}{char}'

        if (
            current
            and pdf.get_string_width(candidate) > max_width
        ):
            chunks.append(current)
            current = char
            continue

        current = candidate

    if current:
        chunks.append(current)

    return chunks or ['']


def _strip_inline_markdown(value: str) -> str:
    text = value or ''
    return text.replace('**', '').replace('__', '').replace('`', '')


def _draw_markdown_table(pdf: FPDF, table_lines: list[str]) -> None:
    header = [
        _strip_inline_markdown(cell)
        for cell in parse_md_table_row(table_lines[0])
    ]
    body_rows = [
        [
            _strip_inline_markdown(cell)
            for cell in parse_md_table_row(row)
        ]
        for row in table_lines[2:]
    ]
    col_count = max(len(header), 1)
    header += [''] * (col_count - len(header))

    normalized_rows = []
    for row in body_rows:
        if len(row) > col_count:
            # Match markdown table behavior used on the site:
            # extra cells beyond header width are ignored.
            row = row[:col_count]
        normalized_rows.append(row + [''] * (col_count - len(row)))

    usable_width = pdf.epw
    col_w = usable_width / col_count
    line_h = 5.4
    pad_x = 1.2
    pad_y = 1.2
    min_cell_width = 8.0

    def wrap_text(text: str, max_width: float) -> list[str]:
        safe_width = max(max_width, min_cell_width)
        normalized = _pdf_text(text)

        if not normalized.strip():
            return ['']

        if pdf.get_string_width(normalized) <= safe_width:
            return [normalized]

        words = normalized.split()
        if not words:
            return ['']

        result: list[str] = []
        current = words[0]

        if pdf.get_string_width(current) > safe_width:
            result.extend(
                _wrap_long_word(
                    pdf,
                    current,
                    safe_width,
                ),
            )
            current = ''

        for word in words[1:]:
            if pdf.get_string_width(word) > safe_width:
                if current:
                    result.append(current)
                    current = ''

                result.extend(
                    _wrap_long_word(
                        pdf,
                        word,
                        safe_width,
                    ),
                )
                continue

            candidate = f'{current} {word}'.strip()

            if (
                not current
                or pdf.get_string_width(candidate) <= safe_width
            ):
                current = candidate
            else:
                result.append(current)
                current = word

        if current:
            result.append(current)

        return result or ['']

    def draw_row(cells: list[str]) -> None:
        cell_inner_width = max(
            col_w - (2 * pad_x),
            min_cell_width,
        )
        wrapped_cells = [
            wrap_text(cell, cell_inner_width)
            for cell in cells
        ]
        row_h = (
            max(len(lines_) for lines_ in wrapped_cells) * line_h
            + (2 * pad_y)
        )
        if pdf.get_y() + row_h > pdf.page_break_trigger:
            pdf.add_page()
            pdf.set_font('main', size=11)

        x0 = pdf.l_margin
        y0 = pdf.get_y()
        for idx, lines_ in enumerate(wrapped_cells):
            x = x0 + (idx * col_w)
            pdf.rect(x, y0, col_w, row_h)
            y = y0 + pad_y
            for line_ in lines_:
                pdf.set_xy(x + pad_x, y)
                pdf.cell(
                    cell_inner_width,
                    line_h,
                    text=line_,
                )
                y += line_h
        pdf.set_xy(x0, y0 + row_h)

    pdf.set_font('main', size=11)
    draw_row(header)
    for row in normalized_rows:
        draw_row(row)
