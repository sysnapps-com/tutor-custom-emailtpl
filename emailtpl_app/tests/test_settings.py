"""
Minimal Django settings so this app's test suite can run standalone
(`python -m django test emailtpl_app --settings=emailtpl_app.tests.test_settings`)
without a full edx-platform checkout. This is a development/CI convenience
only -- it is NOT the settings module Tutor patches into the LMS/CMS image.
"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = "test-only-not-for-production"
DEBUG = True
USE_TZ = True
USE_I18N = True

LANGUAGE_CODE = "en"
# Deliberately more than one language so the i18n-safety test proves
# templates render (structurally) even when a non-English language is
# activated, independent of whether a .mo catalog exists for it.
LANGUAGES = [("en", "English"), ("es", "Spanish"), ("fr", "French")]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "emailtpl_app",
]

DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": False,
        "OPTIONS": {"context_processors": []},
    }
]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CELERY_TASK_ALWAYS_EAGER = True
