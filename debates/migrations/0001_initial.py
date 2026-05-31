import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('agents', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Debate',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'topic',
                    models.CharField(
                        max_length=500,
                        verbose_name='Topic',
                    ),
                ),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('pending', 'Pending'),
                            ('in_progress', 'In progress'),
                            ('completed', 'Completed'),
                            ('failed', 'Failed'),
                        ],
                        default='pending',
                        max_length=20,
                        verbose_name='Status',
                    ),
                ),
                (
                    'rounds_count',
                    models.PositiveIntegerField(
                        default=3,
                        verbose_name='Rounds count',
                    ),
                ),
                (
                    'allow_concessions',
                    models.BooleanField(
                        default=True,
                        help_text=(
                            'Participants may concede when their position '
                            'is no longer defensible'
                        ),
                        verbose_name='Allow concessions',
                    ),
                ),
                (
                    'consensus',
                    models.TextField(
                        blank=True,
                        verbose_name='Consensus',
                    ),
                ),
                (
                    'created_at',
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name='Created at',
                    ),
                ),
                (
                    'updated_at',
                    models.DateTimeField(
                        auto_now=True,
                        verbose_name='Updated at',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='debates',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='User',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Debate',
                'verbose_name_plural': 'Debates',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='DebateParticipant',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'order',
                    models.PositiveIntegerField(
                        default=0,
                        verbose_name='Order',
                    ),
                ),
                (
                    'position',
                    models.CharField(
                        blank=True,
                        choices=[
                            ('support', 'Support'),
                            ('oppose', 'Oppose'),
                        ],
                        max_length=10,
                        verbose_name='Position',
                    ),
                ),
                (
                    'has_conceded',
                    models.BooleanField(
                        default=False,
                        verbose_name='Has conceded',
                    ),
                ),
                (
                    'conceded_at_round',
                    models.PositiveIntegerField(
                        blank=True,
                        null=True,
                        verbose_name='Conceded at round',
                    ),
                ),
                (
                    'debate',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='participants',
                        to='debates.debate',
                        verbose_name='Debate',
                    ),
                ),
                (
                    'debate_role',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='debate_participants',
                        to='agents.debaterole',
                        verbose_name='Debate role',
                    ),
                ),
                (
                    'llm_model',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='debate_participants',
                        to='agents.llmmodel',
                        verbose_name='LLM model',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Debate participant',
                'verbose_name_plural': 'Debate participants',
                'ordering': ['order', 'id'],
            },
        ),
        migrations.CreateModel(
            name='DebateRound',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'number',
                    models.PositiveIntegerField(
                        verbose_name='Number',
                    ),
                ),
                (
                    'created_at',
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name='Created at',
                    ),
                ),
                (
                    'debate',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='rounds',
                        to='debates.debate',
                        verbose_name='Debate',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Debate round',
                'verbose_name_plural': 'Debate rounds',
                'ordering': ['number'],
                'unique_together': {('debate', 'number')},
            },
        ),
        migrations.CreateModel(
            name='DebateMessage',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'speaker_label',
                    models.CharField(
                        max_length=255,
                        verbose_name='Speaker label',
                    ),
                ),
                (
                    'role_name',
                    models.CharField(
                        max_length=100,
                        verbose_name='Role name',
                    ),
                ),
                (
                    'model_name',
                    models.CharField(
                        max_length=255,
                        verbose_name='Model name',
                    ),
                ),
                (
                    'content',
                    models.TextField(
                        verbose_name='Content',
                    ),
                ),
                (
                    'created_at',
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name='Created at',
                    ),
                ),
                (
                    'debate',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='messages',
                        to='debates.debate',
                        verbose_name='Debate',
                    ),
                ),
                (
                    'participant',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='messages',
                        to='debates.debateparticipant',
                        verbose_name='Participant',
                    ),
                ),
                (
                    'round',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='messages',
                        to='debates.debateround',
                        verbose_name='Round',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Debate message',
                'verbose_name_plural': 'Debate messages',
                'ordering': ['created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='debatemessage',
            constraint=models.UniqueConstraint(
                fields=('round', 'participant'),
                name='unique_debate_message_per_participant_round',
            ),
        ),
    ]
