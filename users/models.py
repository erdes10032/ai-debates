from pathlib import Path

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from .validators import validate_avatar


def avatar_upload_path(instance, filename):

    extension = Path(filename).suffix

    return (
        f'avatars/'
        f'{instance.id}/'
        f'avatar{extension}'
    )


class User(AbstractUser):

    class Gender(models.TextChoices):

        MALE = 'male', _('Male')

        FEMALE = 'female', _('Female')

    email = models.EmailField(
        unique=True,
        verbose_name=_('Email'),
    )

    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
        default=Gender.MALE,
        verbose_name=_('Gender'),
    )

    avatar = models.ImageField(
        upload_to=avatar_upload_path,
        validators=[validate_avatar],
        blank=True,
        null=True,
        verbose_name=_('Avatar'),
    )

    bio = models.TextField(
        blank=True,
        verbose_name=_('Bio'),
    )

    USERNAME_FIELD = 'email'

    REQUIRED_FIELDS = [
        'username',
    ]

    class Meta:

        verbose_name = _('User')

        verbose_name_plural = _('Users')

    def __str__(self):

        return self.email