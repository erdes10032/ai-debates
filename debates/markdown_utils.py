import re

import bleach
import markdown as markdown_lib
from django.utils.safestring import SafeString, mark_safe

from debates.markdown_tables import (
    ends_table_block,
    is_table_line,
    merge_wrapped_table_lines,
    normalize_all_table_separators,
    normalize_table_separator_row,
    split_inline_table_rows,
)


_ATX_HEADER_PATTERN = re.compile(
    r'^#{1,6}\s',
)

ALLOWED_MARKDOWN_TAGS = [
    'p',
    'br',
    'strong',
    'em',
    'code',
    'pre',
    'ul',
    'ol',
    'li',
    'blockquote',
    'hr',
    'h1',
    'h2',
    'h3',
    'h4',
    'h5',
    'h6',
    'table',
    'thead',
    'tbody',
    'tr',
    'th',
    'td',
    'a',
]

ALLOWED_MARKDOWN_ATTRIBUTES = {
    'a': ['href', 'title', 'rel'],
    'th': ['align'],
    'td': ['align'],
}

ALLOWED_MARKDOWN_PROTOCOLS = [
    'http',
    'https',
    'mailto',
]


def _ensure_blank_line_before_tables(text: str) -> str:

    lines = text.split('\n')
    result: list[str] = []

    for line in lines:

        if (
            is_table_line(line)
            and result
            and result[-1].strip()
            and not is_table_line(result[-1])
        ):
            result.append('')

        result.append(line)

    return '\n'.join(result)


def _ensure_blank_line_after_tables(text: str) -> str:

    lines = text.split('\n')
    result: list[str] = []

    for index, line in enumerate(lines):

        if (
            index > 0
            and is_table_line(lines[index - 1])
            and not is_table_line(line)
            and line.strip()
            and result
            and result[-1].strip()
        ):
            result.append('')

        result.append(line)

    return '\n'.join(result)


def _ensure_blank_line_before_headers(text: str) -> str:

    lines = text.split('\n')
    result = []

    for line in lines:

        if (
            _ATX_HEADER_PATTERN.match(line.strip())
            and result
            and result[-1].strip()
        ):
            result.append('')

        result.append(line)

    return '\n'.join(result)


def _normalize_horizontal_rules(text: str) -> str:

    lines = text.split('\n')
    result = []

    for line in lines:

        stripped = line.strip()

        if (
            stripped in {'---', '***', '___'}
            and result
            and result[-1].strip()
            and not is_table_line(result[-1])
        ):
            result.append('')
            result.append(stripped)
            result.append('')
            continue

        result.append(line)

    return '\n'.join(result)


def prepare_debate_markdown(text: str) -> str:

    if not text:
        return ''

    normalized = (
        text.replace('\r\n', '\n')
        .replace('\r', '\n')
        .strip()
    )

    normalized = normalize_all_table_separators(normalized)

    normalized = split_inline_table_rows(normalized)

    normalized = merge_wrapped_table_lines(normalized)

    normalized = _ensure_blank_line_before_tables(normalized)

    normalized = _ensure_blank_line_after_tables(normalized)

    normalized = _ensure_blank_line_before_headers(normalized)

    normalized = _normalize_horizontal_rules(normalized)

    return normalized


def sanitize_markdown_html(html: str) -> str:

    return bleach.clean(
        html,
        tags=ALLOWED_MARKDOWN_TAGS,
        attributes=ALLOWED_MARKDOWN_ATTRIBUTES,
        protocols=ALLOWED_MARKDOWN_PROTOCOLS,
        strip=True,
    )


def render_debate_markdown_html(text: str) -> SafeString:

    prepared = prepare_debate_markdown(text)

    html = markdown_lib.markdown(
        prepared,
        extensions=[
            'tables',
            'sane_lists',
            'fenced_code',
        ],
    )

    return mark_safe(
        sanitize_markdown_html(html),
    )
