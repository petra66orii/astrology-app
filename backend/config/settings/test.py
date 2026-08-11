import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-secret-key")

from .base import *  # noqa: F403

if env_bool("USE_SQLITE_FOR_TESTS"):  # noqa: F405
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
