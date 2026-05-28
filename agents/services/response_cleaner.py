class DebateResponseCleaner:

    FORBIDDEN_STARTS = (
        'okay',
        'sure',
        'the user',
        'i need to',
        'i should',
        'let me',
        'here is',
        'analysis:',
        'reasoning:',
        'thoughts:',
        'first, let me',
        'as an ai',
    )

    SHORT_FALLBACK = (
        'I disagree with several points from the previous '
        'speaker. The issue is more complicated than they '
        'describe.'
    )

    EMPTY_FALLBACK = (
        'I disagree with the previous arguments and want '
        'to continue the discussion.'
    )

    @classmethod
    def clean(cls, *, response: str) -> str:

        if not response:
            return cls.EMPTY_FALLBACK

        lines = response.splitlines()

        cleaned_lines = []

        for line in lines:

            stripped = line.strip()

            if not stripped:
                continue

            lower = stripped.lower()

            if (
                len(cleaned_lines) < 3
                and any(
                    lower.startswith(phrase)
                    for phrase in cls.FORBIDDEN_STARTS
                )
            ):
                continue

            cleaned_lines.append(stripped)

        cleaned = '\n'.join(cleaned_lines).strip()

        if not cleaned:
            cleaned = response.strip()

        if len(cleaned) < 20:
            return cls.SHORT_FALLBACK

        return cleaned
