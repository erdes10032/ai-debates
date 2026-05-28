from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Debate(models.Model):

    class Status(models.TextChoices):

        PENDING = 'pending', _('Pending')

        IN_PROGRESS = 'in_progress', _('In progress')

        COMPLETED = 'completed', _('Completed')

        FAILED = 'failed', _('Failed')

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='debates',
        verbose_name=_('User'),
    )

    topic = models.CharField(
        max_length=500,
        verbose_name=_('Topic'),
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_('Status'),
    )

    rounds_count = models.PositiveIntegerField(
        default=3,
        verbose_name=_('Rounds count'),
    )

    allow_concessions = models.BooleanField(
        default=True,
        verbose_name=_('Allow concessions'),
        help_text=_(
            'Participants may concede when their position '
            'is no longer defensible'
        ),
    )

    consensus = models.TextField(
        blank=True,
        verbose_name=_('Consensus'),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at'),
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated at'),
    )

    class Meta:

        ordering = ['-created_at']
        verbose_name = _('Debate')
        verbose_name_plural = _('Debates')

    def __str__(self):

        return self.topic


class DebateParticipant(models.Model):

    class Position(models.TextChoices):

        SUPPORT = 'support', _('Support')

        OPPOSE = 'oppose', _('Oppose')

    debate = models.ForeignKey(
        Debate,
        on_delete=models.CASCADE,
        related_name='participants',
        verbose_name=_('Debate'),
    )

    llm_model = models.ForeignKey(
        'agents.LLMModel',
        on_delete=models.PROTECT,
        related_name='debate_participants',
        verbose_name=_('LLM model'),
    )

    debate_role = models.ForeignKey(
        'agents.DebateRole',
        on_delete=models.PROTECT,
        related_name='debate_participants',
        verbose_name=_('Debate role'),
    )

    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Order'),
    )

    position = models.CharField(
        max_length=10,
        choices=Position.choices,
        blank=True,
        verbose_name=_('Position'),
    )

    has_conceded = models.BooleanField(
        default=False,
        verbose_name=_('Has conceded'),
    )

    conceded_at_round = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_('Conceded at round'),
    )

    class Meta:

        ordering = ['order', 'id']
        verbose_name = _('Debate participant')
        verbose_name_plural = _('Debate participants')

    def __str__(self):

        return self.speaker_label

    @property
    def speaker_label(self) -> str:

        return (
            f'{self.debate_role.localized_name} '
            f'({self.llm_model.name}) '
            f'#{self.order + 1}'
        )


class DebateRound(models.Model):

    debate = models.ForeignKey(
        Debate,
        on_delete=models.CASCADE,
        related_name='rounds',
        verbose_name=_('Debate'),
    )

    number = models.PositiveIntegerField(
        verbose_name=_('Number'),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at'),
    )

    class Meta:

        unique_together = (
            'debate',
            'number',
        )

        ordering = ['number']
        verbose_name = _('Debate round')
        verbose_name_plural = _('Debate rounds')

    def __str__(self):

        return _('%(debate_id)s — round %(number)s') % {
            'debate_id': self.debate_id,
            'number': self.number,
        }


class DebateMessage(models.Model):

    debate = models.ForeignKey(
        Debate,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name=_('Debate'),
    )

    round = models.ForeignKey(
        DebateRound,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name=_('Round'),
    )

    participant = models.ForeignKey(
        DebateParticipant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='messages',
        verbose_name=_('Participant'),
    )

    speaker_label = models.CharField(
        max_length=255,
        verbose_name=_('Speaker label'),
    )

    role_name = models.CharField(
        max_length=100,
        verbose_name=_('Role name'),
    )

    model_name = models.CharField(
        max_length=255,
        verbose_name=_('Model name'),
    )

    content = models.TextField(
        verbose_name=_('Content'),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at'),
    )

    class Meta:

        ordering = ['created_at']
        verbose_name = _('Debate message')
        verbose_name_plural = _('Debate messages')
        constraints = [
            models.UniqueConstraint(
                fields=['round', 'participant'],
                name='unique_debate_message_per_participant_round',
            ),
        ]

    def __str__(self):

        return f'{self.speaker_label}: {self.content[:50]}'
