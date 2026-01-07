# identique à ingest (tu peux le dupliquer ou le mettre dans un layer si tu veux)
import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger("ingesteur")
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

_context: Dict[str, Any] = {}


def with_context(**kwargs: Any) -> None:
    _context.update({k: v for k, v in kwargs.items() if v is not None})


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        if _context:
            base.update(_context)
        if record.exc_info:
            base["exc_info"] = self.formatException(record.exc_info)
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            base.update(record.extra)
        return json.dumps(base, ensure_ascii=False)


if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(JsonFormatter())
    logger.addHandler(h)
    logger.propagate = False
