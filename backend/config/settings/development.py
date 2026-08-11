import os

os.environ.setdefault("DJANGO_SECRET_KEY", "unsafe-development-key-change-me")

from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
