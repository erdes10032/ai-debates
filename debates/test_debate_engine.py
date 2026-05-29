from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import translation

from agents.models import (
    DebateRole,
    LLMModel,
)
from agents.services.debate_engine import DebateEngine
from debates.models import (
    Debate,
    DebateMessage,
    DebateParticipant,
)


class FakeLLMClient:

    def __init__(self, responses: list[str] | None = None):

        self.responses = list(responses or [])
        self.calls = 0

    def generate_response(
        self,
        *,
        model: str,
        system_prompt: str,
        messages: list[dict],
    ) -> str:

        self.calls += 1

        if self.responses:
            return self.responses.pop(0)

        return (
            'This is a substantive response that challenges the '
            'previous speaker with concrete reasoning.'
        )


@override_settings(
    DEBATE_ROUND_DELAY_SECONDS=0,
    CHANNEL_LAYERS={
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    },
)
class DebateEngineTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.user = get_user_model().objects.create_user(
            username='engine_user',
            email='engine@example.com',
            password='password123',
        )

        cls.model = LLMModel.objects.create(
            name='Test Model',
            model_id='provider/test-model',
            is_active=True,
        )

        cls.role_support = DebateRole.objects.create(
            name='Debater',
            behavior='Argue clearly.',
            is_active=True,
        )

        cls.role_oppose = DebateRole.objects.create(
            name='Critic',
            behavior='Challenge claims.',
            is_active=True,
        )

    def _create_debate(self, *, rounds_count: int = 1) -> Debate:

        debate = Debate.objects.create(
            user=self.user,
            topic='Should AI be used in education?',
            rounds_count=rounds_count,
            allow_concessions=True,
        )

        DebateParticipant.objects.create(
            debate=debate,
            llm_model=self.model,
            debate_role=self.role_support,
            order=0,
        )

        DebateParticipant.objects.create(
            debate=debate,
            llm_model=self.model,
            debate_role=self.role_oppose,
            order=1,
        )

        return debate

    def test_completes_debate_with_mock_client(self):

        debate = self._create_debate()

        client = FakeLLMClient(
            responses=[
                'First speaker gives a long substantive argument.',
                'Second speaker gives another long substantive argument.',
                'Final consensus summary for the debate.',
            ],
        )

        DebateEngine(
            client=client,
            round_delay_seconds=0,
        ).run_debate(debate=debate)

        debate.refresh_from_db()

        self.assertEqual(
            debate.status,
            Debate.Status.COMPLETED,
        )
        self.assertEqual(
            DebateMessage.objects.filter(debate=debate).count(),
            2,
        )
        self.assertTrue(debate.consensus)

    def test_stores_localized_role_name_snapshot(self):

        debate = self._create_debate()

        with translation.override('ru'):
            expected_role_name = self.role_support.localized_name

            DebateEngine(
                client=FakeLLMClient(
                    responses=[
                        'First speaker gives a long substantive argument.',
                        'Second speaker gives another long substantive argument.',
                        'Final consensus summary for the debate.',
                    ],
                ),
                round_delay_seconds=0,
            ).run_debate(debate=debate)

        message = DebateMessage.objects.filter(
            debate=debate,
            participant__debate_role=self.role_support,
        ).first()

        self.assertIsNotNone(message)
        self.assertEqual(
            message.role_name,
            expected_role_name,
        )

    def test_skips_duplicate_messages_on_retry(self):

        debate = self._create_debate()

        engine = DebateEngine(
            client=FakeLLMClient(),
            round_delay_seconds=0,
        )

        with patch.object(
            engine,
            '_message_exists',
            side_effect=[False, True],
        ):
            engine.run_debate(debate=debate)

        self.assertEqual(
            DebateMessage.objects.filter(debate=debate).count(),
            1,
        )

    def test_marks_failed_on_engine_error(self):

        debate = self._create_debate()

        client = MagicMock()
        client.generate_response.side_effect = RuntimeError('API down')

        with self.assertRaises(RuntimeError):
            DebateEngine(
                client=client,
                round_delay_seconds=0,
            ).run_debate(debate=debate)

        debate.refresh_from_db()

        self.assertEqual(
            debate.status,
            Debate.Status.FAILED,
        )
