from __future__ import annotations

from typing import Any, Dict, Set

from .models import IngestionRequest


class RequestValidationError(ValueError):
    pass


def validate_source_entity(source: str, entity: str) -> None:
    if not isinstance(source, str) or not source.strip():
        raise RequestValidationError("source must be a non-empty string")
    if not isinstance(entity, str) or not entity.strip():
        raise RequestValidationError("entity must be a non-empty string")


def validate_params_shape(params: Dict[str, Any]) -> None:
    if not isinstance(params, dict):
        raise RequestValidationError("params must be an object/dict")
    for k in params.keys():
        if not isinstance(k, str) or not k:
            raise RequestValidationError(f"Invalid param key: {k!r}")


def validate_params_against_contract(
    params: Dict[str, Any],
    required: Set[str],
    optional: Set[str],
    placeholders: Set[str],
) -> None:
    """
    - required params must exist and be non-null
    - if a placeholder exists in api.query, it must be present in params
      (unless it’s optional and absent AND you later fill defaults; caller can fill before calling this)
    - disallow unknown keys? (non: keep flexible)
    """
    missing_required = [k for k in sorted(required) if k not in params or params.get(k) is None]
    if missing_required:
        raise RequestValidationError(f"Missing required params: {missing_required}")

    missing_placeholders = [k for k in sorted(placeholders) if k not in params or params.get(k) is None]
    if missing_placeholders:
        raise RequestValidationError(f"Missing params required by api.query placeholders: {missing_placeholders}")


def validate_request(req: IngestionRequest) -> None:
    validate_source_entity(req.source, req.entity)
    if not isinstance(req.run_id, str) or not req.run_id.strip():
        raise RequestValidationError("run_id must be a non-empty string")
    validate_params_shape(req.params)
