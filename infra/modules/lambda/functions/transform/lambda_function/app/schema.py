from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import yaml

from app.s3_utils import get_text


class SchemaError(ValueError):
    pass


@dataclass(frozen=True)
class Schema:
    version: int
    id: str
    source: str
    entity: str
    silver: Dict[str, Any]  # columns/transforms/partitioning


def _require(d: Dict[str, Any], key: str) -> Any:
    if key not in d:
        raise SchemaError(f"Missing required key: {key}")
    return d[key]


def validate_schema(raw: Dict[str, Any], expected_source: str, expected_entity: str) -> Schema:
    version = int(_require(raw, "version"))
    sid = str(_require(raw, "id"))
    source = str(_require(raw, "source"))
    entity = str(_require(raw, "entity"))

    if source != expected_source:
        raise SchemaError(f"Schema source mismatch: {source} != {expected_source}")
    if entity != expected_entity:
        raise SchemaError(f"Schema entity mismatch: {entity} != {expected_entity}")

    silver = _require(raw, "silver")
    cols = silver.get("columns")
    if not isinstance(cols, list) or not cols:
        raise SchemaError("silver.columns must be a non-empty list")

    return Schema(version=version, id=sid, source=source, entity=entity, silver=silver)


def load_schema_from_s3(bucket: str, key: str, expected_source: str, expected_entity: str) -> Schema:
    text = get_text(bucket, key)
    raw = yaml.safe_load(text)
    if not isinstance(raw, dict):
        raise SchemaError("Schema file must be a YAML mapping/object")
    return validate_schema(raw, expected_source=expected_source, expected_entity=expected_entity)
