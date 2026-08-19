#!/bin/bash
cd /home/site/wwwroot
exec python -m gunicorn -w 1 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000 --timeout 120 --access-logfile - --error-logfile -
