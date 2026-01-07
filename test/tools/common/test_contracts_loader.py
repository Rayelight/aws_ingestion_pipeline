from __future__ import annotations

import pytest
import yaml
from unittest.mock import MagicMock

from tools.common.contracts_loader import load_contract_from_s3, ContractLoadError, ContractSpec

# --- Test Data ---

BASE_CONTRACT = {
    "version": 1,
    "id": "test-contract",
    "source": "test_source",
    "entity": "test_entity",
    "api": {
        "base_url": "https://api.test.com",
        "endpoint": "test_endpoint",
        "query": {
            "param1": "value1",
            "param2": "{placeholder1}",
        }
    },
    "params": {
        "required": ["placeholder1"],
        "optional": ["opt1"],
    }
}

# Helper to create variations of the base contract
def get_contract_yaml(overrides: dict = None) -> bytes:
    data = BASE_CONTRACT.copy()
    if overrides:
        data.update(overrides)
    return yaml.dump(data).encode('utf-8')

# --- Tests ---

def test_load_contract_from_s3_success(mock_s3_client):
    """
    Tests successful loading and parsing of a valid contract from S3.
    """
    # Arrange
    contract_yaml = get_contract_yaml()
    mock_s3_client.get_object.return_value = {
        'Body': MagicMock(read=MagicMock(return_value=contract_yaml))
    }

    # Act
    contract = load_contract_from_s3(
        s3_client=mock_s3_client,
        bucket="test-bucket",
        key="test-key.yaml",
        expected_source="test_source",
        expected_entity="test_entity"
    )

    # Assert
    assert isinstance(contract, ContractSpec)
    assert contract.id == "test-contract"
    assert contract.source == "test_source"
    assert contract.entity == "test_entity"
    assert contract.required_params == {"placeholder1"}
    assert contract.optional_params == {"opt1"}
    assert contract.query_placeholders == {"placeholder1"}
    mock_s3_client.get_object.assert_called_once_with(Bucket="test-bucket", Key="test-key.yaml")

def test_load_contract_missing_required_key(mock_s3_client):
    """
    Tests that ContractLoadError is raised if a required top-level key is missing.
    """
    # Arrange
    contract_data = BASE_CONTRACT.copy()
    del contract_data['id']
    contract_yaml = yaml.dump(contract_data).encode('utf-8')
    mock_s3_client.get_object.return_value['Body'].read.return_value = contract_yaml

    # Act & Assert
    with pytest.raises(ContractLoadError, match="Missing required key: id"):
        load_contract_from_s3(
            s3_client=mock_s3_client,
            bucket="test-bucket",
            key="test-key.yaml",
            expected_source="test_source",
            expected_entity="test_entity"
        )

def test_load_contract_mismatched_source(mock_s3_client):
    """
    Tests that ContractLoadError is raised if the source in the contract doesn't match the expected source.
    """
    # Arrange
    contract_yaml = get_contract_yaml()
    mock_s3_client.get_object.return_value['Body'].read.return_value = contract_yaml

    # Act & Assert
    with pytest.raises(ContractLoadError, match="Contract source mismatch"):
        load_contract_from_s3(
            s3_client=mock_s3_client,
            bucket="test-bucket",
            key="test-key.yaml",
            expected_source="wrong_source", # This is the mismatch
            expected_entity="test_entity"
        )

def test_load_contract_mismatched_entity(mock_s3_client):
    """
    Tests that ContractLoadError is raised if the entity in the contract doesn't match the expected entity.
    """
    # Arrange
    contract_yaml = get_contract_yaml()
    mock_s3_client.get_object.return_value['Body'].read.return_value = contract_yaml

    # Act & Assert
    with pytest.raises(ContractLoadError, match="Contract entity mismatch"):
        load_contract_from_s3(
            s3_client=mock_s3_client,
            bucket="test-bucket",
            key="test-key.yaml",
            expected_source="test_source",
            expected_entity="wrong_entity" # This is the mismatch
        )
        
def test_extract_placeholders_from_query():
    """
    Tests the private helper function for extracting placeholders from a query dict.
    """
    from tools.common.contracts_loader import _extract_placeholders_from_query
    
    query = {
        "url": "https://test.com/{placeholder1}/details",
        "param1": "{placeholder2}",
        "param2": "no_placeholder",
        "param3": "{placeholder3} and {placeholder4}"
    }
    
    placeholders = _extract_placeholders_from_query(query)
    
    assert placeholders == {"placeholder1", "placeholder2", "placeholder3", "placeholder4"}

def test_load_contract_bad_yaml(mock_s3_client):
    """
    Tests that a generic error (or yaml.YAMLError) is handled if the S3 object is not valid YAML.
    """
    # Arrange
    bad_yaml = b"key: value\n  - unindented_list_item"
    mock_s3_client.get_object.return_value['Body'].read.return_value = bad_yaml

    # Act & Assert
    with pytest.raises(yaml.YAMLError):
        load_contract_from_s3(
            s3_client=mock_s3_client,
            bucket="test-bucket",
            key="test-key.yaml",
            expected_source="test_source",
            expected_entity="test_entity"
        )
