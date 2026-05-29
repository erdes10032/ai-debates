"""
Shared Markdown table detection and normalization for HTML and PDF renderers.
"""

from __future__ import annotations

import re


_ATX_HEADER_PATTERN = re.compile(
    r'^#{1,6}\s',
)

_LIST_ITEM_PATTERN = re.compile(
    r'^(?:[-*+]|\d+\.)\s+',
)


def split_table_cells(line: str) -> list[str]:

    return [
        cell.strip()
        for cell in line.strip().strip('|').split('|')
    ]


def is_table_separator_row(line: str) -> bool:

    stripped = line.strip()

    if not stripped.startswith('|'):
        return False

    cells = split_table_cells(line)

    if not cells:
        return False

    return all(
        re.fullmatch(r':?-{3,}:?', cell) is not None
        for cell in cells
    )


def is_table_data_row(line: str) -> bool:

    stripped = line.strip()

    if not stripped.startswith('|'):
        return False

    if is_table_separator_row(line):
        return False

    return stripped.count('|') >= 2


def is_table_line(line: str) -> bool:

    return (
        is_table_separator_row(line)
        or is_table_data_row(line)
    )


def normalize_table_separator_row(line: str) -> str:

    if not is_table_separator_row(line):
        return line

    cell_count = len(split_table_cells(line))

    return '|' + '|'.join(['---'] * cell_count) + '|'


def ends_table_block(line: str) -> bool:

    stripped = line.strip()

    if not stripped:
        return False

    if is_table_line(line):
        return False

    if _ATX_HEADER_PATTERN.match(stripped):
        return True

    if _LIST_ITEM_PATTERN.match(stripped):
        return True

    if stripped in {'---', '***', '___'}:
        return True

    return False


def normalize_all_table_separators(text: str) -> str:

    lines = text.split('\n')

    return '\n'.join(
        normalize_table_separator_row(line)
        for line in lines
    )


def merge_wrapped_table_lines(text: str) -> str:

    lines = text.split('\n')
    result: list[str] = []
    in_table = False
    index = 0

    while index < len(lines):

        line = lines[index]

        if is_table_line(line):

            in_table = True

            result.append(
                normalize_table_separator_row(line),
            )

            index += 1

            continue

        if not in_table:

            result.append(line)

            index += 1

            continue

        if not line.strip():

            while (
                index < len(lines)
                and not lines[index].strip()
            ):
                index += 1

            if index >= len(lines):

                in_table = False

                continue

            next_line = lines[index]

            if is_table_line(next_line):

                continue

            if ends_table_block(next_line):

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

        if ends_table_block(line):

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


def is_markdown_table_start(lines: list[str], index: int) -> bool:

    if index + 1 >= len(lines):
        return False

    first = lines[index].strip()
    second = lines[index + 1].strip()

    if not (first.startswith('|') and second.startswith('|')):
        return False

    return is_table_separator_row(second)


def collect_markdown_table(
    lines: list[str],
    start: int,
) -> tuple[list[str], int]:

    collected = [lines[start], lines[start + 1]]
    idx = start + 2

    while idx < len(lines) and is_table_data_row(lines[idx]):
        collected.append(lines[idx])
        idx += 1

    return collected, idx


def parse_md_table_row(line: str) -> list[str]:

    raw = re.split(r'(?<!\\)\|', line.strip().strip('|'))

    return [cell.strip().replace(r'\|', '|') for cell in raw]
