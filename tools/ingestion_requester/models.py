from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class IngestionRequest:
    source: str
    entity: str
    run_id: str
    params: Dict[str, Any]
