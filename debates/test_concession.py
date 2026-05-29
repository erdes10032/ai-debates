from django.test import SimpleTestCase

from debates.concession import (
    detect_concession,
    should_end_debate_early,
    side_fully_conceded,
)


class DetectConcessionTests(SimpleTestCase):

    def test_detects_english_concession(self):

        self.assertTrue(
            detect_concession(
                'After careful thought, I concede this debate.',
            ),
        )

    def test_detects_russian_concession(self):

        self.assertTrue(
            detect_concession(
                'Аргументы сильнее — признаю поражение.',
            ),
        )

    def test_ignores_short_text(self):

        self.assertFalse(
            detect_concession('I concede'),
        )

    def test_ignores_regular_argument(self):

        self.assertFalse(
            detect_concession(
                'Your point about funding is weak, but I still '
                'disagree with the overall conclusion.',
            ),
        )


class ShouldEndDebateEarlyTests(SimpleTestCase):

    def _participant(
        self,
        *,
        position: str,
        has_conceded: bool,
    ):
        return type(
            'Participant',
            (),
            {
                'position': position,
                'has_conceded': has_conceded,
            },
        )()

    def test_two_participants_end_when_one_concedes(self):

        participants = [
            self._participant(
                position='support',
                has_conceded=True,
            ),
            self._participant(
                position='oppose',
                has_conceded=False,
            ),
        ]

        self.assertTrue(
            should_end_debate_early(participants),
        )

    def test_three_participants_need_full_side_concession(self):

        participants = [
            self._participant(
                position='support',
                has_conceded=True,
            ),
            self._participant(
                position='support',
                has_conceded=False,
            ),
            self._participant(
                position='oppose',
                has_conceded=False,
            ),
        ]

        self.assertFalse(
            should_end_debate_early(participants),
        )

    def test_side_fully_conceded(self):

        participants = [
            self._participant(
                position='support',
                has_conceded=True,
            ),
            self._participant(
                position='support',
                has_conceded=True,
            ),
            self._participant(
                position='oppose',
                has_conceded=False,
            ),
        ]

        self.assertTrue(
            side_fully_conceded(
                participants,
                position='support',
            ),
        )
        self.assertTrue(
            should_end_debate_early(participants),
        )
