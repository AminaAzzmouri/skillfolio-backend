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


import os

def _get_bool(env_key: str, default: bool = False) -> bool:
    """Parse booleans from env like '1', 'true', 'yes'."""
    raw = os.environ.get(env_key, str(default))
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}

def _get_list(env_key: str, default=None):
    """Parse comma-separated lists from env (e.g., 'a.com,b.com')."""
    if default is None:
        default = []
    raw = os.environ.get(env_key)
    if not raw:
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


BASE_DIR = Path(__file__).resolve().parent.parent

# Reads DJANGO_DEBUG from env. Defaults to True for dev.
DEBUG = _get_bool("DJANGO_DEBUG", True)


# SECRET_KEY with safe production enforcement
#    - In dev (DEBUG=True): fallback to a dev key if none provided
#    - In prod (DEBUG=False): require DJANGO_SECRET_KEY

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or (
    "django-insecure-fg=!^mo%e4$pi-4bt$=4064i9)licimg7y=9gypm1dl$e^72-z" if DEBUG else None
)
if not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG=False")


# Hosts from env (defaults depend on DEBUG) 
# Reads DJANGO_ALLOWED_HOSTS as a comma-separated list. Defaults to:
#           -empty list [] in dev (DEBUG=True)
#           -["127.0.0.1"] in prod (DEBUG=False)

ALLOWED_HOSTS = _get_list("DJANGO_ALLOWED_HOSTS", [] if DEBUG else ["127.0.0.1"])


# Dev CORS defaults (lock down in prod via env)
CORS_ALLOW_ALL_ORIGINS = _get_bool("CORS_ALLOW_ALL_ORIGINS", DEBUG)

# If you want to control exact origins in prod, set CORS_ALLOWED_ORIGINS in env:
# e.g. CORS_ALLOWED_ORIGINS="https://sf-frontend.vercel.app,https://skillfolio.example.com"
CORS_ALLOWED_ORIGINS = _get_list("CORS_ALLOWED_ORIGINS", [])

# These keep your current dev behavior but let you flip to safe prod settings by setting env vars.
# Lets you safely switch between permissive dev mode and restricted prod mode.



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



# --- S3 media storage (optional; prod) ---
USE_S3 = _get_bool("USE_S3_MEDIA", False)

if USE_S3:
    INSTALLED_APPS += ["storages"]
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = os.environ.get("AWS_S3_REGION_NAME", "us-east-1")
    AWS_S3_SIGNATURE_VERSION = os.environ.get("AWS_S3_SIGNATURE_VERSION", "s3v4")
    AWS_S3_ADDRESSING_STYLE = os.environ.get("AWS_S3_ADDRESSING_STYLE", "virtual")
    AWS_QUERYSTRING_AUTH = _get_bool("AWS_QUERYSTRING_AUTH", False)  # make URLs clean if files are public
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None  # let bucket policy control ACLs

    # Credentials from env/role
    AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")

    # Optional: custom domain (CloudFront or S3 website)
    AWS_S3_CUSTOM_DOMAIN = os.environ.get("AWS_S3_CUSTOM_DOMAIN")  # e.g. cdn.skillfolio.example.com
    if AWS_S3_CUSTOM_DOMAIN:
        MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/"
    else:
        MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/"
