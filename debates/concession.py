"""
Detection and early-stop rules for debate concessions.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from debates.models import DebateParticipant


CONCESSION_MIN_ROUND = 2

# Substring match on normalized text (lowercase).
CONCESSION_PHRASES: tuple[str, ...] = (
    'i concede',
    'i admit defeat',
    'i was wrong',
    'the opposing side is correct',
    'my position is indefensible',
    'my position is wrong',
    'i lose this debate',
    'i surrender this argument',
    'признаю поражение',
    'признаю свою неправоту',
    'признаю, что не прав',
    'признаю, что неправ',
    'признаю свое поражение',
    'признаю своё поражение',
    'моя позиция неверна',
    'моя позиция не выдерживает',
    'моя позиция неправильна',
    'соперники правы',
    'противная сторона права',
    'уступаю',
    'сдаюсь',
)

_STRONG_CONCESSION_RE = re.compile(
    r'(?:'
    r'\b(?:i|я)\s+(?:concede|surrender|admit\s+defeat|was\s+wrong|lose)\b'
    r'|'
    r'признаю\s+(?:поражение|свою\s+неправоту|что\s+не\s*прав)'
    r'|'
    r'моя\s+позиция\s+(?:неверна|неправильна|не\s+выдерживает)'
    r')',
    re.IGNORECASE | re.MULTILINE,
)


def normalize_for_detection(text: str) -> str:

    return ' '.join(text.lower().split())


def _phrase_matches(
    phrase: str,
    normalized: str,
) -> bool:

    words = phrase.split()

    if not words:
        return False

    if len(words) == 1:
        return re.search(
            rf'\b{re.escape(words[0])}\b',
            normalized,
            re.IGNORECASE,
        ) is not None

    # Allow a few words between phrase tokens: "i fully concede".
    parts = []

    for index, word in enumerate(words):

        parts.append(re.escape(word))

        if index < len(words) - 1:
            parts.append(r'(?:\s+\w+){0,4}\s+')

    pattern = r'\b' + ''.join(parts) + r'\b'

    return re.search(
        pattern,
        normalized,
        re.IGNORECASE,
    ) is not None


def detect_concession(text: str) -> bool:

    if not text or len(text.strip()) < 12:
        return False

    normalized = normalize_for_detection(text)

    if _STRONG_CONCESSION_RE.search(normalized):
        return True

    return any(
        _phrase_matches(phrase, normalized)
        for phrase in CONCESSION_PHRASES
    )


def active_participants(
    participants: list[DebateParticipant],
) -> list[DebateParticipant]:

    return [
        participant
        for participant in participants
        if not participant.has_conceded
    ]


def side_fully_conceded(
    participants: list[DebateParticipant],
    *,
    position: str,
) -> bool:

    side = [
        participant
        for participant in participants
        if participant.position == position
    ]

    if not side:
        return False

    return all(
        participant.has_conceded
        for participant in side
    )


def should_end_debate_early(
    participants: list[DebateParticipant],
) -> bool:

    if len(participants) < 2:
        return False

    if len(participants) == 2:
        return any(
            participant.has_conceded
            for participant in participants
        )

    return (
        side_fully_conceded(
            participants,
            position='support',
        )
        or side_fully_conceded(
            participants,
            position='oppose',
        )
    )
