#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="/tmp/calling-agent-logs"
mkdir -p "$LOG_DIR"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   AI Calling Agent — Shyam Dhar      ║"
echo "║   Elite Realty, Greater Noida        ║"
echo "╚══════════════════════════════════════╝"
echo ""

cd "$SCRIPT_DIR"

# ── Activate venv ──────────────────────────────────────────────────────────
if [ ! -d "venv" ]; then
    echo "ERROR: venv not found."
    exit 1
fi
source venv/bin/activate

# ── Kill existing server ───────────────────────────────────────────────────
echo "▶  Clearing port 8000..."
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
sleep 1

# ── Start cloudflared FIRST so we get the URL before booting the server ───
echo "▶  Starting cloudflared tunnel..."
cloudflared tunnel --url http://localhost:8000 --protocol http2 > "$LOG_DIR/cloudflared.log" 2>&1 &
CF_PID=$!

echo "   Waiting for public URL..."
PUBLIC_URL=""
for i in $(seq 1 40); do
    PUBLIC_URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$LOG_DIR/cloudflared.log" 2>/dev/null | head -1)
    if [ -n "$PUBLIC_URL" ]; then
        break
    fi
    sleep 1
done

if [ -z "$PUBLIC_URL" ]; then
    echo "ERROR: Could not get cloudflared URL."
    kill $CF_PID 2>/dev/null
    exit 1
fi

echo "   Tunnel URL: $PUBLIC_URL ✓"

# ── Write PUBLIC_URL into .env so uvicorn boots with the correct value ─────
if grep -q "^PUBLIC_URL=" .env 2>/dev/null; then
    # Replace existing line
    sed -i '' "s|^PUBLIC_URL=.*|PUBLIC_URL=$PUBLIC_URL|" .env
else
    # Add new line
    echo "PUBLIC_URL=$PUBLIC_URL" >> .env
fi
echo "   .env updated with PUBLIC_URL ✓"

# ── Start FastAPI server (now with correct PUBLIC_URL in .env) ─────────────
echo "▶  Starting FastAPI server..."
uvicorn main:app --reload --port 8000 > "$LOG_DIR/server.log" 2>&1 &
UVICORN_PID=$!

echo "   Waiting for server to be ready..."
READY=0
for i in $(seq 1 20); do
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        READY=1
        break
    fi
    sleep 1
done

if [ $READY -eq 0 ]; then
    echo "ERROR: Server did not start. Logs:"
    cat "$LOG_DIR/server.log"
    kill $UVICORN_PID $CF_PID 2>/dev/null
    exit 1
fi
echo "   Server ready ✓"

# ── Wait for DNS to resolve before opening browser ─────────────────────────
DOMAIN=$(echo "$PUBLIC_URL" | sed 's|https://||')
echo "▶  Waiting for DNS ($DOMAIN)..."
for i in $(seq 1 30); do
    if host "$DOMAIN" > /dev/null 2>&1; then
        echo "   DNS resolved ✓"
        break
    fi
    sleep 2
done

DASHBOARD_URL="$PUBLIC_URL/dashboard"

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  ✅  ALL SYSTEMS RUNNING                                         ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
printf  "║  Local   :  http://localhost:8000                               ║\n"
printf  "║  Public  :  %-51s║\n" "$PUBLIC_URL"
printf  "║  Dashboard: %-51s║\n" "$DASHBOARD_URL"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "   Opening dashboard..."
open "$DASHBOARD_URL"
echo "   Press Ctrl+C to stop everything."
echo ""

# ── Cleanup on Ctrl+C ──────────────────────────────────────────────────────
cleanup() {
    echo ""
    echo "▶  Shutting down..."
    kill $UVICORN_PID $CF_PID 2>/dev/null
    wait $UVICORN_PID $CF_PID 2>/dev/null
    echo "   Done."
    exit 0
}
trap cleanup INT TERM

tail -f "$LOG_DIR/server.log"
