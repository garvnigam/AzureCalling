#!/bin/bash
set -e
cd /home/site/wwwroot
echo "== Python: $(python --version) =="
echo "== Installing requirements =="
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo "== Starting gunicorn on port ${PORT:-8000} =="
exec python -m gunicorn -w 1 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:${PORT:-8000} --timeout 120
