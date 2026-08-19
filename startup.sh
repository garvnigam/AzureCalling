#!/bin/bash
# Locate the extracted app dir. Azure Oryx with WEBSITE_RUN_FROM_PACKAGE
# extracts the tarball to /tmp/<hash>/ at each restart, so /home/site/wwwroot
# only contains the tarball itself, not main.py. Detect either layout.
set -e

APP_DIR=""
for candidate in /tmp/*/main.py /home/site/wwwroot/main.py; do
  if [ -f "$candidate" ]; then
    APP_DIR="$(dirname "$candidate")"
    break
  fi
done

if [ -z "$APP_DIR" ]; then
  echo "ERROR: main.py not found in /tmp/*/ or /home/site/wwwroot" >&2
  exit 1
fi

echo "== APP_DIR: $APP_DIR =="
cd "$APP_DIR"

# Activate Oryx venv if present so pip-installed packages are on PYTHONPATH
if [ -f /tmp/*/antenv/bin/activate ]; then
  # shellcheck disable=SC1090
  source /tmp/*/antenv/bin/activate
fi

echo "== Starting gunicorn on port 8000 =="
exec python -m gunicorn -w 1 -k uvicorn.workers.UvicornWorker main:app \
  --bind 0.0.0.0:8000 --timeout 120 \
  --access-logfile - --error-logfile -
