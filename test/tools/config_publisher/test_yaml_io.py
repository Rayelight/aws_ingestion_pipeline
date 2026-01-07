from __future__ import annotations

from pathlib import Path
import pytest
import yaml

from tools.config_publisher.yaml_io import read_yaml, ValidationError

# Use pytest's tmp_path fixture to create temporary files
def test_read_yaml_success(tmp_path: Path):
    """Tests that a valid YAML file is read and parsed correctly."""
    # Arrange
    content = "key: value\nnested:\n  - item1\n  - item2"
    p = tmp_path / "test.yaml"
    p.write_text(content, encoding="utf-8")

    # Act
    data = read_yaml(p)

    # Assert
    assert isinstance(data, dict)
    assert data["key"] == "value"
    assert data["nested"] == ["item1", "item2"]

def test_read_yaml_file_not_found():
    """Tests that FileNotFoundError is raised for a non-existent file."""
    # Arrange
    p = Path("non_existent_file.yaml")
    
    # Act & Assert
    with pytest.raises(FileNotFoundError, match="Missing file"):
        read_yaml(p)

def test_read_yaml_not_a_dict(tmp_path: Path):
    """Tests that ValidationError is raised if the YAML root is not a dictionary/mapping."""
    # Arrange
    content = "- item1\n- item2" # A list, not a dict
    p = tmp_path / "list.yaml"
    p.write_text(content, encoding="utf-8")

    # Act & Assert
    with pytest.raises(ValidationError, match="must be a YAML mapping/object"):
        read_yaml(p)

def test_read_yaml_invalid_syntax(tmp_path: Path):
    """Tests that the underlying yaml.YAMLError is propagated for invalid syntax."""
    # Arrange
    content = "key: value\n  - badly: indented"
    p = tmp_path / "bad.yaml"
    p.write_text(content, encoding="utf-8")
    
    # Act & Assert
    with pytest.raises(yaml.YAMLError):
        read_yaml(p)
