from __future__ import annotations

import pytest

from tools.ingestion_requester.validator import (
    validate_source_entity,
    validate_params_shape,
    validate_params_against_contract,
    validate_request,
    RequestValidationError,
)
from tools.ingestion_requester.models import IngestionRequest

# --- Tests for validate_source_entity ---

def test_validate_source_entity_success():
    """Tests that valid source and entity strings pass."""
    validate_source_entity("my_source", "my_entity")
    # No exception means success

@pytest.mark.parametrize("source, entity", [
    ("", "entity"),
    ("source", ""),
    (None, "entity"),
    ("source", None),
    (123, "entity"),
    ("source", 123),
])
def test_validate_source_entity_failure(source, entity):
    """Tests that invalid source or entity strings raise RequestValidationError."""
    with pytest.raises(RequestValidationError):
        validate_source_entity(source, entity)

# --- Tests for validate_params_shape ---

def test_validate_params_shape_success():
    """Tests that a valid params dictionary passes."""
    validate_params_shape({"key1": "value1", "key2": 123})
    # No exception means success

@pytest.mark.parametrize("params", [
    "not_a_dict",
    123,
    ["a", "list"],
    {123: "value"}, # Non-string key
    {"": "value"},   # Empty string key
])
def test_validate_params_shape_failure(params):
    """Tests that invalid params shapes raise RequestValidationError."""
    with pytest.raises(RequestValidationError):
        validate_params_shape(params)

# --- Tests for validate_params_against_contract ---

def test_validate_params_against_contract_success():
    """Tests a successful validation against a contract."""
    validate_params_against_contract(
        params={"p1": "v1", "p2": "v2", "p3": "v3"},
        required={"p1"},
        optional={"p3"},
        placeholders={"p2"}
    )
    # No exception means success

def test_validate_params_missing_required():
    """Tests that a missing required parameter raises an error."""
    with pytest.raises(RequestValidationError, match="Missing required params"):
        validate_params_against_contract(
            params={"p2": "v2"},
            required={"p1"},
            optional={"p3"},
            placeholders={"p2"}
        )

def test_validate_params_missing_placeholder():
    """Tests that a missing parameter required by a placeholder raises an error."""
    with pytest.raises(RequestValidationError, match="Missing params required by api.query placeholders"):
        validate_params_against_contract(
            params={"p1": "v1"},
            required={"p1"},
            optional={"p3"},
            placeholders={"p2"}
        )

# --- Tests for validate_request ---

def test_validate_request_success():
    """Tests a successful validation of a full IngestionRequest."""
    req = IngestionRequest(
        source="my_source",
        entity="my_entity",
        run_id="my_run_id",
        params={"key": "value"}
    )
    validate_request(req)
    # No exception means success

def test_validate_request_invalid_run_id():
    """Tests that an invalid run_id raises an error."""
    with pytest.raises(RequestValidationError, match="run_id must be a non-empty string"):
        req = IngestionRequest(
            source="my_source",
            entity="my_entity",
            run_id="", # Invalid run_id
            params={"key": "value"}
        )
        validate_request(req)
