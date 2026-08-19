#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="/tmp/calling-agent-logs"
mkdir -p "$LOG_DIR"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   Realty Siksha — Gaurav Kumar Nigam     ║"
echo "║   Realty Siksha, Greater Noida           ║"
echo "╚══════════════════════════════════════════╝"
echo ""

PHONE_NUMBER=""
for arg in "$@"; do
    case "$arg" in
        --call=*) PHONE_NUMBER="${arg#--call=}" ;;
    esac
done

cd "$SCRIPT_DIR"

# ── Activate venv using Python 3.12 (create if missing) ───────────────────
PYTHON_BIN=$(which python3.13 2>/dev/null || which python3.12 2>/dev/null || echo "python3")
if [ ! -d "venv" ]; then
    echo "▶  venv not found — creating with $($PYTHON_BIN --version)..."
    "$PYTHON_BIN" -m venv venv
fi
source venv/bin/activate

echo "▶  Installing/verifying dependencies..."
pip install -q --prefer-binary -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: pip install failed. Trying without version pins..."
    pip install -q --prefer-binary fastapi uvicorn gunicorn twilio supabase python-dotenv python-multipart websockets pydantic aiohttp openai PyJWT numpy
fi
echo "   Dependencies ready ✓"

# ── Build frontend ────────────────────────────────────────────────────────
echo "▶  Building frontend..."
cd "$SCRIPT_DIR/frontend"
npm install --silent 2>&1 | tail -3
npm run build 2>&1 | tail -5
cd "$SCRIPT_DIR"
echo "   Frontend built ✓"

# ── Kill existing server ───────────────────────────────────────────────────
echo "▶  Clearing port 8000..."
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
pkill -f "ngrok http" 2>/dev/null || true
sleep 1

# ── Start ngrok tunnel ─────────────────────────────────────────────────────
echo "▶  Starting ngrok tunnel..."
NGROK_DOMAIN=$(grep "^NGROK_DOMAIN=" "$SCRIPT_DIR/.env" 2>/dev/null | cut -d= -f2)
if [ -n "$NGROK_DOMAIN" ]; then
    ngrok http --url="$NGROK_DOMAIN" 8000 --log=stdout > "$LOG_DIR/ngrok.log" 2>&1 &
else
    ngrok http 8000 --log=stdout > "$LOG_DIR/ngrok.log" 2>&1 &
fi
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
"$SCRIPT_DIR/venv/bin/uvicorn" main:app --port 8000 --log-level info 2>&1 | tee "$LOG_DIR/server.log" &
UVICORN_PID=$!

echo "   Waiting for server to be ready..."
READY=0
for i in $(seq 1 20); do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        READY=1
        break
    fi
    sleep 1
done

if [ $READY -eq 0 ]; then
    echo "ERROR: Server did not start in time. Check output above or $LOG_DIR/server.log"
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
echo "   Logs streaming below — watch for [STEP 1] through [STEP 12] when a call is made."
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

wait $UVICORN_PID
