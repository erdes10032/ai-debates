from django.contrib import admin

from debates.models import (
    Debate,
    DebateMessage,
    DebateParticipant,
    DebateRound,
)


class DebateParticipantInline(admin.TabularInline):

    model = DebateParticipant

    extra = 0

    readonly_fields = (
        'position',
        'has_conceded',
        'conceded_at_round',
    )


@admin.register(Debate)
class DebateAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'topic',
        'user',
        'status',
        'rounds_count',
        'allow_concessions',
        'created_at',
    )

    list_filter = (
        'status',
        'allow_concessions',
    )

    search_fields = ('topic',)

    inlines = [DebateParticipantInline]


@admin.register(DebateRound)
class DebateRoundAdmin(admin.ModelAdmin):

    list_display = (
        'debate',
        'number',
        'created_at',
    )


@admin.register(DebateMessage)
class DebateMessageAdmin(admin.ModelAdmin):

    list_display = (
        'debate',
        'speaker_label',
        'role_name',
        'round',
        'created_at',
    )

    search_fields = (
        'speaker_label',
        'content',
    )
