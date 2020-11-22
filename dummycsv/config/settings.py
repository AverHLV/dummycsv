from django.core.exceptions import ImproperlyConfigured

from os import environ
from pathlib import Path
from configparser import ConfigParser

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / 'config' / environ.get('DMCSV_CONF', 'config.ini')

if not CONFIG_PATH.is_file():
    raise ImproperlyConfigured(f'Config file with specified path not found: {CONFIG_PATH}')

config = ConfigParser()
config.read(CONFIG_PATH)

# General

SECRET_KEY = config.get('django', 'secret_key')

DEBUG = config.get('django', 'debug', fallback='true') == 'true'

ALLOWED_HOSTS = config.get('django', 'hosts').split()

ROOT_URLCONF = 'config.urls'

WSGI_APPLICATION = 'config.wsgi.application'

# Application definition

INSTALLED_APPS = [
    # use whitenoise serving on development

    'whitenoise.runserver_nostatic',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'drf_yasg',

    # own apps

    'auth_api',
    'datasets',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Database

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config.get('database', 'name'),
        'USER': config.get('database', 'user'),
        'PASSWORD': config.get('database', 'password'),
        'HOST': config.get('database', 'host'),
        'PORT': config.get('database', 'port'),

        'TEST': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config.get('database_test', 'name'),
            'USER': config.get('database_test', 'user'),
            'PASSWORD': config.get('database_test', 'password'),
            'HOST': config.get('database_test', 'host'),
            'PORT': config.get('database_test', 'port'),
        }
    }
}

# Password validation

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

# Cache

if config.get('cache', 'user', fallback=None) is None:
    redis_url = f'redis://{config.get("cache", "host")}:{config.get("cache", "port")}/0'

else:
    user = config.get('cache', 'user')
    password = config.get('cache', 'password')
    host = config.get('cache', 'host')
    port = config.get('cache', 'port')

    redis_url = f'redis://{user}:{password}@{host}:{port}/0'

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': redis_url,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_COOKIE_AGE = 3600 * 12

# REST API

REST_API_DOCS_URL = config.get('django', 'swagger_url', fallback=None)

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'datasets.pagination.CustomLimitOffsetPagination',
    'PAGE_SIZE': 30,

    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
    ),

    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),

    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ]
}

if DEBUG:
    REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'].append(
        'rest_framework.renderers.BrowsableAPIRenderer'
    )

# Logging configuration

if not DEBUG:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,

        'formatters': {
            'formatter': {
                'format': '{levelname} {asctime} {module} {message}',
                'style': '{',
            },
        },

        'handlers': {
            'file_handler': {
                'level': 'INFO',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': 'dmcsv.log',
                'formatter': 'formatter',
                'maxBytes': 10485760,  # 10 MB
            },
        },

        'loggers': {
            'django': {
                'handlers': ['file_handler'],
                'level': 'INFO',
                'propagate': True,
            },
        }
    }

# Fixtures

FIXTURE_DIRS = BASE_DIR / 'fixtures',

# Internationalization

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'static'
STATICFILES_DIRS = BASE_DIR / 'assets',

# User files

MEDIA_URL = '/datasets/files/'
MEDIA_ROOT = BASE_DIR / 'media'

# Celery

CELERY_BROKER_URL = redis_url
