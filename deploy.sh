#!/bin/bash
set -e  # Stop on any error

echo "──────────────────────────────────"
echo "  Tech Community Bot — VPS Setup  "
echo "──────────────────────────────────"

# ── 1. System packages ─────────────────────────────────────────────────────────
echo "[1/5] Installing system packages..."
sudo apt update -y && sudo apt install -y python3 python3-pip nodejs npm

# ── 2. PM2 ─────────────────────────────────────────────────────────────────────
echo "[2/5] Installing PM2..."
if ! command -v pm2 &>/dev/null; then
  sudo npm install -g pm2
else
  echo "  PM2 already installed, skipping."
fi

# ── 3. Python dependencies ─────────────────────────────────────────────────────
echo "[3/5] Installing Python dependencies..."
pip3 install -r backend/requirements.txt
pip3 install -r bot/requirements.txt

# ── 4. Environment file ────────────────────────────────────────────────────────
echo "[4/5] Setting up .env files..."
if [ ! -f .env ]; then
  echo "  ERROR: .env file not found!"
  echo "  Run:  cp .env.example .env  then fill in your values."
  exit 1
fi
# Both backend and bot need access to the same .env
cp .env backend/.env
cp .env bot/.env
echo "  .env copied to backend/ and bot/"

# ── 5. Start with PM2 ──────────────────────────────────────────────────────────
echo "[5/5] Starting processes with PM2..."
pm2 start ecosystem.config.js
pm2 save
pm2 startup | tail -1 | bash  # Auto-run PM2 on VPS reboot

echo ""
echo "✅ Done! Both workers are running."
echo ""
echo "Useful PM2 commands:"
echo "  pm2 status          → see if backend and bot are running"
echo "  pm2 logs backend    → backend logs"
echo "  pm2 logs bot        → bot logs"
echo "  pm2 restart all     → restart both after code changes"
echo "  pm2 stop all        → stop everything"
