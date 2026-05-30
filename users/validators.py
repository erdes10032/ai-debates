from pathlib import Path

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from PIL import Image, UnidentifiedImageError


ALLOWED_IMAGE_EXTENSIONS = {
    '.jpg',
    '.jpeg',
    '.png',
    '.webp',
}

ALLOWED_IMAGE_FORMATS = {
    'JPEG',
    'PNG',
    'WEBP',
}

MAX_AVATAR_SIZE = 5 * 1024 * 1024


def validate_avatar(file):

    if not file:
        return

    # -----------------------------------
    # Проверка расширения
    # -----------------------------------

    extension = Path(file.name).suffix.lower()

    if extension not in ALLOWED_IMAGE_EXTENSIONS:

        raise ValidationError(
            _('Only JPG, JPEG, PNG and WEBP files are allowed.')
        )

    # -----------------------------------
    # Проверка размера
    # -----------------------------------

    if file.size > MAX_AVATAR_SIZE:

        raise ValidationError(
            _('Avatar size must not exceed 5 MB.')
        )

    try:

        file.seek(0)

        header = file.read(512)

        # -----------------------------------
        # Проверка опасных сигнатур
        # -----------------------------------

        dangerous_signatures = [
            b'MZ',              # exe
            b'<script',
            b'<?php',
            b'#!/bin/bash',
            b'PK\x03\x04',      # zip/apk/docx/jar
        ]

        header_lower = header.lower()

        for signature in dangerous_signatures:

            if signature.lower() in header_lower:

                raise ValidationError(
                    _('Potentially dangerous file detected.')
                )

        # -----------------------------------
        # Проверка через Pillow
        # -----------------------------------

        file.seek(0)

        image = Image.open(file)

        image.verify()

        # reopen after verify
        file.seek(0)

        image = Image.open(file)

        if image.format not in ALLOWED_IMAGE_FORMATS:

            raise ValidationError(
                _('Invalid image format.')
            )

    except ValidationError:
        raise

    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
    ):

        raise ValidationError(
            _('Invalid or corrupted image.')
        )

    finally:

        file.seek(0)