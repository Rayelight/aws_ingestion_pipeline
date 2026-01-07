from __future__ import annotations

import json
from typing import Any, Dict, List

from app.config import load_config
from app.logging_utils import logger
from app.s3_utils import exists, get_text, put_bytes
from app.schema import load_schema_from_s3
from app.transforms import apply_transforms
from app.parquet_writer import rows_to_parquet_bytes
from app.tracking import TrackingStore, RunKey


def _build_partition_prefix(base: str, part_values: Dict[str, Any]) -> str:
    # S3 hive-style: k=v/
    pieces = []
    for k, v in part_values.items():
        pieces.append(f"{k}={v}")
    return base.rstrip("/") + "/" + "/".join(pieces) + "/" if pieces else base.rstrip("/") + "/"


def process_transform_message(msg: Dict[str, Any]) -> None:
    cfg = load_config()

    source = str(msg["source"])
    entity = str(msg["entity"])
    run_id = str(msg["run_id"])
    params = msg.get("params") or {}

    bronze_bucket = str(msg["bronze_bucket"])
    bronze_key = str(msg["bronze_key"])

    rk = RunKey(pk=f"{source}#{entity}", sk=run_id)
    tracking = TrackingStore(cfg.tracking_table)

    schema_key = f"{cfg.config_prefix_schema}{source}/{entity}.yaml"
    schema = load_schema_from_s3(cfg.datalake_bucket, schema_key, expected_source=source, expected_entity=entity)

    silver_cfg = schema.silver
    transforms = silver_cfg.get("transforms") or {}
    partitioning = (silver_cfg.get("partitioning") or {})

    # Read bronze JSONL
    text = get_text(bronze_bucket, bronze_key).strip()
    if not text:
        tracking.update_status(rk, "SILVER_WRITTEN", extra={"empty": True})
        return

    rows: List[Dict[str, Any]] = [json.loads(line) for line in text.splitlines() if line.strip()]

    try:
        # Apply transforms
        out_rows = apply_transforms(rows, transforms=transforms, params=params)

        # Partition values
        part_values: Dict[str, Any] = {}

        # by_params
        for p in partitioning.get("by_params") or []:
            if p not in params:
                raise ValueError(f"partitioning.by_params missing param: {p}")
            part_values[p] = params[p]

        # by_columns
        for c in partitioning.get("by_columns") or []:
            if c not in out_rows[0]:
                raise ValueError(f"partitioning.by_columns missing column: {c}")
            part_values[c] = out_rows[0].get(c)

        base = f"{cfg.data_prefix_silver}source={source}/entity={entity}/"
        silver_prefix = _build_partition_prefix(base, part_values) + f"run_id={run_id}/"

        success_key = silver_prefix + "_SUCCESS"
        out_key = silver_prefix + "part-00000.parquet"

        if exists(cfg.datalake_bucket, success_key):
            tracking.update_status(rk, "SILVER_WRITTEN", extra={"silver_key": out_key, "skipped": True})
            return

        parquet_bytes = rows_to_parquet_bytes(out_rows)
        put_bytes(cfg.datalake_bucket, out_key, parquet_bytes, content_type="application/octet-stream")
        put_bytes(cfg.datalake_bucket, success_key, b"")

        tracking.update_status(rk, "SILVER_WRITTEN", extra={"silver_key": out_key, "schema_key": schema_key})
        logger.info("transform_done", extra={"extra": {"run_id": run_id, "silver_key": out_key, "rows": len(out_rows)}})

    except Exception as e:
        tracking.mark_failed(rk, str(e))
        raise
