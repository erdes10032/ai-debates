from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image

from users.validators import validate_avatar


class ValidateAvatarTests(SimpleTestCase):

    def _png_file(self, *, size: int = 32) -> SimpleUploadedFile:

        image = Image.new('RGB', (size, size), color='red')
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)

        return SimpleUploadedFile(
            'avatar.png',
            buffer.read(),
            content_type='image/png',
        )

    def test_accepts_valid_png(self):

        validate_avatar(self._png_file())

    def test_rejects_invalid_extension(self):

        uploaded = SimpleUploadedFile(
            'avatar.exe',
            b'not-an-image',
            content_type='application/octet-stream',
        )

        with self.assertRaises(ValidationError):
            validate_avatar(uploaded)

    def test_rejects_oversized_file(self):

        uploaded = SimpleUploadedFile(
            'avatar.png',
            b'0' * (5 * 1024 * 1024 + 1),
            content_type='image/png',
        )

        with self.assertRaises(ValidationError):
            validate_avatar(uploaded)
