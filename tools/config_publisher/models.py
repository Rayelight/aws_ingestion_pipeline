from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


SUPPORTED_TYPES = {
    "string",
    "int64",
    "float64",
    "boolean",
    "timestamp_ms",
    "timestamp_s",
    "date",
}

ALLOWED_TRANSFORM_KEYS = {
    "keep",
    "drop",
    "rename",
    "cast",
    "trim",
    "lower",
    "upper",
    "null_if",
    "fillna",
    "deduplicate",
    "add_columns",
    "required",
    "non_null",
    "unique_key",
}


class ValidationError(ValueError):
    pass


@dataclass(frozen=True)
class Contract:
    version: int
    id: str
    source: str
    entity: str
    raw: Dict[str, Any]


@dataclass(frozen=True)
class Schema:
    version: int
    id: str
    source: str
    entity: str
    raw: Dict[str, Any]


@dataclass(frozen=True)
class DatasetFiles:
    source: str
    entity: str
    contract_path: Path
    schema_path: Path


@dataclass(frozen=True)
class DatasetConfig:
    files: DatasetFiles
    contract: Contract
    schema: Schema


@dataclass(frozen=True)
class PublishArtifact:
    s3_key: str
    size_kb: float
    sha256_12: str


@dataclass(frozen=True)
class PublishReport:
    dataset: str
    contract: PublishArtifact
    schema: PublishArtifact
