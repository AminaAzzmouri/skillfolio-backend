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
"""

from pathlib import Path
from datetime import timedelta

# -------------------------------------------------------------------
#                   --- Project Paths ---
# -------------------------------------------------------------------
# BASE_DIR points to the root of the project.
# Used as a reference for DB, media, static files, etc.

BASE_DIR = Path(__file__).resolve().parent.parent


# -------------------------------------------------------------------
#                   --- Security ---
# -------------------------------------------------------------------

# SECRET_KEY: Critical for signing cookies, JWT, CSRF tokens.
# ⚠️ Must be kept secret in production (don’t commit real key).
SECRET_KEY = 'django-insecure-fg=!^mo%e4$pi-4bt$=4064i9)licimg7y=9gypm1dl$e^72-z'

# DEBUG: Enables error pages with full tracebacks.
# ⚠️ Only True during development; never True in production!
DEBUG = True    

# ALLOWED_HOSTS: List of domains/IPs Django can serve.
# Empty = dev only. In production, set your domain/IP here.
ALLOWED_HOSTS = []  # In prod, set to your domain/IP


# -------------------------------------------------------------------
#                   --- Installed Applications ---
# -------------------------------------------------------------------
# Each app is a Django "module" providing functionality.
# - Django core apps → admin, auth, sessions, etc.
# - Third-party apps → DRF, CORS, filters
# - Local apps → our custom apps (users)

INSTALLED_APPS = [
    # Django core apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',     # Django REST Framework (API engine)
    'corsheaders',        # Cross-Origin Resource Sharing 'CORS' (for frontend dev)
    'django_filters',     # Filtering support in DRF APIs

    # Local apps
    'users',              # All user/certificates/projects/goals models live here
]


# -------------------------------------------------------------------
#                   --- Middleware ---
# -------------------------------------------------------------------
# Middleware = global request/response processors.
# Order matters: security, sessions, auth, etc.

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # must be high in the list
    'django.middleware.common.CommonMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# -------------------------------------------------------------------
#                   --- REST Framework Config ---
# -------------------------------------------------------------------
# Configures global DRF behavior:
# - Auth with JWT
# - Default permission = IsAuthenticated
# - Filtering, search, ordering
# - Pagination

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
}

# JWT settings (for auth tokens): dev-friendly lifetimes (longer for testing)
# Controls how long tokens stay valid.
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=6),   # re-login only every 6h
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),   # refresh valid for 1 week
}


# -------------------------------------------------------------------
#                   --- URL/WSGI ---
# -------------------------------------------------------------------
# ROOT_URLCONF: root routing file
# WSGI: entrypoint for deployment

ROOT_URLCONF = 'skillfolio_backend.urls'
WSGI_APPLICATION = 'skillfolio_backend.wsgi.application'


# -------------------------------------------------------------------
#                   --- Templates ---
# -------------------------------------------------------------------
# Define template backend, dirs, and context processors.
# We’re not using custom templates yet, but Django admin uses this.

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],  # we can add template dirs later if needed
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


# -------------------------------------------------------------------
#                   --- Database ---
# -------------------------------------------------------------------
# Default: SQLite (lightweight, file-based DB for dev).
# In production, switch to PostgreSQL/MySQL.

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # dev DB
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
# In prod, we’ll switch to MySQL/PostgreSQL.


# -------------------------------------------------------------------
#                   --- Password Validators ---
# -------------------------------------------------------------------
# Adds built-in validation for secure passwords.

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# -------------------------------------------------------------------
#                   --- Internationalization ---
# -------------------------------------------------------------------
# Controls language, timezone, and localization.

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# -------------------------------------------------------------------
#                   --- Static & Media Files ---
# -------------------------------------------------------------------

# Static = CSS/JS/images (served via collectstatic).
STATIC_URL = '/static/'

# Media = user-uploaded files (certificates, etc.).
MEDIA_URL = "/media/"

# MEDIA_ROOT ensures uploaded cert PDFs/images are stored in ./media/
MEDIA_ROOT = BASE_DIR / "media"



# -------------------------------------------------------------------
#                  --- Default PK Field ---
# -------------------------------------------------------------------
# Auto field type (big integer for primary keys).

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# -------------------------------------------------------------------
#                   --- CORS (Development only) ---
# -------------------------------------------------------------------
# Allows frontend (React/Vue) hosted elsewhere to call APIs.
# For now: allow all origins (dev).
# ⚠️ In production: restrict to your frontend domain(s): CORS_ALLOWED_ORIGINS = ["https://your-frontend.com"]

CORS_ALLOW_ALL_ORIGINS = True  
