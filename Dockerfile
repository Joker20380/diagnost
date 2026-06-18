FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    default-libmysqlclient-dev \
    libpq-dev \
    libwebp-dev \
    gettext \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt

RUN pip install --upgrade pip setuptools wheel \
    && pip install -r /app/requirements.txt \
    && pip install gunicorn psycopg2-binary

# Patch django-webp 3.0.0 absolute imports and missing compatibility constants.
RUN python - <<'PY'
from pathlib import Path
import django_webp

pkg = Path(django_webp.__file__).resolve().parent

# Fix absolute imports: "utils" -> "django_webp.utils"
for path in pkg.rglob("*.py"):
    text = path.read_text()
    old = text

    text = text.replace("from utils import", "from django_webp.utils import")
    text = text.replace("import utils", "import django_webp.utils as utils")

    if text != old:
        path.write_text(text)
        print("patched imports:", path)

# Add compatibility fallbacks to utils.py
utils_path = pkg / "utils.py"
text = utils_path.read_text()

compat = """
# ---- Docker compatibility patch for django-webp 3.0.0 ----
from django.conf import settings as _django_webp_settings

try:
    WEBP_STATIC_ROOT
except NameError:
    WEBP_STATIC_ROOT = getattr(_django_webp_settings, "WEBP_STATIC_ROOT", getattr(_django_webp_settings, "STATIC_ROOT", ""))

try:
    WEBP_STATIC_URL
except NameError:
    WEBP_STATIC_URL = getattr(_django_webp_settings, "WEBP_STATIC_URL", getattr(_django_webp_settings, "STATIC_URL", ""))

try:
    WEBP_MEDIA_ROOT
except NameError:
    WEBP_MEDIA_ROOT = getattr(_django_webp_settings, "WEBP_MEDIA_ROOT", getattr(_django_webp_settings, "MEDIA_ROOT", ""))

try:
    WEBP_MEDIA_URL
except NameError:
    WEBP_MEDIA_URL = getattr(_django_webp_settings, "WEBP_MEDIA_URL", getattr(_django_webp_settings, "MEDIA_URL", ""))

try:
    USING_WHITENOISE
except NameError:
    USING_WHITENOISE = False
# ---- End docker compatibility patch ----
"""

if "Docker compatibility patch for django-webp 3.0.0" not in text:
    utils_path.write_text(text.rstrip() + "\n\n" + compat)
    print("patched utils:", utils_path)
PY

COPY . /app

WORKDIR /app/diagnost

EXPOSE 8000
