from __future__ import annotations

import pytest
from tools.config_publisher.validators import (
    validate_contract,
    validate_schema,
    validate_pair,
    ValidationError,
)
from tools.config_publisher.models import Contract, Schema

# --- Test Data Fixtures ---

@pytest.fixture
def valid_contract_raw():
    return {
        "version": 1,
        "id": "test-id",
        "source": "test_source",
        "entity": "test_entity",
        "api": {
            "base_url": "https://test.com",
            "endpoint": "v1/data",
            "query": {"param": "{placeholder}"},
        },
        "params": {
            "required": ["placeholder"]
        }
    }

@pytest.fixture
def valid_schema_raw():
    return {
        "version": 1,
        "id": "test-id",
        "source": "test_source",
        "entity": "test_entity",
        "silver": {
            "columns": [{"name": "col1", "type": "string"}],
            "transforms": {"required": ["col1"]},
            "partitioning": {"by_columns": ["col1"]}
        }
    }

# --- Tests for validate_contract ---

def test_validate_contract_success(valid_contract_raw):
    """Tests successful validation of a correct contract."""
    contract = validate_contract(
        raw=valid_contract_raw,
        source="test_source",
        entity="test_entity",
        ctx="test"
    )
    assert isinstance(contract, Contract)
    assert contract.id == "test-id"

def test_validate_contract_missing_key(valid_contract_raw):
    """Tests failure when a required key is missing."""
    del valid_contract_raw["api"]
    with pytest.raises(ValidationError, match="missing required key 'api'"):
        validate_contract(valid_contract_raw, "test_source", "test_entity", "test")

def test_validate_contract_source_mismatch(valid_contract_raw):
    """Tests failure on source mismatch."""
    with pytest.raises(ValidationError, match="source mismatch"):
        validate_contract(valid_contract_raw, "wrong_source", "test_entity", "test")

def test_validate_contract_undeclared_placeholder(valid_contract_raw):
    """Tests failure when a placeholder in the API query is not declared in params."""
    valid_contract_raw["params"] = {} # No params declared
    with pytest.raises(ValidationError, match="not declared in params"):
        validate_contract(valid_contract_raw, "test_source", "test_entity", "test")

# --- Tests for validate_schema ---

def test_validate_schema_success(valid_schema_raw):
    """Tests successful validation of a correct schema."""
    schema = validate_schema(
        raw=valid_schema_raw,
        source="test_source",
        entity="test_entity",
        ctx="test",
        strict=True
    )
    assert isinstance(schema, Schema)
    assert schema.id == "test-id"

def test_validate_schema_unsupported_type(valid_schema_raw):
    """Tests failure when a column has an unsupported type."""
    valid_schema_raw["silver"]["columns"][0]["type"] = "unsupported_type"
    with pytest.raises(ValidationError, match="unsupported type 'unsupported_type'"):
        validate_schema(valid_schema_raw, "test_source", "test_entity", "test", True)

def test_validate_schema_unknown_transform(valid_schema_raw):
    """Tests failure when an unknown transform key is used."""
    valid_schema_raw["silver"]["transforms"]["unknown_transform"] = {}
    with pytest.raises(ValidationError, match="unknown transform keys"):
        validate_schema(valid_schema_raw, "test_source", "test_entity", "test", True)

def test_validate_schema_keep_drop_conflict(valid_schema_raw):
    """Tests failure in strict mode when 'keep' and 'drop' lists overlap."""
    valid_schema_raw["silver"]["transforms"]["keep"] = ["col1"]
    valid_schema_raw["silver"]["transforms"]["drop"] = ["col1"]
    with pytest.raises(ValidationError, match="keep and transforms.drop overlap"):
        validate_schema(valid_schema_raw, "test_source", "test_entity", "test", strict=True)

def test_validate_schema_keep_drop_conflict_non_strict(valid_schema_raw):
    """Tests that overlapping keep/drop does NOT fail in non-strict mode."""
    valid_schema_raw["silver"]["transforms"]["keep"] = ["col1"]
    valid_schema_raw["silver"]["transforms"]["drop"] = ["col1"]
    # Should not raise an exception
    validate_schema(valid_schema_raw, "test_source", "test_entity", "test", strict=False)

# --- Tests for validate_pair ---

def test_validate_pair_success(valid_contract_raw, valid_schema_raw):
    """Tests successful validation of a matching contract and schema pair."""
    contract = validate_contract(valid_contract_raw, "test_source", "test_entity", "test")
    schema = validate_schema(valid_schema_raw, "test_source", "test_entity", "test", True)
    validate_pair(contract, schema, "test", True)
    # No exception means success

def test_validate_pair_version_mismatch(valid_contract_raw, valid_schema_raw):
    """Tests failure when contract and schema versions do not match."""
    contract = validate_contract(valid_contract_raw, "test_source", "test_entity", "test")
    valid_schema_raw["version"] = 2
    schema = validate_schema(valid_schema_raw, "test_source", "test_entity", "test", True)
    
    with pytest.raises(ValidationError, match="contract.version != schema.version"):
        validate_pair(contract, schema, "test", True)

def test_validate_pair_partition_param_missing(valid_contract_raw, valid_schema_raw):
    """Tests failure when a schema partition parameter is not declared in the contract."""
    contract = validate_contract(valid_contract_raw, "test_source", "test_entity", "test")
    valid_schema_raw["silver"]["partitioning"]["by_params"] = ["missing_param"]
    schema = validate_schema(valid_schema_raw, "test_source", "test_entity", "test", True)
    
    with pytest.raises(ValidationError, match="not declared in contract.params"):
        validate_pair(contract, schema, "test", True)
