from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

from .models import ValidationError


def read_yaml(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing file: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValidationError(f"{path} must be a YAML mapping/object")
    return raw
