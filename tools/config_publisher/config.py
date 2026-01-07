from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tools.common.app_config import load_app_config


@dataclass(frozen=True)
class PublisherConfig:
    region: str
    datalake_bucket: str

    local_contracts_dir: Path
    local_schema_dir: Path

    s3_contracts_prefix: str
    s3_schema_prefix: str

    strict: bool


def load_config() -> PublisherConfig:
    app = load_app_config()
    local_root = app.repo.configs_local_root

    return PublisherConfig(
        region=app.aws.region,
        datalake_bucket=app.aws.datalake_bucket,

        local_contracts_dir=local_root / "contracts",
        local_schema_dir=local_root / "schema",

        s3_contracts_prefix=app.prefixes.s3_contracts_prefix,
        s3_schema_prefix=app.prefixes.s3_schema_prefix,

        strict=app.strict,
    )
