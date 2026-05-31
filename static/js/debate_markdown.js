/**
 * Markdown rendering for live debate updates (WebSocket).
 */
(function (global) {
    'use strict';

    const ATX_HEADER_PATTERN = /^#{1,6}\s/;
    const LIST_ITEM_PATTERN = /^(?:[-*+]|\d+\.)\s+/;

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.innerText = text;
        return div.innerHTML;
    }

    function fallbackFormat(text) {
        return escapeHtml(text || '').replace(
            /\n/g,
            '<br>',
        );
    }

    function splitTableCells(line) {
        return line
            .trim()
            .replace(/^\|/, '')
            .replace(/\|$/, '')
            .split('|')
            .map((cell) => cell.trim());
    }

    function isTableSeparatorRow(line) {
        const stripped = line.trim();

        if (!stripped.startsWith('|')) {
            return false;
        }

        const cells = splitTableCells(stripped);

        if (!cells.length) {
            return false;
        }

        return cells.every(
            (cell) => /^:?-{3,}:?$/.test(cell),
        );
    }

    function isTableDataRow(line) {
        const stripped = line.trim();

        if (!stripped.startsWith('|')) {
            return false;
        }

        if (isTableSeparatorRow(line)) {
            return false;
        }

        return (stripped.match(/\|/g) || []).length >= 2;
    }

    function isTableLine(line) {
        return (
            isTableSeparatorRow(line)
            || isTableDataRow(line)
        );
    }

    function normalizeTableSeparatorRow(line) {
        if (!isTableSeparatorRow(line)) {
            return line;
        }

        const cellCount = splitTableCells(line).length;

        return `|${'|---|'.repeat(cellCount)}`;
    }

    function endsTableBlock(line) {
        const stripped = line.trim();

        if (!stripped) {
            return false;
        }

        if (isTableLine(line)) {
            return false;
        }

        if (ATX_HEADER_PATTERN.test(stripped)) {
            return true;
        }

        if (LIST_ITEM_PATTERN.test(stripped)) {
            return true;
        }

        if (
            stripped === '---'
            || stripped === '***'
            || stripped === '___'
        ) {
            return true;
        }

        return false;
    }

    function normalizeAllTableSeparators(text) {
        return text
            .split('\n')
            .map((line) => normalizeTableSeparatorRow(line))
            .join('\n');
    }

    function splitInlineTableRows(text) {
        return text
            .split('\n')
            .map((line) => {
                if ((line.match(/\|/g) || []).length < 4) {
                    return line;
                }

                return line.replace(/\|\s*\|/g, '|\n|');
            })
            .join('\n');
    }

    function mergeWrappedTableLines(text) {
        const lines = text.split('\n');
        const result = [];
        let inTable = false;
        let index = 0;

        while (index < lines.length) {
            const line = lines[index];

            if (isTableLine(line)) {
                inTable = true;
                result.push(normalizeTableSeparatorRow(line));
                index += 1;
                continue;
            }

            if (!inTable) {
                result.push(line);
                index += 1;
                continue;
            }

            if (!line.trim()) {
                while (
                    index < lines.length
                    && !lines[index].trim()
                ) {
                    index += 1;
                }

                if (index >= lines.length) {
                    inTable = false;
                    continue;
                }

                const nextLine = lines[index];

                if (isTableLine(nextLine)) {
                    continue;
                }

                if (endsTableBlock(nextLine)) {
                    inTable = false;
                    result.push('');
                    result.push(nextLine);
                    index += 1;
                    continue;
                }

                if (result.length) {
                    result[result.length - 1] = (
                        `${result[result.length - 1].trimEnd()} `
                        + `${nextLine.trim()}`
                    );
                }

                index += 1;
                continue;
            }

            if (endsTableBlock(line)) {
                inTable = false;
                result.push('');
                result.push(line);
                index += 1;
                continue;
            }

            if (result.length) {
                result[result.length - 1] = (
                    `${result[result.length - 1].trimEnd()} ${line.trim()}`
                );
            }

            index += 1;
        }

        return result.join('\n');
    }

    function ensureBlankLineBeforeTables(text) {
        const lines = text.split('\n');
        const result = [];

        lines.forEach((line) => {
            if (
                isTableLine(line)
                && result.length
                && result[result.length - 1].trim()
                && !isTableLine(result[result.length - 1])
            ) {
                result.push('');
            }

            result.push(line);
        });

        return result.join('\n');
    }

    function ensureBlankLineAfterTables(text) {
        const lines = text.split('\n');
        const result = [];
        let previousWasTable = false;

        lines.forEach((line, index) => {
            if (
                index > 0
                && isTableLine(lines[index - 1])
                && !isTableLine(line)
                && line.trim()
                && result.length
                && result[result.length - 1].trim()
            ) {
                result.push('');
            }

            result.push(line);
        });

        return result.join('\n');
    }

    function ensureBlankLineBeforeHeaders(text) {
        const lines = text.split('\n');
        const result = [];

        lines.forEach((line) => {
            if (
                ATX_HEADER_PATTERN.test(line.trim())
                && result.length
                && result[result.length - 1].trim()
            ) {
                result.push('');
            }

            result.push(line);
        });

        return result.join('\n');
    }

    function normalizeHorizontalRules(text) {
        const lines = text.split('\n');
        const result = [];

        lines.forEach((line) => {
            const stripped = line.trim();

            if (
                (stripped === '---'
                    || stripped === '***'
                    || stripped === '___')
                && result.length
                && result[result.length - 1].trim()
                && !isTableLine(result[result.length - 1])
            ) {
                result.push('');
                result.push(stripped);
                result.push('');
                return;
            }

            result.push(line);
        });

        return result.join('\n');
    }

    function prepareDebateMarkdown(text) {
        if (!text) {
            return '';
        }

        let normalized = text
            .replace(/\r\n/g, '\n')
            .replace(/\r/g, '\n')
            .trim();

        normalized = normalizeAllTableSeparators(normalized);
        normalized = splitInlineTableRows(normalized);
        normalized = mergeWrappedTableLines(normalized);
        normalized = ensureBlankLineBeforeTables(normalized);
        normalized = ensureBlankLineAfterTables(normalized);
        normalized = ensureBlankLineBeforeHeaders(normalized);
        normalized = normalizeHorizontalRules(normalized);

        return normalized;
    }

    const MARKDOWN_PURIFY_CONFIG = {
        USE_PROFILES: { html: true },
        ADD_TAGS: [
            'table',
            'thead',
            'tbody',
            'tr',
            'th',
            'td',
        ],
        ADD_ATTR: ['align'],
    };

    let markedConfigured = false;

    function ensureMarkedConfigured() {
        if (markedConfigured) {
            return true;
        }

        if (
            typeof global.marked === 'undefined'
            || typeof global.marked.parse !== 'function'
        ) {
            return false;
        }

        if (typeof global.marked.use === 'function') {
            global.marked.use({
                gfm: true,
                breaks: false,
            });
        }

        markedConfigured = true;
        return true;
    }

    function sanitizeRenderedHtml(html, plainFallback) {
        if (
            typeof global.DOMPurify !== 'undefined'
            && typeof global.DOMPurify.sanitize === 'function'
        ) {
            return global.DOMPurify.sanitize(
                html,
                MARKDOWN_PURIFY_CONFIG,
            );
        }

        return fallbackFormat(plainFallback);
    }

    function renderDebateMarkdown(text) {
        if (!text) {
            return '';
        }

        const prepared = prepareDebateMarkdown(text);

        if (ensureMarkedConfigured()) {
            const rawHtml = global.marked.parse(prepared);

            return sanitizeRenderedHtml(rawHtml, prepared);
        }

        return fallbackFormat(prepared);
    }

    global.prepareDebateMarkdown = prepareDebateMarkdown;
    global.renderDebateMarkdown = renderDebateMarkdown;
})(window);
