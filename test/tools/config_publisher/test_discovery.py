from __future__ import annotations

from pathlib import Path
import pytest

from tools.config_publisher.discovery import discover_datasets, ValidationError
from tools.config_publisher.models import DatasetFiles

def test_discover_datasets_success(tmp_path: Path):
    """
    Tests that datasets are correctly discovered from a valid directory structure.
    """
    # Arrange
    contracts_dir = tmp_path / "contracts"
    schema_dir = tmp_path / "schema"

    # Create source 'binance'
    (contracts_dir / "binance").mkdir(parents=True)
    (schema_dir / "binance").mkdir(parents=True)
    (contracts_dir / "binance" / "trades.yaml").touch()
    (schema_dir / "binance" / "trades.yaml").touch()

    # Create source 'coinbase'
    (contracts_dir / "coinbase").mkdir(parents=True)
    (schema_dir / "coinbase").mkdir(parents=True)
    (contracts_dir / "coinbase" / "orders.yaml").touch()
    (schema_dir / "coinbase" / "orders.yaml").touch()
    
    # Act
    datasets = discover_datasets(contracts_dir, schema_dir)

    # Assert
    assert len(datasets) == 2
    assert all(isinstance(ds, DatasetFiles) for ds in datasets)

    # Check the binance dataset
    binance_ds = next(ds for ds in datasets if ds.source == "binance")
    assert binance_ds.entity == "trades"
    assert binance_ds.contract_path == contracts_dir / "binance" / "trades.yaml"
    assert binance_ds.schema_path == schema_dir / "binance" / "trades.yaml"
    
    # Check the coinbase dataset
    coinbase_ds = next(ds for ds in datasets if ds.source == "coinbase")
    assert coinbase_ds.entity == "orders"
    assert coinbase_ds.contract_path == contracts_dir / "coinbase" / "orders.yaml"
    assert coinbase_ds.schema_path == schema_dir / "coinbase" / "orders.yaml"

def test_discover_datasets_missing_contracts_dir(tmp_path: Path):
    """
    Tests that FileNotFoundError is raised if the contracts directory doesn't exist.
    """
    # Arrange
    contracts_dir = tmp_path / "non_existent_contracts"
    schema_dir = tmp_path / "schema"
    schema_dir.mkdir()

    # Act & Assert
    with pytest.raises(FileNotFoundError, match="Missing local contracts dir"):
        discover_datasets(contracts_dir, schema_dir)

def test_discover_datasets_invalid_contract_path(tmp_path: Path):
    """
    Tests that a ValidationError is raised for contracts not in a <source>/<entity>.yaml structure.
    """
    # Arrange
    contracts_dir = tmp_path / "contracts"
    schema_dir = tmp_path / "schema"
    contracts_dir.mkdir()
    schema_dir.mkdir()
    
    # Create a contract file at the root of the contracts_dir (invalid)
    (contracts_dir / "trades.yaml").touch()

    # Act & Assert
    with pytest.raises(ValidationError, match="Contract path must be contracts/<source>/<entity>.yaml"):
        discover_datasets(contracts_dir, schema_dir)

def test_discover_datasets_empty(tmp_path: Path):
    """
    Tests that an empty list is returned when there are no YAML files to discover.
    """
    # Arrange
    contracts_dir = tmp_path / "contracts"
    schema_dir = tmp_path / "schema"
    contracts_dir.mkdir()
    schema_dir.mkdir()

    # Act
    datasets = discover_datasets(contracts_dir, schema_dir)

    # Assert
    assert datasets == []
