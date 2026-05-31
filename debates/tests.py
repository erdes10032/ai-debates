from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from agents.models import (
    DebateRole,
    LLMModel,
)
from debates.forms import (
    MIN_PARTICIPANTS,
    PARTICIPANT_FORMSET_PREFIX,
    build_participant_formset,
    normalize_participant_formset_post,
    participant_indices_in_post,
)
from debates.models import Debate
from debates.pdf_export import (
    build_debate_pdf_filename,
    render_debate_history_pdf,
)
from debates.markdown_utils import (
    prepare_debate_markdown,
    render_debate_markdown_html,
)


class ParticipantFormsetTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.model_a = LLMModel.objects.create(
            name='Model A',
            model_id='provider/model-a',
            is_active=True,
        )

        cls.model_b = LLMModel.objects.create(
            name='Model B',
            model_id='provider/model-b',
            is_active=True,
        )

        cls.model_c = LLMModel.objects.create(
            name='Model C',
            model_id='provider/model-c',
            is_active=True,
        )

        cls.role_a = DebateRole.objects.create(
            name='Role A',
            behavior='Argue clearly.',
            is_active=True,
        )

        cls.role_b = DebateRole.objects.create(
            name='Role B',
            behavior='Challenge claims.',
            is_active=True,
        )

        cls.role_c = DebateRole.objects.create(
            name='Role C',
            behavior='Summarize points.',
            is_active=True,
        )

    def _participant_post(
        self,
        entries,
        *,
        total_forms=None,
    ):

        post = {
            'topic': 'Test topic',
            'rounds_count': '2',
            f'{PARTICIPANT_FORMSET_PREFIX}-INITIAL_FORMS': '0',
            f'{PARTICIPANT_FORMSET_PREFIX}-MIN_NUM_FORMS': str(
                MIN_PARTICIPANTS,
            ),
            f'{PARTICIPANT_FORMSET_PREFIX}-MAX_NUM_FORMS': '10',
        }

        for index, entry in enumerate(entries):
            post[
                f'{PARTICIPANT_FORMSET_PREFIX}-{index}-llm_model'
            ] = str(entry['llm_model'])

            post[
                f'{PARTICIPANT_FORMSET_PREFIX}-{index}-debate_role'
            ] = str(entry['debate_role'])

        post[
            f'{PARTICIPANT_FORMSET_PREFIX}-TOTAL_FORMS'
        ] = str(
            total_forms
            if total_forms is not None
            else len(entries),
        )

        return post

    def test_formset_uses_participants_prefix(self):

        formset = build_participant_formset()

        self.assertEqual(
            formset.prefix,
            PARTICIPANT_FORMSET_PREFIX,
        )

    def test_normalize_post_fixes_stale_total_forms(self):

        post = self._participant_post(
            [
                {
                    'llm_model': self.model_a.pk,
                    'debate_role': self.role_a.pk,
                },
                {
                    'llm_model': self.model_b.pk,
                    'debate_role': self.role_b.pk,
                },
                {
                    'llm_model': self.model_c.pk,
                    'debate_role': self.role_c.pk,
                },
            ],
            total_forms=MIN_PARTICIPANTS,
        )

        normalized = normalize_participant_formset_post(
            post,
        )

        self.assertEqual(
            normalized[
                f'{PARTICIPANT_FORMSET_PREFIX}-TOTAL_FORMS'
            ],
            '3',
        )


class MarkdownRenderTests(TestCase):

    def test_bold_is_rendered(self):

        html = render_debate_markdown_html(
            '**Итоговый консенсус**',
        )

        self.assertIn(
            '<strong>Итоговый консенсус</strong>',
            html,
        )
        self.assertNotIn(
            '**',
            html,
        )

    def test_table_is_rendered(self):

        source = (
            '| a | b |\n'
            '|---|---|\n'
            '| 1 | 2 |'
        )

        html = render_debate_markdown_html(source)

        self.assertIn('<table>', html)
        self.assertIn('<th>a</th>', html)

    def test_heading_is_rendered(self):

        html = render_debate_markdown_html(
            '### Section title',
        )

        self.assertIn(
            '<h3>Section title</h3>',
            html,
        )

    def test_table_survives_blank_line_before_separator(self):

        source = (
            '| a | b |\n'
            '\n'
            '|---|---|\n'
            '| 1 | 2 |'
        )

        html = render_debate_markdown_html(source)

        self.assertIn('<table>', html)
        self.assertIn('<td>1</td>', html)
        self.assertNotIn(
            '<p>|---',
            html,
        )

    def test_header_after_table_row(self):

        source = (
            '| 1 | x |\n'
            '### Section two'
        )

        html = render_debate_markdown_html(source)

        self.assertIn('<h3>Section two</h3>', html)
        self.assertNotIn('###', html)

    def test_inline_table_rows_are_split(self):

        source = (
            '| a | b | |---|---| | 1 | 2 |'
        )

        prepared = prepare_debate_markdown(source)

        self.assertIn('|---|', prepared)
        self.assertIn('\n', prepared)
        html = render_debate_markdown_html(source)

        self.assertIn('<table>', html)
        self.assertIn('<td>1</td>', html)


class DebateHistoryPdfTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='test_user',
            password='password123',
        )
        self.client.force_login(self.user)

    def test_pdf_download_is_available_for_completed_debate(self):
        debate = Debate.objects.create(
            user=self.user,
            topic='Нужно ли внедрять ИИ в образование',
            status=Debate.Status.COMPLETED,
        )

        response = self.client.get(
            reverse(
                'debates:history-pdf',
                kwargs={'pk': debate.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/pdf',
        )
        self.assertIn(
            'attachment; filename*=UTF-8',
            response['Content-Disposition'],
        )
        self.assertTrue(response.content)

    def test_pdf_download_is_hidden_for_non_completed_debate(self):
        debate = Debate.objects.create(
            user=self.user,
            topic='Topic',
            status=Debate.Status.IN_PROGRESS,
        )

        response = self.client.get(
            reverse(
                'debates:history-pdf',
                kwargs={'pk': debate.pk},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_pdf_filename_uses_topic_sequence(self):
        Debate.objects.create(
            user=self.user,
            topic='Climate change',
            status=Debate.Status.COMPLETED,
        )
        second_debate = Debate.objects.create(
            user=self.user,
            topic='Climate change',
            status=Debate.Status.COMPLETED,
        )

        filename = build_debate_pdf_filename(
            debate=second_debate,
        )

        self.assertIn(
            'Climate_change',
            filename,
        )
        self.assertIn(
            '_2.pdf',
            filename,
        )

    def test_pdf_with_consensus_table(self):
        debate = Debate.objects.create(
            user=self.user,
            topic='Тема дебатов',
            status=Debate.Status.COMPLETED,
            consensus=(
                '| a | b |\n'
                '|---|---|\n'
                '| 1 | 2 |'
            ),
        )

        pdf_bytes = render_debate_history_pdf(
            debate=debate,
        )

        self.assertTrue(pdf_bytes.startswith(b'%PDF'))

    def test_consensus_html_endpoint(self):
        debate = Debate.objects.create(
            user=self.user,
            topic='Topic',
            status=Debate.Status.COMPLETED,
            consensus='**Итог**',
        )

        response = self.client.get(
            reverse(
                'debates:consensus-html',
                kwargs={'pk': debate.pk},
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b'<strong>',
            response.content,
        )
