"""
settings.py — Django project configuration for Skillfolio Backend

Purpose
===============================================================================
Central configuration file that controls how Django behaves:
- Installed apps
- Middleware
- REST framework (auth, permissions, filters, pagination)
- Database settings
- Media & static files
- Internationalization
- Security-related options

This file is critical to ensure the backend runs properly and integrates
with the frontend (via JWT + CORS).

Week 4 Notes
-------------------------------------------------------------------------------
- Models/serializers/admin were enhanced; settings itself remains valid.
- If you later add JWT Blacklist or Swagger, we’ll update INSTALLED_APPS/URLs.

Week 5 Update (feature/auth-logout-blacklist)
-------------------------------------------------------------------------------
- Enabled `rest_framework_simplejwt.token_blacklist` to support blacklisting
  refresh tokens on logout (server-side invalidation).
"""

from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

# ⚠️ Never commit a real secret key in production
SECRET_KEY = 'django-insecure-fg=!^mo%e4$pi-4bt$=4064i9)licimg7y=9gypm1dl$e^72-z'
DEBUG = True
ALLOWED_HOSTS = []

INSTALLED_APPS = [
    # Django core apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',
    'corsheaders',
    'django_filters',      # required for DRF filter backends
    'rest_framework_simplejwt.token_blacklist',  # <-- NEW: enable refresh token blacklist

    # Local apps
    'users',
]

MIDDLEWARE = [
    # CORS middleware should be as high as possible
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
    # (Optional) FE sugar:
    # "SEARCH_PARAM": "search",
    # "ORDERING_PARAM": "ordering",
}

# JWT lifetimes (dev-friendly). Blacklist support is enabled via installed app.
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=6),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    # If you later enable token rotation, you can also set:
    # "ROTATE_REFRESH_TOKENS": True,
    # "BLACKLIST_AFTER_ROTATION": True,
}

ROOT_URLCONF = 'skillfolio_backend.urls'
WSGI_APPLICATION = 'skillfolio_backend.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],   # add template dirs if you start using server-side rendering
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

# SQLite for development (switch to Postgres/MySQL in production)
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

# Dev CORS (lock down in prod)
CORS_ALLOW_ALL_ORIGINS = True
