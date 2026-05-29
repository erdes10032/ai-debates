import re

from django import forms
from django.core.exceptions import ValidationError
from django.forms import (
    BaseFormSet,
    formset_factory,
)
from django.http import QueryDict
from django.utils.translation import gettext_lazy as _

from agents.models import (
    DebateRole,
    LLMModel,
)
from debates.models import Debate


MIN_PARTICIPANTS = 2

MAX_PARTICIPANTS = 10

PARTICIPANT_FORMSET_PREFIX = 'participants'


MIN_ROUNDS = 1

MAX_ROUNDS = 10


class DebateCreateForm(forms.ModelForm):

    class Meta:

        model = Debate

        fields = [
            'topic',
            'rounds_count',
            'allow_concessions',
        ]

        widgets = {
            'topic': forms.TextInput(
                attrs={
                    'class': 'input',
                }
            ),

            'rounds_count': forms.NumberInput(
                attrs={
                    'class': 'input',
                    'min': MIN_ROUNDS,
                    'max': MAX_ROUNDS,
                }
            ),

            'allow_concessions': forms.CheckboxInput(),
        }

    def clean_topic(self):

        topic = self.cleaned_data['topic'].strip()

        if not topic:
            raise ValidationError(
                _('Enter a debate topic.'),
            )

        return topic

    def clean_rounds_count(self):

        rounds_count = self.cleaned_data['rounds_count']

        if (
            rounds_count < MIN_ROUNDS
            or rounds_count > MAX_ROUNDS
        ):
            raise ValidationError(
                _(
                    'Number of rounds must be between '
                    '%(min)s and %(max)s.'
                )
                % {
                    'min': MIN_ROUNDS,
                    'max': MAX_ROUNDS,
                },
            )

        return rounds_count


class DebateParticipantForm(forms.Form):

    llm_model = forms.ModelChoiceField(
        queryset=LLMModel.objects.none(),
        label=_('Model'),
        widget=forms.Select(
            attrs={
                'class': 'input',
            }
        ),
        empty_label=None,
    )

    debate_role = forms.ModelChoiceField(
        queryset=DebateRole.objects.none(),
        label=_('Role'),
        widget=forms.Select(
            attrs={
                'class': 'input',
            }
        ),
        empty_label=None,
    )

    def __init__(
        self,
        *args,
        **kwargs,
    ):

        super().__init__(
            *args,
            **kwargs,
        )

        self.fields['llm_model'].queryset = (
            LLMModel.objects.filter(
                is_active=True,
            )
        )

        self.fields['debate_role'].queryset = (
            DebateRole.objects.filter(
                is_active=True,
            )
        )


class BaseDebateParticipantFormSet(BaseFormSet):

    @classmethod
    def get_default_prefix(cls) -> str:
        return PARTICIPANT_FORMSET_PREFIX

    def clean(self) -> None:

        super().clean()

        if any(self.errors):
            return

        valid_forms = [
            form
            for form in self.forms
            if form.cleaned_data
        ]

        if len(valid_forms) < MIN_PARTICIPANTS:
            raise ValidationError(
                _(
                    'Select at least %(min)s participants.'
                )
                % {'min': MIN_PARTICIPANTS},
            )

        if len(valid_forms) > MAX_PARTICIPANTS:
            raise ValidationError(
                _(
                    'No more than %(max)s participants allowed.'
                )
                % {'max': MAX_PARTICIPANTS},
            )


DebateParticipantFormSet = formset_factory(
    DebateParticipantForm,
    formset=BaseDebateParticipantFormSet,
    min_num=MIN_PARTICIPANTS,
    validate_min=True,
    max_num=MAX_PARTICIPANTS,
    extra=0,
)


_PARTICIPANT_FIELD_PATTERN = re.compile(
    rf'^{re.escape(PARTICIPANT_FORMSET_PREFIX)}-(\d+)-'
)


def participant_indices_in_post(
    post_data,
) -> list[int]:

    indices = set()

    for key in post_data:

        match = _PARTICIPANT_FIELD_PATTERN.match(
            key,
        )

        if match:
            indices.add(
                int(match.group(1)),
            )

    return sorted(indices)


def normalize_participant_formset_post(
    post_data,
) -> QueryDict:

    normalized = post_data.copy()

    indices = participant_indices_in_post(
        normalized,
    )

    if not indices:
        return normalized

    if len(indices) > MAX_PARTICIPANTS:
        raise ValidationError(
            _(
                'No more than %(max)s participants allowed.'
            )
            % {'max': MAX_PARTICIPANTS},
        )

    normalized[
        f'{PARTICIPANT_FORMSET_PREFIX}-TOTAL_FORMS'
    ] = str(len(indices))

    return normalized


def build_participant_formset(
    post_data=None,
) -> DebateParticipantFormSet:

    if post_data is not None:
        post_data = normalize_participant_formset_post(
            post_data,
        )

    return DebateParticipantFormSet(
        post_data,
    )


def iter_participant_cleaned_data(
    formset: BaseDebateParticipantFormSet,
):

    for form in formset.forms:

        if form.cleaned_data:
            yield form.cleaned_data


def validate_participant_formset(
    formset,
) -> None:

    if not formset.is_valid():
        return

    if not LLMModel.objects.filter(
        is_active=True,
    ).exists():
        raise ValidationError(
            _(
                'No active models. Ask an administrator '
                'to add models in the admin panel.'
            ),
        )

    if not DebateRole.objects.filter(
        is_active=True,
    ).exists():
        raise ValidationError(
            _(
                'No active roles. Ask an administrator '
                'to add roles in the admin panel.'
            ),
        )
