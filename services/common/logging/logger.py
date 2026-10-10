"""
Structured logger for all product-verification services.

Strategy:
  1. Try to push to Loki (via HTTP) when LOKI_URL is set and reachable.
  2. Always write to a rotating local log file as the primary/fallback store.
  3. Always emit to stdout (captured by Docker / systemd).

Usage:
    from common.logging.logger import get_logger
    log = get_logger("product-service")
    log.info("product registered", extra={"product_id": "P10001", "action": "register"})
"""

import json
import logging
import os
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

import requests  # type: ignore


# ── Config from environment ────────────────────────────────────────────────────

LOKI_URL: str | None = os.getenv("LOKI_URL")          # e.g. http://loki:3100
LOG_LEVEL: str       = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR: str         = os.getenv("LOG_DIR", "/app/logs")
SERVICE_NAME: str    = os.getenv("SERVICE_NAME", "unknown-service")


# ── Loki HTTP handler ──────────────────────────────────────────────────────────

class LokiHandler(logging.Handler):
    """
    Push log entries to Loki via its HTTP API (/loki/api/v1/push).
    If unavailable, silently drops (local file handler always covers us).
    """

    def __init__(self, loki_url: str, service: str):
        super().__init__()
        self.push_url = f"{loki_url.rstrip('/')}/loki/api/v1/push"
        self.service  = service

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
            payload = {
                "streams": [
                    {
                        "stream": {
                            "service": self.service,
                            "level":   record.levelname.lower(),
                        },
                        "values": [
                            [str(int(time.time() * 1e9)), message],
                        ],
                    }
                ]
            }
            requests.post(
                self.push_url,
                json=payload,
                timeout=1,          # never block the app thread
            )
        except Exception:           # noqa: BLE001 — fire and forget
            pass


# ── JSON formatter ─────────────────────────────────────────────────────────────

class JsonFormatter(logging.Formatter):
    """Emit one JSON object per line — easy to grep, parse, and ingest."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S"),
            "level":     record.levelname,
            "service":   SERVICE_NAME,
            "logger":    record.name,
            "message":   record.getMessage(),
        }

        # Merge any extra= fields the caller passed
        for key, value in record.__dict__.items():
            if key not in logging.LogRecord.__dict__ and not key.startswith("_"):
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


# ── Factory ────────────────────────────────────────────────────────────────────

def get_logger(name: str) -> logging.Logger:
    """
    Return a configured logger.  Idempotent — calling twice returns same logger.

    Handlers added:
      - StreamHandler  (always, stdout)
      - RotatingFileHandler (always, /app/logs/<name>.log)
      - LokiHandler    (when LOKI_URL env var is set)
    """
    logger = logging.getLogger(name)

    if logger.handlers:           # already configured
        return logger

    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    formatter = JsonFormatter()

    # 1. Stdout
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # 2. Rotating local file (10 MB × 5 files)
    log_path = Path(LOG_DIR)
    log_path.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_path / f"{name}.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 3. Loki (optional, fire-and-forget)
    if LOKI_URL:
        loki_handler = LokiHandler(loki_url=LOKI_URL, service=name)
        loki_handler.setFormatter(formatter)
        logger.addHandler(loki_handler)

    logger.propagate = False
    return logger
