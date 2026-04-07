#!/bin/bash
set -euo pipefail

SUBNET="192.168.1.0/24"

echo "=== Tailscale subnet router setup ==="

# 1. Install Tailscale
if ! command -v tailscale &>/dev/null; then
    echo "[1/4] Installing Tailscale..."
    curl -fsSL https://tailscale.com/install.sh | sh
else
    echo "[1/4] Tailscale already installed, skipping."
fi

# 2. Enable IP forwarding (persistent)
echo "[2/4] Enabling IP forwarding..."
grep -qxF 'net.ipv4.ip_forward=1' /etc/sysctl.conf \
    || echo 'net.ipv4.ip_forward=1' | sudo tee -a /etc/sysctl.conf
grep -qxF 'net.ipv6.conf.all.forwarding=1' /etc/sysctl.conf \
    || echo 'net.ipv6.conf.all.forwarding=1' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p /etc/sysctl.conf

# 3. Optimize UDP GRO forwarding (reduces warning, improves UDP throughput)
echo "[3/4] Configuring UDP GRO forwarding on enp1s0..."
if command -v ethtool &>/dev/null; then
    sudo ethtool -K enp1s0 rx-udp-gro-forwarding on rx-gro-list off 2>/dev/null || true
    # Make persistent via networkd-dispatcher or udev
    HOOK_DIR="/etc/networkd-dispatcher/routable.d"
    if [ -d "$HOOK_DIR" ]; then
        sudo tee "$HOOK_DIR/50-tailscale-udp-gro" > /dev/null <<'EOF'
#!/bin/sh
ethtool -K enp1s0 rx-udp-gro-forwarding on rx-gro-list off
EOF
        sudo chmod +x "$HOOK_DIR/50-tailscale-udp-gro"
        echo "    Persistent hook written to $HOOK_DIR/50-tailscale-udp-gro"
    else
        echo "    Warning: $HOOK_DIR not found, GRO setting is not persistent across reboots."
    fi
else
    echo "    ethtool not installed, skipping GRO optimization."
fi

# 4. Start Tailscale and advertise subnet
echo "[4/4] Starting Tailscale (subnet: $SUBNET)..."
sudo tailscale up --advertise-routes="$SUBNET" --advertise-exit-node --accept-dns=false --ssh

echo ""
echo "Done. Teraz v Tailscale admin konzole (https://login.tailscale.com/admin/machines)"
echo "      schval subnet route pre tento node:"
echo "      Machines → tento PC → Edit route settings → povolit $SUBNET"
