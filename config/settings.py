from pathlib import Path
import os
import sys

import dj_database_url
from dotenv import load_dotenv
from django.utils.translation import gettext_lazy as _


_TESTING = 'pytest' in sys.modules

if _TESTING:
    os.environ.setdefault(
        'SECRET_KEY',
        'django-insecure-test-key',
    )
    os.environ.setdefault(
        'OPENROUTER_API_KEY',
        'test-openrouter-key',
    )

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY')

if not SECRET_KEY:
    raise ValueError('SECRET_KEY is missing in .env')

DEBUG = os.getenv('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        'ALLOWED_HOSTS',
        '127.0.0.1,localhost',
    ).split(',')
    if host.strip()
]

RENDER_EXTERNAL_HOSTNAME = os.getenv('RENDER_EXTERNAL_HOSTNAME')

if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        'CSRF_TRUSTED_ORIGINS',
        '',
    ).split(',')
    if origin.strip()
]

if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(
        f'https://{RENDER_EXTERNAL_HOSTNAME}',
    )


INSTALLED_APPS = [
    'daphne',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django_celery_results',

    'channels',

    'allauth',
    'allauth.account',
    'allauth.socialaccount',

    'core',
    'users',
    'debates',
    'agents',

]


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


ROOT_URLCONF = 'config.urls'


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',

        'DIRS': [
            BASE_DIR / 'templates',
        ],

        'APP_DIRS': True,

        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

if DEBUG:
    TEMPLATES[0]['OPTIONS']['context_processors'].insert(
        0,
        'django.template.context_processors.debug',
    )


WSGI_APPLICATION = 'config.wsgi.application'


DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            ssl_require=not DEBUG,
        ),
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',

            'NAME': os.getenv('DB_NAME'),

            'USER': os.getenv('DB_USER'),

            'PASSWORD': os.getenv('DB_PASSWORD'),

            'HOST': os.getenv('DB_HOST'),

            'PORT': os.getenv('DB_PORT'),
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },

    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },

    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },

    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


LANGUAGE_CODE = 'en'

LANGUAGES = [
    ('en', _('English')),
    ('ru', _('Russian')),
]

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


LOCALE_PATHS = [
    BASE_DIR / 'locale',
]


STATIC_URL = '/static/'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    'default': {
        'BACKEND': (
            'django.core.files.storage.FileSystemStorage'
        ),
    },
    'staticfiles': {
        'BACKEND': (
            'whitenoise.storage.CompressedStaticFilesStorage'
        ),
    },
}


MEDIA_URL = '/media/'

MEDIA_ROOT = BASE_DIR / 'media'


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


AUTH_USER_MODEL = 'users.User'


AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',

    'allauth.account.auth_backends.AuthenticationBackend',
]


SITE_ID = 1


LOGIN_URL = '/accounts/login/'

LOGIN_REDIRECT_URL = '/'

LOGOUT_REDIRECT_URL = '/'


ACCOUNT_FORMS = {
    'signup': 'users.forms.CustomSignupForm',
}


ACCOUNT_USER_MODEL_USERNAME_FIELD = 'username'

ACCOUNT_LOGIN_METHODS = {
    'email',
}

ACCOUNT_SIGNUP_FIELDS = [
    'email*',
    'username*',
    'password1*',
    'password2*',
]

ACCOUNT_UNIQUE_EMAIL = True

ACCOUNT_EMAIL_VERIFICATION = 'mandatory'

ACCOUNT_CONFIRM_EMAIL_ON_GET = True

ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 1

ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True

ACCOUNT_SESSION_REMEMBER = True

ACCOUNT_RATE_LIMITS = {
    'login_failed': '5/5m',
    'signup': '5/10m',
}


EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

EMAIL_HOST = 'smtp.yandex.ru'

EMAIL_PORT = 465

EMAIL_USE_SSL = True

EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')

EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')

DEFAULT_FROM_EMAIL = os.getenv('EMAIL_HOST_USER')

SERVER_EMAIL = os.getenv('EMAIL_HOST_USER')

EMAIL_TIMEOUT = 10

ADMINS = [
    (
        'admin',
        os.getenv('EMAIL_ADMIN'),
    ),
]


SECURE_BROWSER_XSS_FILTER = True

SECURE_CONTENT_TYPE_NOSNIFF = True

X_FRAME_OPTIONS = 'DENY'

CSRF_COOKIE_HTTPONLY = True

SESSION_COOKIE_HTTPONLY = True

SESSION_COOKIE_SECURE = False if DEBUG else True

CSRF_COOKIE_SECURE = False if DEBUG else True

SECURE_SSL_REDIRECT = False if DEBUG else True

SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0

SECURE_HSTS_INCLUDE_SUBDOMAINS = True

SECURE_HSTS_PRELOAD = True

SESSION_COOKIE_SAMESITE = 'Lax'

CSRF_COOKIE_SAMESITE = 'Lax'

SECURE_REFERRER_POLICY = 'same-origin'

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = (
        'HTTP_X_FORWARDED_PROTO',
        'https',
    )


FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

if not OPENROUTER_API_KEY and not _TESTING:
    raise ValueError(
        'OPENROUTER_API_KEY is missing in .env',
    )

DEBATE_ROUND_DELAY_SECONDS = float(
    os.getenv('DEBATE_ROUND_DELAY_SECONDS', '4'),
)

# CELERY

CELERY_RESULT_BACKEND = 'django-db'

CELERY_ACCEPT_CONTENT = ['json']

CELERY_TASK_SERIALIZER = 'json'

CELERY_RESULT_SERIALIZER = 'json'

CELERY_TIMEZONE = TIME_ZONE

CELERY_TASK_TRACK_STARTED = True

CELERY_TASK_TIME_LIMIT = 60 * 10

# Parallel debates: run worker with enough processes, e.g.
# celery -A config worker -l info --concurrency=4
CELERY_WORKER_CONCURRENCY = int(
    os.getenv('CELERY_WORKER_CONCURRENCY', '4'),
)

# One long debate task per worker slot (fair scheduling).
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL')

REDIS_URL = os.getenv('REDIS_URL') or CELERY_BROKER_URL

if not REDIS_URL:
    raise ValueError(
        'REDIS_URL or CELERY_BROKER_URL must be set in .env',
    )


def _redis_points_to_localhost(url: str) -> bool:

    return any(
        marker in url
        for marker in (
            '127.0.0.1',
            'localhost',
            '::1',
        )
    )


_redis_url_env = os.getenv('REDIS_URL', '').strip()

if (
    _redis_url_env
    and _redis_points_to_localhost(_redis_url_env)
    and CELERY_BROKER_URL
    and not _redis_points_to_localhost(CELERY_BROKER_URL)
):
    CHANNEL_REDIS_URL = CELERY_BROKER_URL
else:
    CHANNEL_REDIS_URL = REDIS_URL

ASGI_APPLICATION = 'config.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [CHANNEL_REDIS_URL],
            'symmetric_encryption_keys': [
                SECRET_KEY,
            ],
        },
    },
}

LOGGING = {
    'version': 1,

    'disable_existing_loggers': False,

    'formatters': {
        'standard': {
            'format': (
                '%(asctime)s [%(levelname)s] '
                '%(name)s: %(message)s'
            ),
        },
    },

    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
    },

    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

if DEBUG:
    LOGGING['handlers']['file'] = {
        'class': 'logging.FileHandler',
        'filename': BASE_DIR / 'django.log',
        'formatter': 'standard',
    }
    LOGGING['loggers']['django']['handlers'].append('file')