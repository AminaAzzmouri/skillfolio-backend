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
- **CSP (django-csp v4) `frame-ancestors` set so frontend (Vercel/localhost) can embed PDFs** 

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
  so the Authorize button accepts “Bearer <access-token>”.

CSP (django-csp)
- CONTENT_SECURITY_POLICY.DIRECTIVES.frame-ancestors includes 'self', FE origin,
  and localhost dev ports so PDFs/media can be embedded inside <iframe>/<object>.

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
from urllib.parse import urlparse
import os
import sys


# ---------------------------
# Helpers for env parsing
# ---------------------------
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

def _origin_from(url: str) -> str:
    """Turn a full URL into an origin string (scheme://host[:port])."""
    p = urlparse(url or "")
    if not p.scheme or not p.hostname:
        return ""
    return f"{p.scheme}://{p.hostname}" + (f":{p.port}" if p.port else "")


BASE_DIR = Path(__file__).resolve().parent.parent

# Reads DJANGO_DEBUG from env. Defaults to True for dev.
DEBUG = _get_bool("DJANGO_DEBUG", True)


# --- Frontend URL & CORS/CSRF (dev-friendly defaults) ---
# Root redirect will send "/" here (see urls.py). In dev we default to Vite's 5173.
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5174/")

# Dev CORS toggle (allow all while DEBUG=True unless overridden by env).
# In prod set CORS_ALLOW_ALL_ORIGINS=False and specify CORS_ALLOWED_ORIGINS explicitly.
CORS_ALLOW_ALL_ORIGINS = _get_bool("CORS_ALLOW_ALL_ORIGINS", DEBUG)

# Optional explicit allow-list (use in prod). Example:
#   CORS_ALLOWED_ORIGINS="https://fe.example.com,https://staging.example.com"
CORS_ALLOWED_ORIGINS = _get_list("CORS_ALLOWED_ORIGINS", [])
if not CORS_ALLOWED_ORIGINS and FRONTEND_URL:
    # If no list provided, derive a single origin from FRONTEND_URL (e.g., http://localhost:5173)
    derived = _origin_from(FRONTEND_URL)
    if derived:
        CORS_ALLOWED_ORIGINS = [derived]

# Optional: CSRF (useful if you ever move to cookie auth; harmless otherwise)
CSRF_TRUSTED_ORIGINS = _get_list("CSRF_TRUSTED_ORIGINS", [])
if not CSRF_TRUSTED_ORIGINS and FRONTEND_URL:
    derived = _origin_from(FRONTEND_URL)
    if derived:
        CSRF_TRUSTED_ORIGINS = [derived]
        


# Allow preview subdomains (e.g., Vercel previews) via regex if you need it, from env:
#   CORS_ALLOWED_ORIGIN_REGEXES="^https?://.*\.vercel\.app$"
CORS_ALLOWED_ORIGIN_REGEXES = _get_list("CORS_ALLOWED_ORIGIN_REGEXES", [])

# --- Framing / PDF preview ---------------------------------------------------
# FE (Vercel) needs to embed PDFs served by BE (Render), so we must allow framing.
X_FRAME_OPTIONS = "ALLOWALL"  # because FE and BE are different origins

# Build allowed ancestors for CSP frame-ancestors
_frontend_origin = _origin_from(FRONTEND_URL) if FRONTEND_URL else ""
_allowed_ancestors = set(["'self'"])

if _frontend_origin:
    _allowed_ancestors.add(_frontend_origin)

# Include any explicit CORS origins too
for o in CORS_ALLOWED_ORIGINS:
    if o:
        _allowed_ancestors.add(o)

# Optional: allow ALL Vercel preview URLs (e.g., https://feature-123.vercel.app)
if _get_bool("ALLOW_VERCEL_PREVIEWS", False):
    # CORS (API calls) — regex for previews:
    CORS_ALLOWED_ORIGIN_REGEXES.append(r"^https://.*\.vercel\.app$")
    # CSRF (only relevant if you switch to cookie auth later)
    CSRF_TRUSTED_ORIGINS.append("https://*.vercel.app")
    # CSP framing:
    _allowed_ancestors.add("https://*.vercel.app")

# Local dev helpers
_allowed_ancestors.update([
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
])

# django-csp v4+ format:
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        # Let only these origins frame pages/files (PDF <object>/<iframe>)
        "frame-ancestors": sorted(_allowed_ancestors),
    }
}




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
#   - [] in dev (DEBUG=True)
#   - ["127.0.0.1"] in prod (DEBUG=False)
ALLOWED_HOSTS = _get_list("DJANGO_ALLOWED_HOSTS", [] if DEBUG else ["127.0.0.1"])


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
    'announcements',
    'csp',
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
}  # <- used by drf-yasg to render the Authorize dialog as Bearer

MIDDLEWARE = [
    # CORS should be as high as possible
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',

    'django.middleware.security.SecurityMiddleware',
    "csp.middleware.CSPMiddleware",
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Serves static in prod
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
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_THROTTLE_CLASSES": [ "rest_framework.throttling.AnonRateThrottle" ],
    "DEFAULT_THROTTLE_RATES": {"anon": "10/min"},
}

# Disable throtting when running tests
if "test" in sys.argv:
    REST_FRAMEWORK[ "DEFAULT_THROTTLE_CLASSES"] = []
    REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {}

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
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }


# --- Database (Neon when DATABASE_URL set; SQLite otherwise) ---
import dj_database_url

DB_URL = os.environ.get("DATABASE_URL", "").strip()
IS_POSTGRES = DB_URL.startswith("postgres://") or DB_URL.startswith("postgresql://")

if DB_URL:
    # Use the URL as-is. Neon already includes ?sslmode=require in the URL.
    DATABASES = {
        "default": dj_database_url.parse(
            DB_URL,
            conn_max_age=600,
            ssl_require=IS_POSTGRES,  # only apply SSL flag for Postgres URLs
        )
    }
else:
    # Default to SQLite for local dev/CI
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

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
    AWS_QUERYSTRING_AUTH = _get_bool("AWS_QUERYSTRING_AUTH", False)  # clean URLs if files are public
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

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "loggers": {
        "django.request": {  # 500s, 404s with exceptions
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": True,
        },
        "django": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
}
