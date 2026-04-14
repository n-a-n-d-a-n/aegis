#!/usr/bin/env bash
# Aegis — Cloudflare Tunnel Setup Script
# Run this on your VPS after deploying the backend with Docker.
set -euo pipefail

DOMAIN="${1:-}"
TUNNEL_NAME="aegis-tunnel"

if [ -z "$DOMAIN" ]; then
  echo "Usage: bash scripts/setup.sh yourdomain.com"
  exit 1
fi

echo ""
echo "  Aegis — Cloudflare Tunnel Setup"
echo "  Domain: $DOMAIN"
echo ""

# ── Install cloudflared ───────────────────────────────────────────────────────
if ! command -v cloudflared &> /dev/null; then
  echo "  Installing cloudflared..."
  curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb \
    -o /tmp/cloudflared.deb
  sudo dpkg -i /tmp/cloudflared.deb
  rm /tmp/cloudflared.deb
  echo "  ✓ cloudflared installed"
else
  echo "  ✓ cloudflared already installed"
fi

# ── Authenticate ──────────────────────────────────────────────────────────────
echo ""
echo "  Opening Cloudflare authentication..."
echo "  (A browser link will appear — open it to authorize)"
echo ""
cloudflared tunnel login

# ── Create tunnel ─────────────────────────────────────────────────────────────
echo ""
echo "  Creating tunnel: $TUNNEL_NAME"
cloudflared tunnel create "$TUNNEL_NAME"

TUNNEL_ID=$(cloudflared tunnel list | grep "$TUNNEL_NAME" | awk '{print $1}')
echo "  Tunnel ID: $TUNNEL_ID"

# ── Write config ──────────────────────────────────────────────────────────────
CONFIG_DIR="$HOME/.cloudflared"
CONFIG_FILE="$CONFIG_DIR/config.yml"

cat > "$CONFIG_FILE" <<EOF
tunnel: $TUNNEL_ID
credentials-file: $CONFIG_DIR/$TUNNEL_ID.json

ingress:
  - hostname: submit.$DOMAIN
    service: http://localhost:8000
  - hostname: admin.$DOMAIN
    service: http://localhost:8000
  - service: http_status:404
EOF

echo "  ✓ Config written to $CONFIG_FILE"

# ── Route DNS ─────────────────────────────────────────────────────────────────
echo ""
echo "  Creating DNS routes..."
cloudflared tunnel route dns "$TUNNEL_NAME" "submit.$DOMAIN"
cloudflared tunnel route dns "$TUNNEL_NAME" "admin.$DOMAIN"
echo "  ✓ DNS routes created"

# ── Install as systemd service ────────────────────────────────────────────────
echo ""
echo "  Installing cloudflared as systemd service..."
sudo cloudflared service install
sudo systemctl enable cloudflared
sudo systemctl start cloudflared

echo ""
echo "  ✓ Tunnel running as a system service"

# ── Lock down firewall ────────────────────────────────────────────────────────
echo ""
echo "  Locking down firewall (removing all inbound rules)..."
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
# Note: SSH is intentionally NOT re-added here.
# Use Cloudflare Access SSH from this point forward.
sudo ufw enable

echo ""
echo "  ================================================================"
echo "  Setup complete!"
echo ""
echo "  Submission URL:  https://submit.$DOMAIN"
echo "  Admin URL:       https://admin.$DOMAIN  (protect with CF Access)"
echo ""
echo "  IMPORTANT: SSH is now only accessible via Cloudflare Access."
echo "  Set up Access SSH before closing this session."
echo "  ================================================================"
echo ""
