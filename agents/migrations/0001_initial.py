from django.db import migrations, models


DEFAULT_ROLES = (
    (
        'Debater',
        (
            'Aggressive and persuasive. Actively attacks weak logic '
            'and strongly defends ideas.'
        ),
    ),
    (
        'Mediator',
        (
            'Calm and balanced. Looks for compromise points while '
            'still defending position.'
        ),
    ),
    (
        'Critic',
        (
            'Highly analytical. Focuses on contradictions, logical '
            'flaws and weak evidence.'
        ),
    ),
    (
        'Visionary',
        (
            'Creative and future-oriented. Uses big-picture thinking '
            'and bold predictions.'
        ),
    ),
)

DEFAULT_MODELS = (
    (
        'Llama 3.3 70B (free)',
        'meta-llama/llama-3.3-70b-instruct:free',
    ),
    (
        'Qwen3 Next 80B (free)',
        'qwen/qwen3-next-80b-a3b-instruct:free',
    ),
    (
        'DeepSeek V4 Flash (free)',
        'deepseek/deepseek-v4-flash:free',
    ),
)


def seed_catalog(apps, schema_editor):

    LLMModel = apps.get_model('agents', 'LLMModel')
    DebateRole = apps.get_model('agents', 'DebateRole')

    for name, model_id in DEFAULT_MODELS:
        LLMModel.objects.get_or_create(
            model_id=model_id,
            defaults={
                'name': name,
                'is_active': True,
            },
        )

    for name, behavior in DEFAULT_ROLES:
        DebateRole.objects.get_or_create(
            name=name,
            defaults={
                'behavior': behavior,
                'is_active': True,
                'allows_concession': True,
            },
        )


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='LLMModel',
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
                    'name',
                    models.CharField(
                        help_text='Display name in the debate UI',
                        max_length=100,
                        verbose_name='Name',
                    ),
                ),
                (
                    'model_id',
                    models.CharField(
                        help_text=(
                            'OpenRouter model ID, e.g. '
                            'meta-llama/llama-3.3-70b-instruct:free'
                        ),
                        max_length=255,
                        unique=True,
                        verbose_name='Model ID',
                    ),
                ),
                (
                    'description',
                    models.TextField(
                        blank=True,
                        verbose_name='Description',
                    ),
                ),
                (
                    'is_active',
                    models.BooleanField(
                        default=True,
                        verbose_name='Is active',
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
            ],
            options={
                'verbose_name': 'LLM model',
                'verbose_name_plural': 'LLM models',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='DebateRole',
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
                    'name',
                    models.CharField(
                        help_text=(
                            'Stable English label (e.g. Critic). '
                            'Translated in the UI via locale files.'
                        ),
                        max_length=100,
                        unique=True,
                        verbose_name='Name',
                    ),
                ),
                (
                    'behavior',
                    models.TextField(
                        help_text=(
                            'Instructions for how this role argues '
                            'in a debate'
                        ),
                        verbose_name='Behavior',
                    ),
                ),
                (
                    'is_active',
                    models.BooleanField(
                        default=True,
                        verbose_name='Is active',
                    ),
                ),
                (
                    'allows_concession',
                    models.BooleanField(
                        default=True,
                        help_text=(
                            'If enabled, this role may concede during '
                            'a debate when concessions are allowed'
                        ),
                        verbose_name='Allows concession',
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
            ],
            options={
                'verbose_name': 'Debate role',
                'verbose_name_plural': 'Debate roles',
                'ordering': ['name'],
            },
        ),
        migrations.RunPython(
            seed_catalog,
            migrations.RunPython.noop,
        ),
    ]
