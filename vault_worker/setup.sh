#!/usr/bin/env bash
# MixMint vault — one-shot server setup (Ubuntu 22.04/24.04, x86 or ARM).
# Usage (on the server, inside the copied vault_worker folder):  bash setup.sh
set -euo pipefail
cd "$(dirname "$0")"

say() { printf '\n\033[1;32m==> %s\033[0m\n' "$*"; }
die() { printf '\n\033[1;31m✗ %s\033[0m\n' "$*"; exit 1; }

[ -f .env ] || die "No .env here. Copy vault_worker/.env from your PC (it's pre-filled) into this folder."
set -a; . ./.env; set +a
for k in TELEGRAM_API_ID TELEGRAM_API_HASH TELEGRAM_BOT_TOKEN VAULT_WORKER_SECRET R2_ENDPOINT R2_ACCESS_KEY_ID R2_SECRET_ACCESS_KEY VAULT_DOMAIN; do
  [ -n "${!k:-}" ] || die "$k is empty in .env — fill it and run again."
done

say "Checking DNS: $VAULT_DOMAIN should point at this server"
MYIP=$(curl -fsS4 https://api.ipify.org || true)
DNSIP=$(getent ahostsv4 "$VAULT_DOMAIN" | awk 'NR==1{print $1}' || true)
echo "this server: ${MYIP:-?}   $VAULT_DOMAIN → ${DNSIP:-not found}"
[ "$MYIP" = "$DNSIP" ] || echo "⚠ DNS doesn't point here yet (or is proxied). HTTPS will start working once it does."

if ! command -v docker >/dev/null; then
  say "Installing Docker"
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER" || true
fi
DOCKER="docker"; docker ps >/dev/null 2>&1 || DOCKER="sudo docker"

MEM_MB=$(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo)
if [ "$MEM_MB" -lt 2000 ] && ! swapon --show | grep -q .; then
  say "Small server (${MEM_MB} MB RAM): adding 2 GB swap"
  sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

say "Opening ports 80 and 443 in the server firewall"
if command -v iptables >/dev/null; then
  for p in 80 443; do
    sudo iptables -C INPUT -p tcp --dport $p -j ACCEPT 2>/dev/null || sudo iptables -I INPUT 5 -p tcp --dport $p -j ACCEPT
  done
  command -v netfilter-persistent >/dev/null && sudo netfilter-persistent save || true
fi
command -v ufw >/dev/null && sudo ufw status | grep -q active && sudo ufw allow 80,443/tcp || true
echo "(Also allow 80 and 443 in your cloud provider's firewall / security list.)"

if [ ! -f .logged-out ]; then
  say "Moving the bot from Telegram's cloud to this server (one time)"
  echo "After this, the bot only works through this server. It can't go back to the cloud for 10 minutes."
  read -r -p "Type YES to continue: " ok
  [ "$ok" = "YES" ] || die "Stopped. Nothing changed."
  curl -fsS "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/logOut" | grep -q '"ok":true' && touch .logged-out \
    || echo "(logOut said no — fine if it was already done)"; touch .logged-out
fi

say "Starting the vault (Bot API server + worker + HTTPS)"
$DOCKER compose up -d --build

say "Waiting for it to come up"
for i in $(seq 1 30); do
  if $DOCKER compose exec -T worker python -c "import urllib.request,os;urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8000/health',headers={'Authorization':'Bearer '+os.environ['VAULT_WORKER_SECRET']}))" >/dev/null 2>&1; then
    break
  fi
  sleep 4
done
$DOCKER compose exec -T worker python - <<'PY' || true
import json, os, urllib.request
r = urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8000/health", headers={"Authorization": "Bearer " + os.environ["VAULT_WORKER_SECRET"]}))
print("health:", json.load(r))
PY

cat <<MSG

──────────────────────────────────────────────────────────────
 Done. Now in Vercel → mixmint → Settings → Environment Variables add:

   VAULT_WORKER_URL     = https://$VAULT_DOMAIN
   VAULT_WORKER_SECRET  = (the VAULT_WORKER_SECRET line in your .env)
   TELEGRAM_API_BASE    = https://$VAULT_DOMAIN

 Redeploy, then Admin → Support → Reconnect, link both channels, Run vault now.
 Logs:  $DOCKER compose logs -f worker
──────────────────────────────────────────────────────────────
MSG
