#!/usr/bin/env bash
set -Eeuo pipefail
HOST="${SCDS_VPS_HOST:-catalystadmin@94.72.113.77}"
KEY="${SCDS_SSH_KEY:-$HOME/.ssh/id_ed25519}"
DOWNLOADS="$HOME/Downloads"
BACKEND="$DOWNLOADS/sustainable-catalyst-decision-studio-backend-v2.3.1.zip"
UPGRADER="$DOWNLOADS/upgrade_decision_studio_backend_v2_3_1_contabo.sh"
[[ -f "$BACKEND" ]] || { echo "Missing $BACKEND" >&2; exit 1; }
[[ -f "$UPGRADER" ]] || { echo "Missing $UPGRADER" >&2; exit 1; }
echo "=== PRE-FLIGHT VPS STATE ==="
ssh -i "$KEY" -o IdentitiesOnly=yes "$HOST" 'docker ps --filter name=sc-decision-studio --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"; curl -fsS http://127.0.0.1:8089/health | python3 -m json.tool || true'
echo "=== UPLOAD v2.3.1 ==="
scp -i "$KEY" -o IdentitiesOnly=yes "$BACKEND" "$UPGRADER" "$HOST:/tmp/"
echo "=== GUARDED VPS UPGRADE ==="
ssh -i "$KEY" -o IdentitiesOnly=yes "$HOST" 'chmod +x /tmp/upgrade_decision_studio_backend_v2_3_1_contabo.sh && /tmp/upgrade_decision_studio_backend_v2_3_1_contabo.sh /tmp/sustainable-catalyst-decision-studio-backend-v2.3.1.zip'
echo "=== PUBLIC VERIFY ==="
curl -fsS https://decision-studio-api.sustainablecatalyst.com/health | python3 -m json.tool
