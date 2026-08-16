# TODO – wifi-manager

## Bezpečnosť

- [ ] **RADIUS porty obmedziť na IP UniFi controllera**
  - Momentálne: ak sa pri `setup.sh` nechá UniFi IP prázdna, porty 1812/1813 (UDP) sú otvorené pre všetkých
  - Fix: znova spustiť `bash setup/02-firewall.sh` po zistení IP controllera
  - Premenná: `CFG_UNIFI_IP` v `setup.sh`
  - *Neoverené – nemám prístup k `ufw status` na serveri (chýba sudo), skontroluj ručne*

## Emaily

- [ ] **Profilová fotka odosielateľa (Gravatar)** – aby sa pri emailoch z `no-reply@salezianipresov.xyz` zobrazovalo WiFi Manager logo namiesto prázdneho avatara v Gmail/Outlook/Apple Mail
  - Zaregistrovať účet na gravatar.com pre `no-reply@salezianipresov.xyz`
  - Nahrať logo (`backend/assets/email-logo.png` alebo `frontend/src/assets/logo-source.jpg`)
  - Zadarmo, funguje v Outlooku/Apple Mail; v Gmaile nie je garantované (na spoľahlivé zobrazenie v Gmaile s modrou fajočkou by bol potrebný platený BIMI certifikát)

## Testovanie

- [ ] **Backend testy** – existujú (`backend/tests/`), ale **24 z 40 padá** (`docker compose exec backend pip install -r requirements-dev.txt && python -m pytest`)
- [ ] **Frontend testy** – existujú (`frontend/src/test/`), 2 z 19 padajú (`api.test.ts` očakáva starý `Authorization` header namiesto aktuálnej cookie-based JWT autentifikácie – test treba prepísať)

## DNS – Cloudflare (salezianipresov.xyz)

### Mail server – plán zo Stalwart bol opustený
- Stalwart nie je nikde nasadený (žiadny kontajner, žiadne súbory na serveri)
- Namiesto toho beží **Cloudflare Email Routing** (`MX` → `route1-3.mx.cloudflare.net`), reálne funkčné
- `A mail.salezianipresov.xyz` (šedý mrak, správne) aj `TXT stalwart._domainkey` v DNS ešte existujú ako pozostatok pôvodného plánu – zváž, či ich zmazať, alebo Stalwart naozaj nasadiť
- **SPF nezahŕňa Brevo**: aktuálne `v=spf1 include:_spf.mx.cloudflare.net ~all`, pôvodný plán chcel aj `include:spf.brevo.com` – keďže appka reálne posiela cez Brevo SMTP, toto je medzera v anti-spam ochrane (DKIM pre Brevo je nastavené OK cez `brevo1/2._domainkey`, len SPF chýba)
  - Fix: `v=spf1 include:_spf.mx.cloudflare.net include:spf.brevo.com ~all`

---

**Hotovo (overené priamo v kóde/Cloudflare API, odstránené z listu):**
JWT token refresh v `api.ts`, duplikované Next.js stránky, `.env` vyplnený a stack beží, SMTP/Celery emaily reálne fungujú (otestované), DNS A/MX/DKIM/DMARC pre web+Brevo, Cloudflare API token pre Certbot, `radius.salezianipresov.xyz` A záznam.
