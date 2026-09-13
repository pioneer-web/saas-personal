import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    return [
        item.strip()
        for item in os.getenv(name, default).split(",")
        if item.strip()
    ]


DEBUG = env_bool("DJANGO_DEBUG", False)

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "").strip()

if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "unsafe-dev-key-only-for-local-debug"
    else:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY é obrigatório em produção."
        )

if not DEBUG and (
    len(SECRET_KEY) < 50
    or SECRET_KEY.startswith("unsafe-")
    or SECRET_KEY == "troque-por-uma-chave-forte"
):
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY fraca ou de exemplo."
    )


if DEBUG:
    ALLOWED_HOSTS = env_list(
        "DJANGO_ALLOWED_HOSTS",
        "localhost,127.0.0.1",
    )
else:
    raw_hosts = os.getenv("DJANGO_ALLOWED_HOSTS", "").strip()
    if not raw_hosts:
        raise ImproperlyConfigured(
            "DJANGO_ALLOWED_HOSTS é obrigatório em produção."
        )
    ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")


CSRF_TRUSTED_ORIGINS = env_list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
)


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.core",
    "apps.accounts",
    "apps.organizations",
    "apps.students",
    "apps.exercises",
    "apps.workouts",
    "apps.student_portal",
    "apps.security_center",
]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.security_center.middleware.SecurityHeadersMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.security_center.middleware.SensitiveRateLimitMiddleware",
    "apps.organizations.middleware.CurrentOrganizationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "config.urls"


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


POSTGRES_PASSWORD = os.getenv(
    "POSTGRES_PASSWORD",
    "saas_personal" if DEBUG else "",
)

if not DEBUG and (
    not POSTGRES_PASSWORD
    or POSTGRES_PASSWORD in {
        "123",
        "password",
        "saas_personal",
        "troque-esta-senha",
    }
):
    raise ImproperlyConfigured(
        "POSTGRES_PASSWORD ausente ou insegura em produção."
    )


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "saas_personal"),
        "USER": os.getenv("POSTGRES_USER", "saas_personal"),
        "PASSWORD": POSTGRES_PASSWORD,
        "HOST": os.getenv("POSTGRES_HOST", "db"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "connect_timeout": 5,
        },
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME":
        "django.contrib.auth.password_validation."
        "UserAttributeSimilarityValidator"
    },
    {
        "NAME":
        "django.contrib.auth.password_validation."
        "MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {
        "NAME":
        "django.contrib.auth.password_validation."
        "CommonPasswordValidator"
    },
    {
        "NAME":
        "django.contrib.auth.password_validation."
        "NumericPasswordValidator"
    },
]


LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Bahia"
USE_I18N = True
USE_TZ = True


STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {
        "BACKEND":
        "django.core.files.storage.FileSystemStorage"
    },
    "staticfiles": {
        "BACKEND":
        "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}


MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"


SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"

SESSION_COOKIE_AGE = int(
    os.getenv("DJANGO_SESSION_COOKIE_AGE", "43200")
)
SESSION_SAVE_EVERY_REQUEST = True

DATA_UPLOAD_MAX_MEMORY_SIZE = int(
    os.getenv("DJANGO_MAX_REQUEST_BYTES", "2097152")
)
FILE_UPLOAD_MAX_MEMORY_SIZE = int(
    os.getenv("DJANGO_MAX_FILE_BYTES", "1048576")
)
DATA_UPLOAD_MAX_NUMBER_FIELDS = 200

SECURITY_TRUST_X_FORWARDED_FOR = env_bool(
    "SECURITY_TRUST_X_FORWARDED_FOR",
    False,
)


if not DEBUG:
    SECURE_PROXY_SSL_HEADER = (
        "HTTP_X_FORWARDED_PROTO",
        "https",
    )
    SECURE_SSL_REDIRECT = env_bool(
        "DJANGO_SECURE_SSL_REDIRECT",
        True,
    )
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    SECURE_HSTS_SECONDS = int(
        os.getenv(
            "DJANGO_HSTS_SECONDS",
            "31536000",
        )
    )
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
        "DJANGO_HSTS_INCLUDE_SUBDOMAINS",
        True,
    )
    SECURE_HSTS_PRELOAD = False
else:
    SECURE_SSL_REDIRECT = False


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format":
            "%(asctime)s %(levelname)s %(name)s %(message)s"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "loggers": {
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
