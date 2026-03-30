# TODO – wifi-manager

## Bezpečnosť

- [ ] **RADIUS porty obmedziť na IP UniFi controllera**
  - Momentálne: ak sa pri `setup.sh` nechá UniFi IP prázdna, porty 1812/1813 (UDP) sú otvorené pre všetkých
  - Fix: znova spustiť `bash setup/02-firewall.sh` po zistení IP controllera
  - Premenná: `CFG_UNIFI_IP` v `setup.sh`

## Infraštruktúra

- [ ] **Duplikované Next.js stránky** – existujú v `src/app/(dashboard)/` aj `src/app/dashboard/`
  - Jedno z nich zmazať, nechať len `(dashboard)` (route group)

## Backend

- [ ] **JWT token refresh** – `api.ts` nemá auto-refresh access tokenu
  - Momentálne: expirovaný token = redirect na `/login`
  - Fix: interceptor ktorý volá `/api/auth/token/refresh/` a retry pôvodného requestu

## Testovanie

- [ ] Backend testy (Django – pytest)
- [ ] Frontend testy (Jest / Playwright)

## Nasadenie

- [ ] Vyplniť `.env` podľa `.env.example` a spustiť `docker compose up -d`
- [ ] Overiť SMTP config pre Celery email tasky (expirácia kľúčov)

## DNS – Cloudflare (salezianipresov.xyz)

### Web app
- [ ] `A` – `salezianipresov.xyz` → IP servera
- [ ] `A` – `www.salezianipresov.xyz` → IP servera

### Mail server (Stalwart)
- [ ] `A` – `mail.salezianipresov.xyz` → IP servera (**Proxy vypnutý – šedý mrak!**)
- [ ] `MX` – `salezianipresov.xyz` → `mail.salezianipresov.xyz` (priorita 10)

### SPF / DKIM / DMARC (anti-spam)
- [ ] `TXT` – `salezianipresov.xyz` → `v=spf1 include:spf.brevo.com ~all`
- [ ] `TXT` – DKIM záznam – **po inštalácii:**
  1. `docker compose up -d`
  2. Otvor `http://<IP servera>:8080` → Directories → Domains → salezianipresov.xyz → DKIM
  3. Skopíruj vygenerovaný záznam (napr. `stalwart._domainkey.salezianipresov.xyz`) do Cloudflare
- [ ] `TXT` – `_dmarc.salezianipresov.xyz` → `v=DMARC1; p=none; rua=mailto:admin@salezianipresov.xyz`

### Let's Encrypt (Certbot cez Cloudflare DNS-01)
- [ ] API token pre Certbot: `dash.cloudflare.com` → My Profile → API Tokens
  - Permissions: `Zone:DNS:Edit`, `Zone:Zone:Read`
  - Uložiť do `.env` ako `CLOUDFLARE_API_TOKEN`

### RADIUS / UniFi
- [ ] `A` – `radius.salezianipresov.xyz` → IP servera (voliteľné – pre RADIUS cert)



## nastavenie ssh kluca na git 
## tailsacale expose 



 
zobrazenie pre telefon doladit 




