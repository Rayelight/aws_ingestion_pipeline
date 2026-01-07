from __future__ import annotations

from dataclasses import dataclass

from tools.common.app_config import load_app_config


@dataclass(frozen=True)
class SmokeConfig:
    region: str
    datalake_bucket: str
    tracking_table_name: str

    ingest_queue_name: str
    transform_queue_name: str

    bronze_prefix: str
    silver_prefix: str

    poll_interval_sec: int
    timeout_sec: int


def load_config() -> SmokeConfig:
    app = load_app_config()
    return SmokeConfig(
        region=app.aws.region,
        datalake_bucket=app.aws.datalake_bucket,
        tracking_table_name=app.aws.tracking_table_name,
        ingest_queue_name=app.aws.ingest_queue_name,
        transform_queue_name=app.aws.transform_queue_name,
        bronze_prefix=app.prefixes.data_bronze_prefix,
        silver_prefix=app.prefixes.data_silver_prefix,
        poll_interval_sec=5,
        timeout_sec=240,
    )
