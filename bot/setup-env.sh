#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "Telegram bot setup"
echo
read -r -p "BOT_TOKEN from BotFather: " BOT_TOKEN
read -r -p "ADMIN_IDS, only digits, comma-separated if many: " ADMIN_IDS

if [[ ! "$BOT_TOKEN" =~ ^[0-9]+:[A-Za-z0-9_-]{20,}$ ]]; then
  echo "BOT_TOKEN format looks wrong."
  exit 1
fi

if [[ ! "$ADMIN_IDS" =~ ^[0-9]+(,[0-9]+)*$ ]]; then
  echo "ADMIN_IDS must contain only digits, for example: 123456789"
  exit 1
fi

cat > .env <<EOF
BOT_TOKEN=$BOT_TOKEN
ADMIN_IDS=$ADMIN_IDS
DATA_DIR=/app/data
EOF

chmod 600 .env
docker compose down
docker compose up -d --build
docker compose ps
echo
echo "Done. Open Telegram and send /start to your bot."
