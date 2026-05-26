import re

import bleach
import markdown as markdown_lib
from django.utils.safestring import SafeString, mark_safe


_ATX_HEADER_PATTERN = re.compile(
    r'^#{1,6}\s',
)

_LIST_ITEM_PATTERN = re.compile(
    r'^(?:[-*+]|\d+\.)\s+',
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


def _split_table_cells(line: str) -> list[str]:

    return [
        cell.strip()
        for cell in line.strip().strip('|').split('|')
    ]


def _is_table_separator_row(line: str) -> bool:

    stripped = line.strip()

    if not stripped.startswith('|'):
        return False

    cells = _split_table_cells(line)

    if not cells:
        return False

    return all(
        re.fullmatch(r':?-{3,}:?', cell) is not None
        for cell in cells
    )


def _is_table_data_row(line: str) -> bool:

    stripped = line.strip()

    if not stripped.startswith('|'):
        return False

    if _is_table_separator_row(line):
        return False

    return stripped.count('|') >= 2


def _is_table_line(line: str) -> bool:

    return (
        _is_table_separator_row(line)
        or _is_table_data_row(line)
    )


def _normalize_table_separator_row(line: str) -> str:

    if not _is_table_separator_row(line):
        return line

    cell_count = len(_split_table_cells(line))

    return '|' + '|'.join(['---'] * cell_count) + '|'


def _ends_table_block(line: str) -> bool:

    stripped = line.strip()

    if not stripped:
        return False

    if _is_table_line(line):
        return False

    if _ATX_HEADER_PATTERN.match(stripped):
        return True

    if _LIST_ITEM_PATTERN.match(stripped):
        return True

    if stripped in {'---', '***', '___'}:
        return True

    return False


def _normalize_all_table_separators(text: str) -> str:

    lines = text.split('\n')

    return '\n'.join(
        _normalize_table_separator_row(line)
        for line in lines
    )


def _merge_wrapped_table_lines(text: str) -> str:

    lines = text.split('\n')
    result: list[str] = []
    in_table = False
    index = 0

    while index < len(lines):

        line = lines[index]

        if _is_table_line(line):

            in_table = True

            result.append(
                _normalize_table_separator_row(line),
            )

            index += 1

            continue

        if not in_table:

            result.append(line)

            index += 1

            continue

        if not line.strip():

            blank_start = index

            while (
                index < len(lines)
                and not lines[index].strip()
            ):
                index += 1

            if index >= len(lines):

                in_table = False

                continue

            next_line = lines[index]

            if _is_table_line(next_line):

                continue

            if _ends_table_block(next_line):

                in_table = False

                result.append('')

                result.append(next_line)

                index += 1

                continue

            if result:

                result[-1] = (
                    result[-1].rstrip()
                    + ' '
                    + next_line.strip()
                )

            index += 1

            continue

        if _ends_table_block(line):

            in_table = False

            result.append('')

            result.append(line)

            index += 1

            continue

        if result:

            result[-1] = (
                result[-1].rstrip()
                + ' '
                + line.strip()
            )

        index += 1

    return '\n'.join(result)


def _ensure_blank_line_before_tables(text: str) -> str:

    lines = text.split('\n')
    result: list[str] = []

    for line in lines:

        if (
            _is_table_line(line)
            and result
            and result[-1].strip()
            and not _is_table_line(result[-1])
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
            and _is_table_line(lines[index - 1])
            and not _is_table_line(line)
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
            and not _is_table_line(result[-1])
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

    normalized = _normalize_all_table_separators(normalized)

    normalized = _merge_wrapped_table_lines(normalized)

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
