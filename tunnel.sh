#!/usr/bin/env bash
# ============================================================
# Cloudflare Tunnel for AngKer Mini App
# Local app listens on: http://127.0.0.1:15541
# ============================================================
# HOW TO GET TOKEN:
#   1. Go to Cloudflare Zero Trust → Networks → Tunnels
#   2. Create / select tunnel → copy the token
#   3. Paste it below (or set env CLOUDFLARE_TUNNEL_TOKEN)
# ============================================================

set -e

# ---------- CLOUDFLARE TUNNEL TOKEN ----------
CLOUDFLARE_TUNNEL_TOKEN="${CLOUDFLARE_TUNNEL_TOKEN:-eyJhIjoiMjYxOGY4MzY3Y2M3M2ExYWMxZDZlNmY2ZGM5NWIyNWUiLCJ0IjoiYjA4YWM1OWYtYTQxNy00ODA1LWE2ODEtMzM1MjEzNDI1YmU2IiwicyI6Ik5UazVZalpoTTJJdE5EVmhZUzAwWlRoa0xUaG1OVGd0WVRNMU1HUXdNVEU1TmpjeiJ9}"
# ------------------------------------------------------------

ROOT="$(cd "$(dirname "$0")" && pwd)"
LOCAL_PORT=15541
LOCAL_URL="http://127.0.0.1:${LOCAL_PORT}"

# Find cloudflared binary
CF=""
if command -v cloudflared >/dev/null 2>&1; then
  CF="$(command -v cloudflared)"
elif [ -x "$ROOT/bin/cloudflared" ]; then
  CF="$ROOT/bin/cloudflared"
elif [ -x "/usr/local/bin/cloudflared" ]; then
  CF="/usr/local/bin/cloudflared"
fi

if [ -z "$CF" ]; then
  echo "[tunnel] ERROR: cloudflared binary not found"
  echo "[tunnel] Install: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/"
  exit 2
fi

if [ -z "$CLOUDFLARE_TUNNEL_TOKEN" ]; then
  echo "[tunnel] WARNING: CLOUDFLARE_TUNNEL_TOKEN is empty"
  echo "[tunnel] Domain will show Error 1033 (tunnel not connected)"
  echo "[tunnel] App still runs on ${LOCAL_URL}"
  echo "[tunnel] Edit this file or export CLOUDFLARE_TUNNEL_TOKEN=your_token"
  exit 2
fi

echo "[tunnel] Starting cloudflared → ${LOCAL_URL}"
echo "[tunnel] Using: $CF"
exec "$CF" tunnel --no-autoupdate run --token "$CLOUDFLARE_TUNNEL_TOKEN"
