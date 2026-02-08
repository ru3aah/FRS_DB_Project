import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# =====================================================
# Core
# =====================================================

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key")

DEBUG = os.getenv("DJANGO_DEBUG", "True") == "True"

ALLOWED_HOSTS = ["*"]

# =====================================================
# Applications
# =====================================================

INSTALLED_APPS = [
    # Django default apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Local apps
    "companies",
    "persons",
    "users",
]

# =====================================================
# Middleware
# =====================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Custom middleware
    "companies.middleware.ActiveCompanyRequiredMiddleware",
]

# =====================================================
# URLs / Templates
# =====================================================

ROOT_URLCONF = "FireService_DB.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "companies.context_processors.active_company_and_person",
            ],
        },
    },
]

WSGI_APPLICATION = "FireService_DB.wsgi.application"

# =====================================================
# Database auto-switch logic
# =====================================================


def _running_in_docker() -> bool:
    # Явный флаг из docker-compose
    if os.getenv("IN_DOCKER") == "1":
        return True
    # Стандартный маркер Docker
    return os.path.exists("/.dockerenv")


IN_DOCKER = _running_in_docker()
POSTGRES_HOST = os.getenv("POSTGRES_HOST")

if IN_DOCKER or POSTGRES_HOST:
    # Docker или явный запрос Postgres
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "frs_db"),
            "USER": os.getenv("POSTGRES_USER", "frs_user"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", "ZDz9E4Dv"),
            "HOST": POSTGRES_HOST or "db",
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
        }
    }
else:
    # Локальный dev по умолчанию
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# =====================================================
# Auth / Passwords
# =====================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "users.CustomUser"

# =====================================================
# CSRF / Reverse proxy (nginx https -> gunicorn http)
# =====================================================

# Разрешаем корректную CSRF-проверку при HTTPS через nginx
CSRF_TRUSTED_ORIGINS = [
    "https://localhost",
    "https://127.0.0.1",
    "http://localhost",
    "http://127.0.0.1",
]

# Django должен понимать, что исходно запрос пришёл по HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Учитывать Host, который передал прокси (nginx)
USE_X_FORWARDED_HOST = True

# =====================================================
# I18N / TZ
# =====================================================

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# =====================================================
# Static / Media
# =====================================================

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# =====================================================
# Defaults
# =====================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
