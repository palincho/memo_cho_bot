#!/usr/bin/env bash
set -euo pipefail

# Run once on a fresh GCE e2-micro Ubuntu 22.04 instance.

APP_DIR=/opt/memo_cho_bot
REPO_URL=${REPO_URL:-"https://github.com/palincho/memo_cho_bot.git"}

echo "==> Updating system packages"
sudo apt-get update -y
sudo apt-get install -y python3.11 python3.11-venv python3-pip git

echo "==> Cloning repository"
sudo git clone "$REPO_URL" "$APP_DIR"
sudo chown -R "$USER":"$USER" "$APP_DIR"

echo "==> Installing Python dependencies"
cd "$APP_DIR"
python3.11 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

echo "==> Copying .env (edit before running)"
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    echo "  -> Edit $APP_DIR/.env with your credentials before starting the service."
fi

echo "==> Installing systemd service"
sudo cp "$APP_DIR/deploy/drift.service" /etc/systemd/system/drift.service
sudo systemctl daemon-reload
sudo systemctl enable drift

echo ""
echo "Setup complete. Edit $APP_DIR/.env, then run:"
echo "  sudo systemctl start drift"
echo "  sudo journalctl -fu drift"
