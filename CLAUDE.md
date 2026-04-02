# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WiFi Manager for Salesian oratory — admin panel for managing WPA2 Enterprise WiFi (SSID: Oratko). Authentication flow: iOS/Android → UniFi AP → FreeRADIUS (PEAP/MSCHAPv2) → OpenLDAP (user auth) + PostgreSQL (VLAN via `radreply`).

## Commands

### Development

```bash
make dev              # generate self-signed cert + docker compose up --build
make dev-detach       # same but detached
make migrate          # run Django migrations in backend container
make superadmin       # create default admin (admin / zmen_heslo)
make logs             # follow all logs
make logs-radius      # follow FreeRADIUS logs
make logs-backend     # follow Django logs
make clean            # docker compose down -v
```

### Backend Tests (inside container or with pytest-django)

```bash
docker compose exec backend pytest                        # all tests
docker compose exec backend pytest tests/test_key_api.py  # single file
docker compose exec backend pytest -k test_create_key     # single test
```

Tests live in `backend/tests/`. `pytest.ini` sets `DJANGO_SETTINGS_MODULE = config.settings`.

### Frontend Tests

```bash
cd frontend
npm run test          # vitest run (once)
npm run test:watch    # vitest watch
npm run lint          # eslint
npm run build         # next build
```

### RADIUS Debugging

```bash
docker compose exec freeradius radtest USER PASS localhost 1812 testing123
docker compose exec openldap ldapsearch -x -H ldap://localhost \
  -D "cn=admin,dc=oratko,dc=local" -w "$LDAP_ADMIN_PASSWORD" \
  -b "ou=users,dc=oratko,dc=local"
docker compose exec backend celery -A config inspect active
```

### Production

```bash
make prod-cert        # obtain Let's Encrypt cert via Cloudflare DNS-01
make prod-up          # docker compose -f docker-compose.prod.yml up -d
make prod-migrate     # run migrations in prod backend
```

## Architecture

### Services (docker-compose.yml)

| Service | Role |
|---------|------|
| `postgres` | Django models + FreeRADIUS `radreply`/accounting |
| `redis` | Celery broker + result backend |
| `openldap` | WiFi users (`ou=users`) and groups (`ou=groups`) |
| `freeradius` | RADIUS auth/accounting; config mounted as volume |
| `backend` | Django 4.2 + DRF; runs `runserver` in dev, `gunicorn` in prod |
| `celery` | Async tasks (key creation, email) |
| `celery-beat` | Scheduled tasks (expire temp keys every 5 min) |
| `frontend` | Next.js 14 dev server on port 3006 |
| `nginx` | Reverse proxy; terminates TLS; routes `/api/` → backend, rest → frontend |
| `unifi` + `unifi-db` | UniFi controller with MongoDB (optional) |

### Backend Django Apps (`backend/apps/`)

- **`panel_users`** — `AdminUser` (extends `AbstractUser`) with roles `superadmin/admin/readonly`. `AdminInvitation` for token-based onboarding. Custom `JWTCookieAuthentication` reads JWT from HttpOnly cookie `access_token` instead of `Authorization` header.
- **`users`** — LDAP CRUD via `ldap3` (`ldap_service.py`). Also holds `LDAPGroup` model which drives group/VLAN config. **Does not touch Django auth** — that's handled by `django-auth-ldap` for admin logins only.
- **`keys`** — `TempKey` model: one-time, timed, or multi-use keys. Passwords stored encrypted (Fernet, key = `FIELD_ENCRYPTION_KEY`). Celery tasks handle expiry and LDAP cleanup.
- **`sessions`** — RADIUS accounting data (live connections, history).
- **`audit`** — Audit log + `AuditMiddleware` that records all API actions.

### VLAN Assignment Flow

1. FreeRADIUS authenticates user via LDAP module (PEAP/MSCHAPv2).
2. SQL module (`authorize_reply_query`) looks up `radreply` table by `username`.
3. `radreply` entries (`Tunnel-Type`, `Tunnel-Medium-Type`, `Tunnel-Private-Group-Id`) were written by Django when user was created/assigned to a group.
4. `vlan_policy` in `radius/config/policy.d/` is static — VLAN comes entirely from `radreply` DB lookup.

If `radreply` is missing entries after a restart, run `sync_radreply.py` to bulk-sync.

### FreeRADIUS Configuration

Config files are bind-mounted: `./radius/config → /etc/freeradius/3.0`. The entrypoint (`docker-entrypoint.sh`) runs `envsubst` on `*.template` files to inject env vars (`FR_POSTGRES_HOST`, `FR_LDAP_HOST`, `RADIUS_SECRET`, etc.) and copies/symlinks modules and sites.

### Frontend (`frontend/src/app/`)

Next.js 14 App Router. Routes:
- `/login` — unauthenticated login page
- `/dashboard` — main layout with nested routes: `users/`, `keys/`, `live/`, `history/`, `admins/`
- `/invite` — admin invitation acceptance

Uses SWR for data fetching, Radix UI primitives, TailwindCSS. API calls go to `/api/` (no `NEXT_PUBLIC_API_URL` in dev — nginx handles routing).

### Authentication

- Admin panel login: POST `/api/auth/login/` → sets `access_token` + `refresh_token` HttpOnly cookies.
- All API calls are cookie-authenticated (no `Authorization` header needed from frontend).
- `LoginSerializer` accepts `email` in the `username` field.

### Key Environment Variables

| Variable | Purpose |
|----------|---------|
| `DJANGO_SECRET_KEY` | Django secret |
| `FIELD_ENCRYPTION_KEY` | Fernet key for `TempKey.ldap_password` |
| `RADIUS_COA_SECRET` | RADIUS CoA shared secret |
| `LDAP_ADMIN_PASSWORD` / `LDAP_READONLY_PASSWORD` | OpenLDAP credentials |
| `RADIUS_SECRET` | FreeRADIUS ↔ UniFi shared secret |
| `BREVO_SMTP_USER` / `BREVO_SMTP_KEY` | Email via Brevo SMTP relay |

Generate `FIELD_ENCRYPTION_KEY` with:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### LDAP Groups → VLANs

| Group | VLAN |
|-------|------|
| sdb | 10 |
| animatori, fma | 20 |
| spolupracovnici | 30 |
| hostia, docasny | 40 |

Groups are managed via `LDAPGroup` model in Django admin. The `ldap_service.py` falls back to hardcoded lists if the DB query fails.
