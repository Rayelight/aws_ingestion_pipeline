from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

import yaml


class ContractLoadError(ValueError):
    pass


@dataclass(frozen=True)
class ContractSpec:
    version: int
    id: str
    source: str
    entity: str
    raw: Dict[str, Any]

    required_params: Set[str]
    optional_params: Set[str]
    query_placeholders: Set[str]


def _require(d: Dict[str, Any], key: str) -> Any:
    if key not in d:
        raise ContractLoadError(f"Missing required key: {key}")
    return d[key]


def _extract_placeholders_from_query(query: Dict[str, Any]) -> Set[str]:
    # simple "{x}" extraction via str.format style
    found: Set[str] = set()
    for v in query.values():
        if not isinstance(v, str):
            continue
        # find occurrences of {...}
        start = 0
        while True:
            l = v.find("{", start)
            if l == -1:
                break
            r = v.find("}", l + 1)
            if r == -1:
                break
            name = v[l + 1 : r].strip()
            if name:
                found.add(name)
            start = r + 1
    return found


def load_contract_from_s3(
    s3_client,
    bucket: str,
    key: str,
    expected_source: str,
    expected_entity: str,
) -> ContractSpec:
    obj = s3_client.get_object(Bucket=bucket, Key=key)
    text = obj["Body"].read().decode("utf-8")

    raw = yaml.safe_load(text)
    if not isinstance(raw, dict):
        raise ContractLoadError("Contract file must be a YAML mapping/object")

    version = int(_require(raw, "version"))
    cid = str(_require(raw, "id"))
    source = str(_require(raw, "source"))
    entity = str(_require(raw, "entity"))

    if source != expected_source:
        raise ContractLoadError(f"Contract source mismatch: {source} != {expected_source}")
    if entity != expected_entity:
        raise ContractLoadError(f"Contract entity mismatch: {entity} != {expected_entity}")

    params_block = raw.get("params") or {}
    if params_block and not isinstance(params_block, dict):
        raise ContractLoadError("params must be an object if present")

    required = params_block.get("required") or []
    optional = params_block.get("optional") or []
    if not isinstance(required, list) or not all(isinstance(x, str) and x for x in required):
        raise ContractLoadError("params.required must be a list of strings")
    if not isinstance(optional, list) or not all(isinstance(x, str) and x for x in optional):
        raise ContractLoadError("params.optional must be a list of strings")

    api = raw.get("api") or {}
    query = api.get("query") or {}
    if query and not isinstance(query, dict):
        raise ContractLoadError("api.query must be an object if present")
    placeholders = _extract_placeholders_from_query(query if isinstance(query, dict) else {})

    return ContractSpec(
        version=version,
        id=cid,
        source=source,
        entity=entity,
        raw=raw,
        required_params=set(required),
        optional_params=set(optional),
        query_placeholders=placeholders,
    )
