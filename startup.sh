#!/bin/bash
cd /home/site/wwwroot
pip install -r requirements.txt
python -m gunicorn -w 1 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000 --timeout 120
