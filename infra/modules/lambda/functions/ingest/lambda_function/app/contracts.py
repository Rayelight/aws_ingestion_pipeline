from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import yaml

from app.s3_utils import get_text


class ContractError(ValueError):
    pass


@dataclass(frozen=True)
class IngestionContract:
    version: int
    id: str
    source: str
    entity: str
    api: Dict[str, Any]
    pagination: Dict[str, Any]
    incremental: Dict[str, Any]
    output: Dict[str, Any]


def _require(d: Dict[str, Any], key: str) -> Any:
    if key not in d:
        raise ContractError(f"Missing required key: {key}")
    return d[key]


def validate_contract(raw: Dict[str, Any], expected_source: str, expected_entity: str) -> IngestionContract:
    version = int(_require(raw, "version"))
    cid = str(_require(raw, "id"))
    source = str(_require(raw, "source"))
    entity = str(_require(raw, "entity"))

    if source != expected_source:
        raise ContractError(f"Contract source mismatch: {source} != {expected_source}")
    if entity != expected_entity:
        raise ContractError(f"Contract entity mismatch: {entity} != {expected_entity}")

    api = _require(raw, "api")
    if "base_url" not in api or "endpoint" not in api:
        raise ContractError("api.base_url and api.endpoint are required")

    pagination = raw.get("pagination") or {"type": "none"}
    incremental = raw.get("incremental") or {"mode": "full"}
    output = raw.get("output") or {"bronze_format": "jsonl", "silver_format": "parquet"}

    return IngestionContract(
        version=version,
        id=cid,
        source=source,
        entity=entity,
        api=api,
        pagination=pagination,
        incremental=incremental,
        output=output,
    )


def load_contract_from_s3(bucket: str, key: str, expected_source: str, expected_entity: str) -> IngestionContract:
    text = get_text(bucket, key)
    raw = yaml.safe_load(text)
    if not isinstance(raw, dict):
        raise ContractError("Contract file must be a YAML mapping/object")
    return validate_contract(raw, expected_source=expected_source, expected_entity=expected_entity)
