from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from agents.models import (
    DebateRole,
    LLMModel,
)
from debates.forms import PARTICIPANT_FORMSET_PREFIX
from debates.models import (
    Debate,
    DebateParticipant,
)


class DebateCreateViewTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.user = get_user_model().objects.create_user(
            username='creator',
            email='creator@example.com',
            password='password123',
        )

        cls.model = LLMModel.objects.create(
            name='Model A',
            model_id='provider/model-a',
            is_active=True,
        )

        cls.role = DebateRole.objects.create(
            name='Debater',
            behavior='Argue clearly.',
            is_active=True,
        )

    def setUp(self):

        self.client.force_login(self.user)

    @patch('debates.views.run_debate_task.delay')
    def test_create_debate_persists_participants(
        self,
        run_debate_delay,
    ):

        post = {
            'topic': 'Test topic',
            'rounds_count': '2',
            'allow_concessions': 'on',
            f'{PARTICIPANT_FORMSET_PREFIX}-TOTAL_FORMS': '2',
            f'{PARTICIPANT_FORMSET_PREFIX}-INITIAL_FORMS': '0',
            f'{PARTICIPANT_FORMSET_PREFIX}-MIN_NUM_FORMS': '2',
            f'{PARTICIPANT_FORMSET_PREFIX}-MAX_NUM_FORMS': '10',
            f'{PARTICIPANT_FORMSET_PREFIX}-0-llm_model': str(
                self.model.pk,
            ),
            f'{PARTICIPANT_FORMSET_PREFIX}-0-debate_role': str(
                self.role.pk,
            ),
            f'{PARTICIPANT_FORMSET_PREFIX}-1-llm_model': str(
                self.model.pk,
            ),
            f'{PARTICIPANT_FORMSET_PREFIX}-1-debate_role': str(
                self.role.pk,
            ),
        }

        response = self.client.post(
            reverse('debates:create'),
            post,
        )

        self.assertEqual(response.status_code, 302)

        debate = Debate.objects.get(topic='Test topic')

        self.assertEqual(
            DebateParticipant.objects.filter(debate=debate).count(),
            2,
        )
        run_debate_delay.assert_called_once_with(debate.id)
