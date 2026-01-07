from __future__ import annotations

from pathlib import Path
from typing import List

from .models import DatasetFiles, ValidationError


def discover_datasets(contracts_dir: Path, schema_dir: Path) -> List[DatasetFiles]:
    if not contracts_dir.exists():
        raise FileNotFoundError(f"Missing local contracts dir: {contracts_dir}")
    if not schema_dir.exists():
        raise FileNotFoundError(f"Missing local schema dir: {schema_dir}")

    datasets: List[DatasetFiles] = []
    for contract_path in sorted(contracts_dir.rglob("*.yaml")):
        rel = contract_path.relative_to(contracts_dir)
        # expect: <source>/<entity>.yaml
        if len(rel.parts) != 2:
            raise ValidationError(f"Contract path must be contracts/<source>/<entity>.yaml, got: {rel}")

        source = rel.parts[0]
        entity = rel.stem
        schema_path = schema_dir / source / f"{entity}.yaml"
        datasets.append(DatasetFiles(source=source, entity=entity, contract_path=contract_path, schema_path=schema_path))

    return datasets
