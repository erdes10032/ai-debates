import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
)

from debates.forms import (
    MAX_PARTICIPANTS,
    MIN_PARTICIPANTS,
    DebateCreateForm,
    build_participant_formset,
    validate_participant_formset,
)
from debates.models import Debate
from debates.services import create_debate_participants
from debates.tasks import run_debate_task


logger = logging.getLogger(__name__)


class DebateListView(
    LoginRequiredMixin,
    ListView,
):

    model = Debate

    template_name = 'debates/debates_list.html'

    context_object_name = 'debates'

    def get_queryset(self):

        return Debate.objects.filter(
            user=self.request.user,
        )


class DebateCreateView(
    LoginRequiredMixin,
    CreateView,
):

    model = Debate

    form_class = DebateCreateForm

    template_name = 'debates/debate_create.html'

    success_url = reverse_lazy(
        'debates:list',
    )

    def get_participant_formset(self):

        if self.request.method == 'POST':
            return build_participant_formset(
                self.request.POST,
            )

        return build_participant_formset()

    def get_context_data(
        self,
        **kwargs,
    ):

        context = super().get_context_data(
            **kwargs,
        )

        context['participant_formset'] = (
            kwargs.get(
                'participant_formset',
                self.get_participant_formset(),
            )
        )

        context['min_participants'] = MIN_PARTICIPANTS

        context['max_participants'] = MAX_PARTICIPANTS

        return context

    def post(
        self,
        request,
        *args,
        **kwargs,
    ):

        self.object = None

        form = self.get_form()

        try:
            participant_formset = (
                build_participant_formset(
                    request.POST,
                )
            )
        except ValidationError as error:
            form.add_error(None, error)
            participant_formset = (
                build_participant_formset()
            )
        else:
            if (
                form.is_valid()
                and participant_formset.is_valid()
            ):
                try:
                    validate_participant_formset(
                        participant_formset,
                    )
                except ValidationError as error:
                    form.add_error(
                        None,
                        error,
                    )
                else:
                    return self.form_valid(
                        form,
                        participant_formset,
                    )

        return self.render_to_response(
            self.get_context_data(
                form=form,
                participant_formset=(
                    participant_formset
                ),
            )
        )

    def form_valid(
        self,
        form,
        participant_formset=None,
    ):

        form.instance.user = self.request.user

        self.object = form.save()

        participants = create_debate_participants(
            debate=self.object,
            participant_formset=participant_formset,
        )

        logger.info(
            'Debate %s created with %s participants',
            self.object.id,
            len(participants),
        )

        run_debate_task.delay(
            self.object.id,
        )

        return HttpResponseRedirect(
            self.get_success_url(),
        )


class DebateDetailView(
    LoginRequiredMixin,
    DetailView,
):

    model = Debate

    template_name = 'debates/debate_detail.html'

    context_object_name = 'debate'

    def get_queryset(self):

        return Debate.objects.filter(
            user=self.request.user,
        )

    def get_context_data(
        self,
        **kwargs,
    ):

        context = super().get_context_data(
            **kwargs,
        )

        participants_count = (
            self.object.participants.count()
        )

        context['participants_count'] = (
            participants_count
        )

        context['debate_messages'] = (
            self.object.messages.select_related(
                'round',
                'participant',
                'participant__debate_role',
                'participant__llm_model',
            ).order_by('created_at')
        )

        context['allow_concessions'] = (
            self.object.allow_concessions
        )

        return context
