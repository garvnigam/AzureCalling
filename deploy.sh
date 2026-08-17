#!/bin/bash
set -e

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   AI Calling Agent — Railway Deploy  ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── Check Railway CLI ────────────────────────────────────────────────────────
if ! command -v railway &> /dev/null; then
  echo "ERROR: Railway CLI not found. Run: npm install -g @railway/cli"
  exit 1
fi

# ── Check login ──────────────────────────────────────────────────────────────
echo "▸ Checking Railway auth..."
if ! railway whoami &> /dev/null; then
  echo "Not logged in. Opening login..."
  railway login
fi
echo "  ✓ Logged in as $(railway whoami)"

# ── Stage & commit any pending changes ──────────────────────────────────────
echo ""
echo "▸ Checking git status..."
if [[ -n $(git status --porcelain) ]]; then
  echo "  Uncommitted changes found — committing before deploy..."
  git add main.py dashboard.html database.py
  git commit -m "deploy: update phone number management and lead fields"
fi
echo "  ✓ Git is clean"

# ── Push to main ─────────────────────────────────────────────────────────────
echo ""
echo "▸ Pushing to GitHub (main)..."
git push origin main
echo "  ✓ Pushed to GitHub"

# ── Deploy to Railway ────────────────────────────────────────────────────────
echo ""
echo "▸ Deploying to Railway..."
railway up --detach
echo "  ✓ Deploy triggered"

# ── Print logs ───────────────────────────────────────────────────────────────
echo ""
echo "▸ Streaming deployment logs (Ctrl+C to stop watching)..."
echo ""
railway logs
