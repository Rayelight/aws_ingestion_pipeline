from __future__ import annotations

from typing import Any, Dict, List, Union


class ResponseMappingError(ValueError):
    pass


def apply_response_mapping(payload: Any, mapping: Dict[str, Any]) -> Any:
    """
    Supports:
      - type=array_to_object : payload is list[list|tuple], output list[dict]
    """
    mtype = mapping.get("type")
    if mtype == "array_to_object":
        cols = mapping.get("columns")
        if not isinstance(cols, list) or not cols:
            raise ResponseMappingError("array_to_object requires non-empty columns")
        return _array_to_object(payload, cols)

    raise ResponseMappingError(f"Unsupported response mapping type: {mtype}")


def _array_to_object(payload: Any, cols: List[str]) -> List[Dict[str, Any]]:
    if not isinstance(payload, list):
        raise ResponseMappingError("array_to_object expects payload to be a list")

    out: List[Dict[str, Any]] = []
    for i, row in enumerate(payload):
        if not isinstance(row, (list, tuple)):
            raise ResponseMappingError(f"Row {i} is not a list/tuple")
        if len(row) < len(cols):
            raise ResponseMappingError(f"Row {i} has {len(row)} values, expected at least {len(cols)}")
        out.append({cols[j]: row[j] for j in range(len(cols))})
    return out
