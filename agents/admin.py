from django.contrib import admin

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
        'is_active',
        'updated_at',
    )

    list_filter = ('is_active',)

    search_fields = ('name',)
