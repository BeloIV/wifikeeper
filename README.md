# WiFi Manager – Saleziánske oratórium

Admin panel pre správu WPA2 Enterprise WiFi siete (SSID: **Oratko**).

## Architektúra

```
┌──────────────┐     PEAP/MSCHAPv2     ┌─────────────────┐
│ iOS / Android│ ──────────────────── ▶ │ UniFi Access AP  │
└──────────────┘                        └────────┬────────┘
                                                 │ RADIUS (UDP 1812/1813)
                                        ┌────────▼────────┐
                                        │  FreeRADIUS 3.x  │
                                        └─────┬──────┬────┘
                                              │ LDAP  │ SQL
                                    ┌─────────▼──┐ ┌──▼──────────┐
                                    │  OpenLDAP   │ │  PostgreSQL  │
                                    │ (users/     │ │  (sessions,  │
                                    │  groups)    │ │   audit)     │
                                    └─────────────┘ └─────────────┘

┌─────────────────────────────────────────────────────────┐
│ Admin panel (Next.js + Django REST API)                  │
│  • Správa LDAP používateľov                             │
│  • Jednorazové / časové kľúče                          │
│  • Live pripojenia (RADIUS accounting)                  │
│  • História, audit log                                  │
└─────────────────────────────────────────────────────────┘
```

## Skupiny a VLAN

| LDAP skupina    | VLAN | SSID    |
|----------------|------|---------|
| sdb            | 10   | SDB (Personal) |
| animatori      | 20   | Oratko  |
| fma            | 20   | Oratko  |
| spolupracovnici| 30   | Oratko  |
| hostia         | 40   | Oratko  |
| docasny        | 40   | Oratko  |

## Lokálny vývoj

### Požiadavky
- Docker + Docker Compose v2
- `openssl` (pre generovanie self-signed certifikátu)
- `make` (voliteľné, pre skrátené príkazy)

### Prvý štart

```bash
# 1. Klonuj repozitár
git clone <repo> wifi-manager
cd wifi-manager

# 2. Skopíruj a vyplň .env
cp .env.example .env
# Vyplň aspoň: POSTGRES_PASSWORD, LDAP_ADMIN_PASSWORD, LDAP_CONFIG_PASSWORD,
#              LDAP_READONLY_PASSWORD, DJANGO_SECRET_KEY

# 3. Spusti (vygeneruje self-signed cert automaticky)
make dev
# alebo: bash scripts/gen-self-signed.sh && docker compose up --build

# 4. Vytvor Django migrácie a superadmina
make migrate
make superadmin

# 5. Otvor v prehliadači
#    https://localhost  (potvrď bezpečnostné varovanie – self-signed cert)
```

> **iOS/Android**: Self-signed cert spôsobí varovanie pri připojení na WiFi.
> Pre produkciu použiješ Let's Encrypt, kde toto varovanie nevznikne.

### Prihlasovacie údaje (dev)

| Služba       | URL / prístup               |
|--------------|-----------------------------|
| Admin panel  | https://localhost            |
| Django admin | https://localhost/admin/     |
| Login        | `admin` / `zmen_heslo`       |
| OpenLDAP     | ldap://localhost:389         |
| PostgreSQL   | localhost:5432               |

## Produkčný deployment (Ubuntu 22.04)

### Požiadavky
- Ubuntu 22.04 LTS
- Docker + Docker Compose v2
- Doménové meno (napr. `wifi.oratko.sk`) smerujúce na server
- Cloudflare API token (DNS-01 challenge)

### Kroky

```bash
# 1. Nainštaluj Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 2. Naklonuj projekt
git clone <repo> /opt/wifi-manager
cd /opt/wifi-manager

# 3. Vyplň .env pre produkciu
cp .env.example .env
# Dôležité: DOMAIN=wifi.oratko.sk, vypni DEBUG, nastav silné heslá

# 4. Vyplň Cloudflare API token
nano certbot/cloudflare.ini
chmod 600 certbot/cloudflare.ini

# 5. Získaj Let's Encrypt certifikát (DNS-01 cez Cloudflare)
make prod-cert
# alebo:
# docker compose -f docker-compose.prod.yml run --rm certbot

# 6. Spusti produkčné prostredie
make prod-up

# 7. Django migrácie
make prod-migrate

# 8. Vytvor superadmina
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser

# 9. Nastav automatické obnovovanie certifikátu
# Certbot beh cez cron alebo systemd timer
sudo crontab -e
# Pridaj: 0 3 * * * docker compose -f /opt/wifi-manager/docker-compose.prod.yml run --rm certbot

# 10. Nastav deploy hook (nakopírovanie certu do RADIUS + reload)
chmod +x scripts/deploy-cert-hook.sh
sudo ln -s /opt/wifi-manager/scripts/deploy-cert-hook.sh \
           /etc/letsencrypt/renewal-hooks/deploy/wifi-manager-radius.sh
```

## FreeRADIUS – konfigurácia UniFi

V UniFi Network Controller nastav:

**Settings → Profiles → RADIUS**

| Parameter      | Hodnota                          |
|---------------|----------------------------------|
| Auth Server IP | IP adresa Docker hostu           |
| Auth Port      | 1812                             |
| Auth Secret    | hodnota `RADIUS_SECRET` z `.env` |
| Acct Server IP | IP adresa Docker hostu           |
| Acct Port      | 1813                             |
| Acct Secret    | hodnota `RADIUS_SECRET` z `.env` |

**Settings → WiFi → Oratko**

| Parameter          | Hodnota                    |
|-------------------|----------------------------|
| Security           | WPA2 Enterprise            |
| RADIUS Profile     | (profil z kroku vyššie)    |
| VLAN               | *(nastavuje RADIUS dynamicky)* |

> **Dôležité**: Nastav v `radius/config/clients.conf` správnu IP adresu UniFi controllera
> a shared secret, ktorý súhlasí s UniFi konfigom.

## Správa kľúčov

### Jednorazový kľúč
- Vytvorí LDAP účet v skupine `docasny` (VLAN 40)
- Po 1 prihlásení Celery zmaže LDAP účet
- Zobraziť ako QR kód alebo poslať emailom

### Časový kľúč
- Platí N hodín od vytvorenia
- Celery kontroluje každých 5 minút a maže expirované účty
- 30 minút pred expirácou pošle email adminovi

## Štruktúra projektu

```
wifi-manager/
├── docker-compose.yml          # Dev (self-signed cert)
├── docker-compose.prod.yml     # Prod (Let's Encrypt)
├── .env.example                # Príklad premenných
├── Makefile                    # Skrátené príkazy
├── README.md
├── certs/                      # Auto-generované certifikáty (dev)
├── certbot/
│   └── cloudflare.ini          # Cloudflare DNS-01 credentials
├── ldap/
│   └── bootstrap/
│       └── init.ldif           # Inicializácia LDAP skupín
├── radius/
│   ├── Dockerfile
│   ├── docker-entrypoint.sh
│   └── config/                 # FreeRADIUS konfigurácia
│       ├── clients.conf        # UniFi klienti + shared secret
│       ├── mods-available/
│       │   ├── sql             # PostgreSQL accounting
│       │   ├── ldap            # LDAP autentifikácia
│       │   └── eap             # PEAP/MSCHAPv2
│       ├── sites-available/
│       │   ├── default
│       │   └── inner-tunnel
│       ├── policy.d/
│       │   └── vlan_policy     # VLAN priradenie podľa skupiny
│       └── mods-config/sql/postgresql/
│           └── queries.conf    # SQL dotazy pre accounting
├── backend/                    # Django 4.x + DRF
│   ├── apps/
│   │   ├── users/              # LDAP CRUD (ldap3)
│   │   ├── keys/               # Dočasné kľúče + Celery
│   │   ├── sessions/           # RADIUS accounting
│   │   ├── audit/              # Audit log
│   │   └── panel_users/        # Admin panel useri + JWT
│   └── config/                 # Django settings, urls, celery
├── frontend/                   # Next.js 14 + TailwindCSS
│   └── src/app/
│       ├── login/
│       └── (dashboard)/
│           ├── page.tsx        # Prehľad
│           ├── users/          # Správa používateľov
│           ├── keys/           # Dočasné kľúče
│           ├── live/           # Live pripojenia
│           ├── history/        # História
│           └── admins/         # Správa adminov + audit log
├── nginx/
│   ├── nginx.dev.conf
│   └── nginx.prod.conf
└── scripts/
    ├── gen-self-signed.sh      # Generovanie dev certifikátu
    └── deploy-cert-hook.sh     # Let's Encrypt deploy hook
```

## Troubleshooting

**RADIUS neautentifikuje:**
```bash
# Testovanie z Docker hostu
docker compose exec freeradius radtest testuser testpassword localhost 1812 testing123
```

**LDAP pripojenie:**
```bash
docker compose exec openldap ldapsearch -x -H ldap://localhost \
  -D "cn=admin,dc=oratko,dc=local" -w "$LDAP_ADMIN_PASSWORD" \
  -b "ou=users,dc=oratko,dc=local"
```

**Celery tasky:**
```bash
docker compose logs celery
docker compose exec backend celery -A config inspect active
```

**Certifikát (prod):**
```bash
openssl x509 -in /etc/letsencrypt/live/wifi.oratko.sk/cert.pem -noout -dates
```
