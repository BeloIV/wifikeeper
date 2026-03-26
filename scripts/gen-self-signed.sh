#!/bin/bash
# =============================================================================
# Generovanie self-signed certifikátu pre lokálny vývoj
# Spúšťa sa automaticky pri docker compose up cez hook, alebo manuálne.
# =============================================================================

set -e

CERT_DIR="$(dirname "$0")/../certs"
mkdir -p "$CERT_DIR"

if [ -f "$CERT_DIR/server.crt" ] && [ -f "$CERT_DIR/server.key" ]; then
    echo "Self-signed cert already exists in $CERT_DIR, skipping."
    exit 0
fi

echo "Generating self-signed certificate for local development..."

# CA kľúč a certifikát
openssl genrsa -out "$CERT_DIR/ca.key" 4096 2>/dev/null
openssl req -new -x509 -days 1826 -key "$CERT_DIR/ca.key" \
    -out "$CERT_DIR/ca.crt" \
    -subj "/C=SK/ST=Bratislava/L=Bratislava/O=Salezianske oratorium/CN=WiFi-Manager-Dev-CA" 2>/dev/null

# Server kľúč a CSR
openssl genrsa -out "$CERT_DIR/server.key" 2048 2>/dev/null
openssl req -new -key "$CERT_DIR/server.key" \
    -out "$CERT_DIR/server.csr" \
    -subj "/C=SK/ST=Bratislava/L=Bratislava/O=Salezianske oratorium/CN=localhost" 2>/dev/null

# Rozšírenia pre server cert (SAN)
cat > "$CERT_DIR/server.ext" << EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = *.localhost
IP.1 = 127.0.0.1
EOF

# Podpíš server cert CA-čkou
openssl x509 -req -days 825 \
    -in "$CERT_DIR/server.csr" \
    -CA "$CERT_DIR/ca.crt" \
    -CAkey "$CERT_DIR/ca.key" \
    -CAcreateserial \
    -out "$CERT_DIR/server.crt" \
    -extfile "$CERT_DIR/server.ext" 2>/dev/null

# DH parametre pre FreeRADIUS EAP
if [ ! -f "$CERT_DIR/dh" ]; then
    echo "Generating DH parameters (this may take a moment)..."
    openssl dhparam -out "$CERT_DIR/dh" 2048 2>/dev/null
fi

# Upratanie
rm -f "$CERT_DIR/server.csr" "$CERT_DIR/server.ext"

echo "Done! Certificates generated in $CERT_DIR"
echo "  CA:     $CERT_DIR/ca.crt"
echo "  Server: $CERT_DIR/server.crt"
echo "  Key:    $CERT_DIR/server.key"
echo ""
echo "Note: This is a self-signed cert for development only."
echo "iOS/Android will show a security warning – click 'Connect Anyway' or install ca.crt."
