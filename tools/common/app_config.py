from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AwsConfig:
    region: str
    datalake_bucket: str
    ingest_queue_name: str
    transform_queue_name: str
    tracking_table_name: str


@dataclass(frozen=True)
class RepoConfig:
    repo_root: Path
    configs_local_root: Path  # repo_root/configs_local


@dataclass(frozen=True)
class PrefixConfig:
    s3_contracts_prefix: str
    s3_schema_prefix: str
    data_bronze_prefix: str
    data_silver_prefix: str


@dataclass(frozen=True)
class AppConfig:
    aws: AwsConfig
    repo: RepoConfig
    prefixes: PrefixConfig
    strict: bool


def load_app_config() -> AppConfig:
    """
    ✅ Pas d'args, pas d'env vars : tu modifies ici si besoin.
    """
    repo_root = Path(__file__).resolve().parents[2]
    configs_local = repo_root / "configs_local"

    return AppConfig(
        aws=AwsConfig(
            region="eu-west-3",
            datalake_bucket="ingesteur-dev-datalake",
            ingest_queue_name="ingesteur-dev-ingest",
            transform_queue_name="ingesteur-dev-transform",
            tracking_table_name="ingesteur-dev-ingestion-runs",
        ),
        repo=RepoConfig(
            repo_root=repo_root,
            configs_local_root=configs_local,
        ),
        prefixes=PrefixConfig(
            s3_contracts_prefix="configs/contracts/",
            s3_schema_prefix="configs/schema/",
            data_bronze_prefix="data/bronze/",
            data_silver_prefix="data/silver/",
        ),
        strict=True,
    )
