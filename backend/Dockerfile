FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    libsasl2-dev \
    libldap2-dev \
    libssl-dev \
    freeradius-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

# ── Dev stage ─────────────────────────────────────────────────────────────────
FROM base AS dev
# Zdrojový kód je mountovaný ako volume
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ── Prod stage ────────────────────────────────────────────────────────────────
FROM base AS prod
COPY . .
RUN pip install gunicorn
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
