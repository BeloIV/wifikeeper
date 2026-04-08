.PHONY: dev prod cert migrate superadmin logs clean

# ── Lokálny vývoj ─────────────────────────────────────────────────────────────
dev: cert
	docker compose up --build

dev-detach: cert
	docker compose up --build -d

cert:
	@bash scripts/gen-self-signed.sh

# ── Migrácie a bootstrap ──────────────────────────────────────────────────────
migrate:
	docker compose exec backend python manage.py migrate

superadmin:
	docker compose exec backend python manage.py shell -c "\
from apps.panel_users.models import AdminUser; \
AdminUser.objects.create_superuser('admin', 'admin@oratko.sk', 'zmen_heslo', role='superadmin') \
if not AdminUser.objects.filter(username='admin').exists() \
else print('Admin already exists')"

# ── Logy ──────────────────────────────────────────────────────────────────────
logs:
	docker compose logs -f

logs-radius:
	docker compose logs -f freeradius

logs-backend:
	docker compose logs -f backend

# ── Produkcia ─────────────────────────────────────────────────────────────────
prod-up:
	docker compose -f docker-compose.prod.yml up -d

prod-cert:
	docker compose -f docker-compose.prod.yml run --rm certbot

prod-migrate:
	docker compose -f docker-compose.prod.yml exec backend python manage.py migrate

# ── Monitoring (Loki + Grafana) ───────────────────────────────────────────────
monitoring-up:
	docker compose -f docker-compose.monitoring.yml up -d

monitoring-down:
	docker compose -f docker-compose.monitoring.yml down

monitoring-logs:
	docker compose -f docker-compose.monitoring.yml logs -f

# ── Upratovanie ───────────────────────────────────────────────────────────────
clean:
	docker compose down -v

clean-certs:
	rm -rf certs/
