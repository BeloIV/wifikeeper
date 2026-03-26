# wifikeeper – Server Setup

Server pre WPA2 Enterprise WiFi správu Saleziánskeho oratória.

## Čo tento setup robí

| Skript | Čo robí |
|---|---|
| `setup.sh` | **Hlavný entry point** – checks + interaktívna konfigurácia |
| `01-base.sh` | Hostname, update, základné nástroje, statická IP |
| `02-firewall.sh` | UFW firewall – SSH, HTTP, HTTPS, RADIUS porty |
| `03-docker.sh` | Docker + Docker Compose |
| `04-certbot.sh` | Let's Encrypt certifikát cez Cloudflare DNS-01 |
| `05-ssh-hardening.sh` | Zakáže heslo, povolí len SSH kľúč |
| `06-tailscale.sh` | Tailscale VPN (auth key alebo manuálne prihlásenie) |

## Predpoklady

- Ubuntu 24.04 LTS (fresh install)
- Doména na Cloudflare (napr. `tvoja-domena.xyz`)
- Cloudflare API token (DNS edit permissions)
- SSH kľúč už skopírovaný na server (`ssh-copy-id`)
- Tailscale účet (voliteľné: auth key z admin konzoly)

## Inštalácia

### 1. Stiahni skripty na server

```bash
git clone https://github.com/tvoj-repo/wifikeeper-setup.git
cd wifikeeper-setup
chmod +x *.sh
```

### 2. Uprav premenné

Pred spustením uprav v skriptoch:

**`01-base.sh`:**
```bash
STATIC_IP="192.168.1.222"   # IP servera
GATEWAY="192.168.1.1"       # IP routera
INTERFACE="enp1s0"           # sieťový interface (over: ip a)
```

**`04-certbot.sh`:**
```bash
DOMAIN="radius.tvoja-domena.xyz"
EMAIL="tvoj@email.com"
CF_TOKEN="cloudflare-api-token"
```

### 3. Spusti setup

```bash
bash setup.sh
```

Skript sám zistí čo je nainštalované a spustí len čo chýba.
Jednotlivé skripty môžeš spustiť aj manuálne ak treba.

## Sieťová architektúra

```
Internet
    │
    ▼
Router (192.168.1.1)
    │
    ├── wifikeeper (192.168.1.222)  ← tento server
    │       ├── FreeRADIUS :1812/1813
    │       ├── Admin panel :443
    │       └── Docker containers
    │
    └── UniFi Controller
            └── AP-čka → RADIUS → wifikeeper
```

## SSID / VLAN schéma

| SSID | Typ | Skupiny | VLAN |
|---|---|---|---|
| **Oratko** | WPA2 Enterprise | animatori, fma, spolupracovnici | 20/30 |
| **Oratko** | WPA2 Enterprise | hostia, docasny | 40 |
| **SDB** | WPA2 Personal | saleziáni | – |
| **IoT** | WPA2 Personal | zariadenia | – |

## Po základnom sete

Nasadiť `wifi-manager` projekt:

```bash
git clone https://github.com/tvoj-repo/wifi-manager.git
cd wifi-manager
cp .env.example .env
# uprav .env
docker compose up -d
```

## Užitočné príkazy

```bash
# Status Docker kontajnerov
docker compose ps

# Logy
docker compose logs -f

# Reštart
docker compose restart

# Certifikát – manuálna obnova
sudo certbot renew

# Firewall status
sudo ufw status verbose

# Kto je pripojený na SSH
who
```

## Server info

| Položka | Hodnota |
|---|---|
| Hostname | `wifikeeper` |
| IP | `192.168.1.222` |
| OS | Ubuntu 24.04 LTS |
| User | `oratko` |
| SSH port | `22` |
