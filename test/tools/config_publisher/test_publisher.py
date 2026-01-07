from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock, call

import pytest

from tools.config_publisher.publisher import publish_all
from tools.config_publisher.models import DatasetFiles, Contract, Schema, ValidationError
from tools.config_publisher.config import PublisherConfig

@pytest.fixture
def mock_publisher_config(tmp_path: Path):
    """Provides a mock PublisherConfig."""
    return PublisherConfig(
        region="us-east-1",
        datalake_bucket="test-bucket",
        local_contracts_dir=tmp_path / "contracts",
        local_schema_dir=tmp_path / "schema",
        s3_contracts_prefix="configs/contracts/",
        s3_schema_prefix="configs/schema/",
        strict=True,
    )

@pytest.pytest.fixture
def mock_publisher_dependencies():
    """Mocks all dependencies for the publisher module."""
    with patch('tools.config_publisher.publisher.S3Uploader') as mock_uploader, \
         patch('tools.config_publisher.publisher.discover_datasets') as mock_discover, \
         patch('tools.config_publisher.publisher.read_yaml') as mock_read_yaml, \
         patch('tools.config_publisher.publisher.validate_contract') as mock_val_contract, \
         patch('tools.config_publisher.publisher.validate_schema') as mock_val_schema, \
         patch('tools.config_publisher.publisher.validate_pair') as mock_val_pair:
        
        # Configure mocks
        mock_uploader_instance = MagicMock()
        mock_uploader.return_value = mock_uploader_instance
        
        yield {
            "uploader": mock_uploader_instance,
            "discover": mock_discover,
            "read_yaml": mock_read_yaml,
            "val_contract": mock_val_contract,
            "val_schema": mock_val_schema,
            "val_pair": mock_val_pair,
        }

def test_publish_all_success(mock_publisher_config, mock_publisher_dependencies):
    """
    Tests the happy path where discovery, validation, and uploading all succeed.
    """
    # Arrange
    cfg = mock_publisher_config
    
    # Mock discovery results
    ds_files = [DatasetFiles("source1", "entity1", Path("c/s1/e1.yaml"), Path("s/s1/e1.yaml"))]
    mock_publisher_dependencies["discover"].return_value = ds_files

    # Mock file content reads
    mock_publisher_dependencies["read_yaml"].side_effect = [
        {"version": 1, "id": "c1"}, # contract
        {"version": 1, "id": "s1"}, # schema
    ]
    
    # Mock path reads for uploader
    with patch.object(Path, 'read_text', return_value="yaml content") as mock_read_text:

        # Mock validation successes (by having them not raise an error)
        mock_contract = Contract(1, "c1", "s1", "e1", {})
        mock_schema = Schema(1, "s1", "s1", "e1", {})
        mock_publisher_dependencies["val_contract"].return_value = mock_contract
        mock_publisher_dependencies["val_schema"].return_value = mock_schema

        # Mock uploader result
        mock_upload_result = MagicMock(s3_key="s3://key", size_kb=1.0, sha256_12="abc")
        mock_publisher_dependencies["uploader"].put_yaml.return_value = mock_upload_result

        # Act
        reports = publish_all(cfg)

        # Assert
        # Discovery was called
        mock_publisher_dependencies["discover"].assert_called_once_with(cfg.local_contracts_dir, cfg.local_schema_dir)
        
        # Validation was called
        mock_publisher_dependencies["val_contract"].assert_called_once()
        mock_publisher_dependencies["val_schema"].assert_called_once()
        mock_publisher_dependencies["val_pair"].assert_called_once()
        
        # Uploader was called twice (once for contract, once for schema)
        assert mock_publisher_dependencies["uploader"].put_yaml.call_count == 2
        calls = mock_publisher_dependencies["uploader"].put_yaml.call_args_list
        assert calls[0].args[0] == "configs/contracts/source1/entity1.yaml"
        assert calls[1].args[0] == "configs/schema/source1/entity1.yaml"

        # Report was generated
        assert len(reports) == 1
        assert reports[0].dataset == "source1/entity1"
        assert reports[0].contract.sha256_12 == "abc"


def test_publish_all_validation_error(mock_publisher_config, mock_publisher_dependencies):
    """
    Tests that if one dataset fails validation, the process continues with others,
    but ultimately raises a comprehensive error.
    """
    # Arrange
    cfg = mock_publisher_config
    
    ds_files = [
        DatasetFiles("source1", "entity1_fail", Path("c/s1/e1.yaml"), Path("s/s1/e1.yaml")),
        DatasetFiles("source2", "entity2_ok", Path("c/s2/e2.yaml"), Path("s/s2/e2.yaml")),
    ]
    mock_publisher_dependencies["discover"].return_value = ds_files

    # Mock validation to fail on the first dataset
    mock_publisher_dependencies["val_contract"].side_effect = [
        ValidationError("Invalid contract"), # Fails for entity1
        MagicMock(), # Succeeds for entity2
    ]
    
    # Mock other dependencies for the successful case
    mock_publisher_dependencies["read_yaml"].return_value = {}
    mock_publisher_dependencies["val_schema"].return_value = MagicMock()
    mock_publisher_dependencies["uploader"].put_yaml.return_value = MagicMock()
    
    with patch.object(Path, 'read_text', return_value="..."):
        # Act & Assert
        with pytest.raises(ValidationError, match="Publishing failed"):
            publish_all(cfg)

    # Check that the uploader was only called for the valid dataset
    assert mock_publisher_dependencies["uploader"].put_yaml.call_count == 2
    
def test_publish_all_no_datasets_found(mock_publisher_config, mock_publisher_dependencies):
    """
    Tests that an error is raised if no datasets are discovered.
    """
    # Arrange
    cfg = mock_publisher_config
    mock_publisher_dependencies["discover"].return_value = [] # No datasets found
    
    # Act & Assert
    with pytest.raises(ValidationError, match="No datasets found"):
        publish_all(cfg)
