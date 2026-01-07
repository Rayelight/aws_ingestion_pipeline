from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from tools.common.aws_clients import make_aws_clients
from .config import SmokeConfig
from .ddb_tracker import get_run_state
from .s3_finder import find_run_artifacts
from .sqs_probe import get_queue_counts


@dataclass(frozen=True)
class SmokeResult:
    source: str
    entity: str
    run_id: str

    ddb_status: Optional[str]
    bronze_ok: bool
    silver_ok: bool

    bronze_success_key: Optional[str]
    silver_success_key: Optional[str]


def wait_for_run(cfg: SmokeConfig, source: str, entity: str, run_id: str) -> SmokeResult:
    clients = make_aws_clients(cfg.region)

    deadline = time.time() + cfg.timeout_sec
    last_status = None
    last_bronze_ok = False
    last_silver_ok = False
    last_artifacts = None

    while time.time() < deadline:
        state = get_run_state(clients.dynamodb, cfg.tracking_table_name, source, entity, run_id)
        last_status = state.status

        artifacts = find_run_artifacts(
            clients.s3,
            cfg.datalake_bucket,
            cfg.bronze_prefix,
            cfg.silver_prefix,
            source,
            entity,
            run_id,
        )
        last_artifacts = artifacts

        bronze_ok = bool(artifacts.bronze_success_key and artifacts.bronze_data_key)
        silver_ok = bool(artifacts.silver_success_key and artifacts.silver_parquet_key)

        last_bronze_ok = bronze_ok
        last_silver_ok = silver_ok

        # Condition de succès: silver OK (ou au minimum DDB SILVER_WRITTEN)
        if silver_ok or state.status == "SILVER_WRITTEN":
            return SmokeResult(
                source=source,
                entity=entity,
                run_id=run_id,
                ddb_status=state.status,
                bronze_ok=bronze_ok,
                silver_ok=silver_ok,
                bronze_success_key=artifacts.bronze_success_key,
                silver_success_key=artifacts.silver_success_key,
            )

        # Fail fast si DDB FAILED
        if state.status == "FAILED":
            return SmokeResult(
                source=source,
                entity=entity,
                run_id=run_id,
                ddb_status=state.status,
                bronze_ok=bronze_ok,
                silver_ok=silver_ok,
                bronze_success_key=artifacts.bronze_success_key,
                silver_success_key=artifacts.silver_success_key,
            )

        time.sleep(cfg.poll_interval_sec)

    # timeout
    return SmokeResult(
        source=source,
        entity=entity,
        run_id=run_id,
        ddb_status=last_status,
        bronze_ok=last_bronze_ok,
        silver_ok=last_silver_ok,
        bronze_success_key=(last_artifacts.bronze_success_key if last_artifacts else None),
        silver_success_key=(last_artifacts.silver_success_key if last_artifacts else None),
    )


def print_system_snapshot(cfg: SmokeConfig) -> None:
    clients = make_aws_clients(cfg.region)

    ingest_counts = get_queue_counts(clients.sts, clients.sqs, cfg.region, cfg.ingest_queue_name)
    transform_counts = get_queue_counts(clients.sts, clients.sqs, cfg.region, cfg.transform_queue_name)

    print("--- SQS snapshot ---")
    print(f"ingest   : visible={ingest_counts.visible} inflight={ingest_counts.inflight}")
    print(f"transform: visible={transform_counts.visible} inflight={transform_counts.inflight}")
