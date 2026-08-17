import logging
import os
from logging.handlers import RotatingFileHandler

_LOG_DIR = os.getenv("LOG_DIR", "/tmp/calling-agent-logs")
_FORMAT = "%(asctime)s [%(name)s] %(levelname)s %(message)s"


def setup_logging():
    os.makedirs(_LOG_DIR, exist_ok=True)
    root = logging.getLogger()
    if root.handlers:
        return
    root.setLevel(logging.INFO)
    formatter = logging.Formatter(_FORMAT)
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    file = RotatingFileHandler(
        os.path.join(_LOG_DIR, "app.log"), maxBytes=5_000_000, backupCount=3,
    )
    file.setFormatter(formatter)
    root.addHandler(console)
    root.addHandler(file)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(f"svc.{name}")