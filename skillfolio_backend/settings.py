"""
settings.py — Django project configuration for Skillfolio Backend

What this file configures
===============================================================================
- Core Django wiring (INSTALLED_APPS, MIDDLEWARE, TEMPLATES, DB)
- REST Framework defaults (JWT auth, IsAuthenticated, filtering, pagination)
- SimpleJWT (access/refresh) + blacklist app (logout invalidates refresh)
- CORS for FE ↔ BE requests
- Static + media handling, including optional S3 via django-storages
- Production serving of static via WhiteNoise
- **Swagger (drf-yasg) configured to use Bearer tokens in the Authorize dialog**  ← NEW

How environment variables drive behavior (deployment-safe)
===============================================================================
DJANGO_DEBUG            -> Enables dev mode when true. Defaults to True locally.
DJANGO_SECRET_KEY       -> Required when DJANGO_DEBUG=False (production).
DJANGO_ALLOWED_HOSTS    -> Comma-separated list of allowed hostnames in prod.
CORS_ALLOW_ALL_ORIGINS  -> Dev toggle to allow any origin (default True in dev).
CORS_ALLOWED_ORIGINS    -> Comma-separated list of exact origins (prod).
USE_S3_MEDIA            -> When true, use S3 for media (django-storages).
AWS_STORAGE_BUCKET_NAME -> S3 bucket for uploads.
AWS_S3_REGION_NAME      -> AWS region (e.g., us-east-1).
AWS_ACCESS_KEY_ID       -> AWS key (omit if using instance role).
AWS_SECRET_ACCESS_KEY   -> AWS secret (omit if using instance role).
AWS_S3_CUSTOM_DOMAIN    -> Optional CDN/CloudFront domain for media URLs.
AWS_QUERYSTRING_AUTH    -> True to sign URLs; False for public-read objects.

Why some ordering matters
===============================================================================
- We compute DEBUG first so SECRET_KEY can enforce “prod requires a key.”
- SECRET_KEY only falls back to a dev key when DEBUG=True.
- ALLOWED_HOSTS/CORS read from env with dev-safe defaults so you can flip
  to production behavior without code changes.

Quick reference of important sections
===============================================================================
REST_FRAMEWORK  -> JWT auth, IsAuthenticated default, filters, pagination.
SIMPLE_JWT      -> Token lifetimes; rotation keys are ready but commented.
DATABASES       -> SQLite in dev; you can wire DATABASE_URL to Postgres in prod.
Static files    -> STATIC_ROOT + WhiteNoise for production static serving.
S3 section      -> Activated when USE_S3_MEDIA=True; sets DEFAULT_FILE_STORAGE
                   and MEDIA_URL accordingly.
Swagger (drf-yasg)
- SWAGGER_SETTINGS sets a Bearer security scheme and disables session auth,
  so the Authorize button accepts “Bearer <access-token>”.                 ← NEW

Deployment notes (Render-friendly)
===============================================================================
- Add to requirements.txt: gunicorn, whitenoise (already done here).
- Set STATIC_ROOT (already done) and add WhiteNoise middleware (done).
- runtime.txt pins Python (e.g., python-3.11.9).
- Build command example:
    pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate --noinput
- Start command example:
    gunicorn skillfolio_backend.wsgi:application --log-file -
- Minimal env vars:
    DJANGO_SECRET_KEY=<random>
    DJANGO_DEBUG=False
    DJANGO_ALLOWED_HOSTS=<your-service>.onrender.com
    CORS_ALLOW_ALL_ORIGINS=True   (for quick tests)  OR
    CORS_ALLOW_ALL_ORIGINS=False + CORS_ALLOWED_ORIGINS=<https://your-fe.example.com>
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



SWAGGER_SETTINGS = {
    "USE_SESSION_AUTH": False,  # hide Django session login in the docs
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "Paste: Bearer <access-token>",
        }
    },
} # <- used by drf-yasg to render the Authorize dialog as Bearer


MIDDLEWARE = [
    # CORS should be as high as possible
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',

    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',      # WhiteNoise will serve Django Admin CSS/JS and any collected assets in production.
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
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
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
STATIC_ROOT = BASE_DIR / "staticfiles"

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
