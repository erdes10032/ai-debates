from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from agents.models import (
    DebateRole,
    LLMModel,
)


@admin.register(LLMModel)
class LLMModelAdmin(admin.ModelAdmin):

    list_display = (
        'name',
        'model_id',
        'is_active',
        'updated_at',
    )

    list_filter = ('is_active',)

    search_fields = (
        'name',
        'model_id',
    )


@admin.register(DebateRole)
class DebateRoleAdmin(admin.ModelAdmin):

    list_display = (
        'name',
        'localized_name',
        'is_active',
        'allows_concession',
        'updated_at',
    )

    list_filter = (
        'is_active',
        'allows_concession',
    )

    search_fields = ('name',)

    @admin.display(description=_('Localized name'))
    def localized_name(self, obj):
        return obj.localized_name
