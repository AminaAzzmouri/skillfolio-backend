"""
settings.py — Django project configuration for Skillfolio Backend

Purpose
===============================================================================
Centralize framework configuration:
- Apps, middleware, DB, REST framework, JWT auth, CORS, i18n, static/media

Key Integrations
- REST framework defaults: authentication, permissions, filtering, pagination
- SimpleJWT for stateless auth (access + refresh tokens)
- SimpleJWT blacklist app to invalidate refresh tokens on logout
- drf-yasg for Swagger UI and OpenAPI schema
- CORS middleware for FE ↔ BE development

Security
- Never commit real production secrets to version control.
- For production, restrict CORS and configure a hardened DB.
"""

from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

# ⚠️ Replace with a real secret in production
SECRET_KEY = 'django-insecure-fg=!^mo%e4$pi-4bt$=4064i9)licimg7y=9gypm1dl$e^72-z'
DEBUG = True
ALLOWED_HOSTS = []

INSTALLED_APPS = [
    # Django core
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'corsheaders',
    'django_filters',                             # filtering backend for DRF
    'drf_yasg',                                   # Swagger/OpenAPI docs
    'rest_framework_simplejwt.token_blacklist',   # refresh-token blacklist

    # Local apps
    'users',
]

MIDDLEWARE = [
    # CORS should be as high as possible
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',

    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    # Optionally rename query params for FE sugar:
    # "SEARCH_PARAM": "search",
    # "ORDERING_PARAM": "ordering",
}

# JWT lifetimes (dev-friendly defaults)
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=6),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    # If you later enable rotation:
    # "ROTATE_REFRESH_TOKENS": True,
    # "BLACKLIST_AFTER_ROTATION": True,
}

ROOT_URLCONF = 'skillfolio_backend.urls'
WSGI_APPLICATION = 'skillfolio_backend.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # Add template dirs here if you adopt server-side HTML rendering
        'DIRS': [],
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

# SQLite for development; switch to Postgres/MySQL in production
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static & media
STATIC_URL = '/static/'
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Dev CORS (lock down in production)
CORS_ALLOW_ALL_ORIGINS = True
