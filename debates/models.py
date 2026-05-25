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
    )

    topic = models.CharField(
        max_length=500,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    rounds_count = models.PositiveIntegerField(
        default=3,
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
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:

        ordering = ['-created_at']

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
    )

    llm_model = models.ForeignKey(
        'agents.LLMModel',
        on_delete=models.PROTECT,
        related_name='debate_participants',
    )

    debate_role = models.ForeignKey(
        'agents.DebateRole',
        on_delete=models.PROTECT,
        related_name='debate_participants',
    )

    order = models.PositiveIntegerField(
        default=0,
    )

    position = models.CharField(
        max_length=10,
        choices=Position.choices,
        blank=True,
    )

    has_conceded = models.BooleanField(
        default=False,
    )

    conceded_at_round = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    class Meta:

        ordering = ['order', 'id']

    def __str__(self):

        return self.speaker_label

    @property
    def speaker_label(self) -> str:

        return (
            f'{self.debate_role.name} '
            f'({self.llm_model.name}) '
            f'#{self.order + 1}'
        )


class DebateRound(models.Model):

    debate = models.ForeignKey(
        Debate,
        on_delete=models.CASCADE,
        related_name='rounds',
    )

    number = models.PositiveIntegerField()

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:

        unique_together = (
            'debate',
            'number',
        )

        ordering = ['number']

    def __str__(self):

        return f'{self.debate_id} - Round {self.number}'


class DebateMessage(models.Model):

    debate = models.ForeignKey(
        Debate,
        on_delete=models.CASCADE,
        related_name='messages',
    )

    round = models.ForeignKey(
        DebateRound,
        on_delete=models.CASCADE,
        related_name='messages',
    )

    participant = models.ForeignKey(
        DebateParticipant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='messages',
    )

    speaker_label = models.CharField(
        max_length=255,
    )

    role_name = models.CharField(
        max_length=100,
    )

    model_name = models.CharField(
        max_length=255,
    )

    content = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:

        ordering = ['created_at']

    def __str__(self):

        return f'{self.speaker_label}: {self.content[:50]}'
