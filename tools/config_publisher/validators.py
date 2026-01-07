from __future__ import annotations

import re
from typing import Any, Dict, List, Set, Tuple

from .models import (
    ALLOWED_TRANSFORM_KEYS,
    SUPPORTED_TYPES,
    Contract,
    Schema,
    ValidationError,
)

_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def _require(d: Dict[str, Any], key: str, ctx: str) -> Any:
    if key not in d:
        raise ValidationError(f"{ctx}: missing required key '{key}'")
    return d[key]

def validate_contract(raw: Dict[str, Any], source: str, entity: str, ctx: str) -> Contract:
    version = int(_require(raw, "version", ctx))
    cid = str(_require(raw, "id", ctx))
    csource = str(_require(raw, "source", ctx))
    centity = str(_require(raw, "entity", ctx))

    if csource != source:
        raise ValidationError(f"{ctx}: source mismatch: {csource} != {source}")
    if centity != entity:
        raise ValidationError(f"{ctx}: entity mismatch: {centity} != {entity}")

    api = _require(raw, "api", ctx)
    if not isinstance(api, dict):
        raise ValidationError(f"{ctx}: api must be an object")
    if "base_url" not in api or "endpoint" not in api:
        raise ValidationError(f"{ctx}: api.base_url and api.endpoint are required")
    if "query" in api and not isinstance(api["query"], dict):
        raise ValidationError(f"{ctx}: api.query must be an object if present")

    params = raw.get("params", {})
    if params is not None and not isinstance(params, dict):
        raise ValidationError(f"{ctx}: params must be an object if present")
    if params:
        required = params.get("required", [])
        optional = params.get("optional", [])
        if required and not isinstance(required, list):
            raise ValidationError(f"{ctx}: params.required must be a list")
        if optional and not isinstance(optional, list):
            raise ValidationError(f"{ctx}: params.optional must be a list")

        # Validate placeholders in api.query
        query = api.get("query") or {}
        placeholders = _extract_placeholders_from_map(query)
        declared = set(required) | set(optional)
        missing = placeholders - declared
        if missing:
            raise ValidationError(f"{ctx}: api.query placeholders not declared in params.*: {sorted(missing)}")

    # response_mapping (optional)
    rm = api.get("response_mapping")
    if rm is not None:
        if not isinstance(rm, dict) or "type" not in rm:
            raise ValidationError(f"{ctx}: api.response_mapping must be an object with 'type'")
        if rm["type"] != "array_to_object":
            raise ValidationError(f"{ctx}: api.response_mapping.type unsupported: {rm['type']}")
        cols = rm.get("columns")
        if not isinstance(cols, list) or not cols or not all(isinstance(x, str) and x for x in cols):
            raise ValidationError(f"{ctx}: api.response_mapping.columns must be a non-empty list of strings")

    return Contract(version=version, id=cid, source=csource, entity=centity, raw=raw)



def validate_schema(raw: Dict[str, Any], source: str, entity: str, ctx: str, strict: bool) -> Schema:
    version = int(_require(raw, "version", ctx))
    sid = str(_require(raw, "id", ctx))
    ssource = str(_require(raw, "source", ctx))
    sentity = str(_require(raw, "entity", ctx))

    if ssource != source:
        raise ValidationError(f"{ctx}: source mismatch: {ssource} != {source}")
    if sentity != entity:
        raise ValidationError(f"{ctx}: entity mismatch: {sentity} != {entity}")

    silver = _require(raw, "silver", ctx)
    if not isinstance(silver, dict):
        raise ValidationError(f"{ctx}: silver must be an object")

    columns = silver.get("columns")
    if not isinstance(columns, list) or not columns:
        raise ValidationError(f"{ctx}: silver.columns must be a non-empty list")

    col_names: List[str] = []
    for i, col in enumerate(columns):
        if not isinstance(col, dict):
            raise ValidationError(f"{ctx}: silver.columns[{i}] must be an object")
        name = col.get("name")
        typ = col.get("type")
        if not name or not typ:
            raise ValidationError(f"{ctx}: silver.columns[{i}] requires name/type")
        if typ not in SUPPORTED_TYPES:
            raise ValidationError(f"{ctx}: unsupported type '{typ}' for column '{name}'")
        col_names.append(str(name))

    if len(set(col_names)) != len(col_names):
        raise ValidationError(f"{ctx}: duplicate column names in silver.columns")

    declared_cols = set(col_names)
    transforms = silver.get("transforms") or {}
    if transforms and not isinstance(transforms, dict):
        raise ValidationError(f"{ctx}: silver.transforms must be an object if present")

    partitioning = silver.get("partitioning") or {}
    if partitioning and not isinstance(partitioning, dict):
        raise ValidationError(f"{ctx}: silver.partitioning must be an object if present")

    _validate_transforms(transforms, declared_cols, ctx, strict)
    _validate_partitioning(partitioning, declared_cols, ctx)

    return Schema(version=version, id=sid, source=ssource, entity=sentity, raw=raw)


def validate_pair(contract: Contract, schema: Schema, ctx: str, strict: bool) -> None:
    # hard checks
    if contract.version != schema.version:
        raise ValidationError(f"{ctx}: contract.version != schema.version ({contract.version} != {schema.version})")
    if contract.id != schema.id:
        raise ValidationError(f"{ctx}: contract.id != schema.id ({contract.id} != {schema.id})")
    if contract.source != schema.source:
        raise ValidationError(f"{ctx}: contract.source != schema.source ({contract.source} != {schema.source})")
    if contract.entity != schema.entity:
        raise ValidationError(f"{ctx}: contract.entity != schema.entity ({contract.entity} != {schema.entity})")

    # quality: partitioning.by_params should exist in contract.params if present
    schema_part = ((schema.raw.get("silver") or {}).get("partitioning") or {})
    by_params = schema_part.get("by_params") or []
    if by_params:
        params = contract.raw.get("params") or {}
        declared = set(params.get("required", [])) | set(params.get("optional", []))
        missing = set(by_params) - declared
        if missing:
            raise ValidationError(f"{ctx}: schema.partitioning.by_params not declared in contract.params: {sorted(missing)}")


def _validate_transforms(transforms: Dict[str, Any], declared_cols: Set[str], ctx: str, strict: bool) -> None:
    if not transforms:
        return

    unknown = set(transforms.keys()) - ALLOWED_TRANSFORM_KEYS
    if unknown:
        raise ValidationError(f"{ctx}: unknown transform keys: {sorted(unknown)}")

    keep = transforms.get("keep")
    drop = transforms.get("drop")
    rename = transforms.get("rename") or {}
    cast = transforms.get("cast") or {}
    add_cols = transforms.get("add_columns") or []
    required = transforms.get("required") or []
    non_null = transforms.get("non_null") or []
    unique_key = transforms.get("unique_key") or []

    if keep is not None and not isinstance(keep, list):
        raise ValidationError(f"{ctx}: transforms.keep must be a list")
    if drop is not None and not isinstance(drop, list):
        raise ValidationError(f"{ctx}: transforms.drop must be a list")
    if not isinstance(rename, dict):
        raise ValidationError(f"{ctx}: transforms.rename must be an object")
    if not isinstance(cast, dict):
        raise ValidationError(f"{ctx}: transforms.cast must be an object")
    if not isinstance(add_cols, list):
        raise ValidationError(f"{ctx}: transforms.add_columns must be a list")

    # rename: targets must be declared, and no two olds map to same new
    targets = list(rename.values())
    if len(set(targets)) != len(targets):
        raise ValidationError(f"{ctx}: transforms.rename has duplicate targets (collision)")

    for old, new in rename.items():
        if new not in declared_cols:
            raise ValidationError(f"{ctx}: transforms.rename target '{new}' not declared in silver.columns")

    # cast: columns must be declared and types supported
    for col, typ in cast.items():
        if typ not in SUPPORTED_TYPES:
            raise ValidationError(f"{ctx}: transforms.cast unsupported type '{typ}' for '{col}'")
        if col not in declared_cols:
            raise ValidationError(f"{ctx}: transforms.cast column '{col}' not declared in silver.columns")

    # add_columns: each spec defines exactly one source, name must be declared
    for i, spec in enumerate(add_cols):
        if not isinstance(spec, dict):
            raise ValidationError(f"{ctx}: transforms.add_columns[{i}] must be an object")
        name = spec.get("name")
        if not name:
            raise ValidationError(f"{ctx}: transforms.add_columns[{i}] missing 'name'")
        if name not in declared_cols:
            raise ValidationError(f"{ctx}: transforms.add_columns defines '{name}' but it's not in silver.columns")
        sources = sum(int(k in spec) for k in ("from_param", "literal", "from_column"))
        if sources != 1:
            raise ValidationError(f"{ctx}: transforms.add_columns[{i}] must define exactly one of from_param/literal/from_column")

    # required/non_null/unique_key must reference declared columns (post-transforms)
    for col in required:
        if col not in declared_cols:
            raise ValidationError(f"{ctx}: transforms.required column '{col}' not declared in silver.columns")
    for col in non_null:
        if col not in declared_cols:
            raise ValidationError(f"{ctx}: transforms.non_null column '{col}' not declared in silver.columns")
    for col in unique_key:
        if col not in declared_cols:
            raise ValidationError(f"{ctx}: transforms.unique_key column '{col}' not declared in silver.columns")

    # keep/drop contradiction warning -> error if strict
    if keep and drop:
        overlap = set(keep) & set(drop)
        if overlap:
            msg = f"{ctx}: transforms.keep and transforms.drop overlap: {sorted(overlap)}"
            if strict:
                raise ValidationError(msg)
            # else: allow (warning handled at publisher)


def _validate_partitioning(partitioning: Dict[str, Any], declared_cols: Set[str], ctx: str) -> None:
    if not partitioning:
        return
    by_params = partitioning.get("by_params") or []
    by_columns = partitioning.get("by_columns") or []

    if by_params and not isinstance(by_params, list):
        raise ValidationError(f"{ctx}: silver.partitioning.by_params must be a list")
    if by_columns and not isinstance(by_columns, list):
        raise ValidationError(f"{ctx}: silver.partitioning.by_columns must be a list")

    for c in by_columns:
        if c not in declared_cols:
            raise ValidationError(f"{ctx}: partitioning.by_columns '{c}' not declared in silver.columns")


def _extract_placeholders_from_map(m: Dict[str, Any]) -> Set[str]:
    found: Set[str] = set()
    for v in m.values():
        if isinstance(v, str):
            for g in _PLACEHOLDER_RE.findall(v):
                found.add(g)
    return found
