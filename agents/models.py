from django.db import models
from django.utils.translation import gettext_lazy as _


class LLMModel(models.Model):

    name = models.CharField(
        max_length=100,
        help_text=_('Display name in the debate UI'),
    )

    model_id = models.CharField(
        max_length=255,
        unique=True,
        help_text=_(
            'OpenRouter model ID, e.g. meta-llama/llama-3.3-70b-instruct:free'
        ),
    )

    description = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:

        verbose_name = _('LLM model')

        verbose_name_plural = _('LLM models')

        ordering = ['name']

    def __str__(self):

        return self.name


class DebateRole(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text=_('Display name, e.g. Critic'),
    )

    behavior = models.TextField(
        help_text=_(
            'Instructions for how this role argues in a debate'
        ),
    )

    is_active = models.BooleanField(
        default=True,
    )

    allows_concession = models.BooleanField(
        default=True,
        verbose_name=_('Allows concession'),
        help_text=_(
            'If enabled, this role may concede during a debate '
            'when concessions are allowed'
        ),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:

        verbose_name = _('Debate role')

        verbose_name_plural = _('Debate roles')

        ordering = ['name']

    def __str__(self):

        return self.name

