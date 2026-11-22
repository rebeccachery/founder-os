"""Logging configuration for the CLI, nightly job and API.

Plain ``key=value`` lines by default (easy to grep in the nightly log); set
``LOG_FORMAT=json`` for one JSON object per line.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

_RESERVED = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime"}


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "msg": record.getMessage(),
        }
        payload.update({k: v for k, v in record.__dict__.items() if k not in _RESERVED})
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class _KeyValueFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extras = {k: v for k, v in record.__dict__.items() if k not in _RESERVED}
        if extras:
            base += " " + " ".join(f"{k}={v}" for k, v in extras.items())
        return base


def configure_logging(level: str | None = None) -> None:
    handler = logging.StreamHandler(sys.stdout)
    if os.getenv("LOG_FORMAT", "text").lower() == "json":
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            _KeyValueFormatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s", "%H:%M:%S")
        )
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel((level or os.getenv("LOG_LEVEL") or "INFO").upper())
    # httpx logs every request at INFO; keep it for debugging only.
    logging.getLogger("httpx").setLevel(logging.WARNING)
