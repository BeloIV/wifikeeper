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
