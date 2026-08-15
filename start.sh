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

PHONE_NUMBER=""
for arg in "$@"; do
    case "$arg" in
        --call=*) PHONE_NUMBER="${arg#--call=}" ;;
    esac
done

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
pkill -f "ngrok http" 2>/dev/null || true
sleep 1

# ── Start ngrok tunnel ─────────────────────────────────────────────────────
echo "▶  Starting ngrok tunnel..."
ngrok http 8000 --log=stdout > "$LOG_DIR/ngrok.log" 2>&1 &
TUNNEL_PID=$!

echo "   Waiting for public URL..."
PUBLIC_URL=""
for i in $(seq 1 30); do
    PUBLIC_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | python3 -c "import sys,json; t=json.load(sys.stdin).get('tunnels',[]); print(t[0]['public_url'] if t else '')" 2>/dev/null)
    if [ -n "$PUBLIC_URL" ]; then
        break
    fi
    sleep 1
done

if [ -z "$PUBLIC_URL" ]; then
    echo "ERROR: Could not get ngrok URL. Check $LOG_DIR/ngrok.log"
    kill $TUNNEL_PID 2>/dev/null
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
    kill $UVICORN_PID $TUNNEL_PID 2>/dev/null
    exit 1
fi
echo "   Server ready ✓"

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

# ── Place outbound call if --call flag was provided ────────────────────────
if [ -n "$PHONE_NUMBER" ]; then
    echo ""
    echo "▶  Placing outbound call to $PHONE_NUMBER..."
    python telephony.py "$PHONE_NUMBER"
    echo ""
fi

echo "   Press Ctrl+C to stop everything."
echo ""

# ── Cleanup on Ctrl+C ──────────────────────────────────────────────────────
cleanup() {
    echo ""
    echo "▶  Shutting down..."
    kill $UVICORN_PID $TUNNEL_PID 2>/dev/null
    wait $UVICORN_PID $TUNNEL_PID 2>/dev/null
    echo "   Done."
    exit 0
}
trap cleanup INT TERM

tail -f "$LOG_DIR/server.log"
