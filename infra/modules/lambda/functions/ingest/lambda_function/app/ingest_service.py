from __future__ import annotations

import json
import uuid
import datetime as dt
from typing import Any, Dict, List, Union

from app.config import load_config
from app.logging_utils import logger
from app.s3_utils import exists, put_bytes, sha256
from app.sqs_utils import send_json
from app.api_client import ApiClient
from app.contracts import load_contract_from_s3
from app.templating import render_templates
from app.tracking import TrackingStore, RunKey
from app.response_mapping import apply_response_mapping



def _utc_now() -> dt.datetime:
    return dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)


def _partition_parts(now: dt.datetime) -> tuple[str, str]:
    return now.strftime("%Y-%m-%d"), now.strftime("%H")


def _to_jsonl(payload: Union[Dict[str, Any], List[Any]]) -> bytes:
    if isinstance(payload, list):
        lines = [json.dumps(x, ensure_ascii=False) for x in payload]
    else:
        lines = [json.dumps(payload, ensure_ascii=False)]
    return (("\n".join(lines)) + "\n").encode("utf-8")


def process_ingest_message(msg: Dict[str, Any]) -> None:
    cfg = load_config()

    source = str(msg["source"])
    entity = str(msg["entity"])
    run_id = str(msg.get("run_id") or uuid.uuid4())
    params = msg.get("params") or {}

    rk = RunKey(pk=f"{source}#{entity}", sk=run_id)
    tracking = TrackingStore(cfg.tracking_table)

    # 0) Track requested (idempotence métier possible ici si tu veux plus tard)
    tracking.upsert_requested(rk, source=source, entity=entity, run_id=run_id, params=params)

    # 1) Charger contrat + schema key dérivés (schema sera surtout utilisé par transform)
    contract_key = f"{cfg.config_prefix_contracts}{source}/{entity}.yaml"
    schema_key = f"{cfg.config_prefix_schema}{source}/{entity}.yaml"
    contract = load_contract_from_s3(cfg.datalake_bucket, contract_key, expected_source=source, expected_entity=entity)

    now = _utc_now()
    ingestion_dt, ingestion_hr = _partition_parts(now)

    base = (
        f"{cfg.data_prefix_bronze}"
        f"source={source}/entity={entity}/"
        f"ingestion_dt={ingestion_dt}/ingestion_hr={ingestion_hr}/"
        f"run_id={run_id}/"
    )
    success_key = base + "_SUCCESS"
    data_key = base + "data.jsonl"
    manifest_key = base + "manifest.json"

    # idempotence par marker S3
    if exists(cfg.datalake_bucket, success_key):
        logger.info("ingest_skip_already_done", extra={"extra": {"run_id": run_id, "data_key": data_key}})
        tracking.update_status(rk, "BRONZE_WRITTEN", extra={"bronze_key": data_key, "skipped": True})
        return

    try:
        api_cfg = contract.api
        method = str(api_cfg.get("method", "GET")).upper()
        base_url = str(api_cfg["base_url"])
        endpoint = str(api_cfg["endpoint"])
        headers = dict(api_cfg.get("headers") or {})

        query_tpl = dict(api_cfg.get("query") or {})
        query = render_templates(query_tpl, params)

        client = ApiClient(timeout_sec=cfg.api_timeout_sec, max_retries=cfg.api_max_retries)

        # V1: pagination simple (none). On ajoutera cursor/page ensuite.
        payload = client.request_json(method=method, base_url=base_url, endpoint=endpoint, headers=headers,
                                      params=query)

        # Optional response mapping (e.g. klines array->object)
        mapping = api_cfg.get("response_mapping")
        if mapping:
            payload = apply_response_mapping(payload, mapping)

        data_bytes = _to_jsonl(payload)
        put_bytes(cfg.datalake_bucket, data_key, data_bytes, content_type="application/x-ndjson")

        manifest = {
            "contract": {"id": contract.id, "version": contract.version, "s3_key": contract_key},
            "schema_s3_key": schema_key,
            "source": source,
            "entity": entity,
            "run_id": run_id,
            "params": params,
            "ingested_at": now.isoformat(),
            "bronze_bucket": cfg.datalake_bucket,
            "bronze_key": data_key,
            "sha256": sha256(data_bytes),
            "bytes": len(data_bytes),
        }
        put_bytes(cfg.datalake_bucket, manifest_key, json.dumps(manifest).encode("utf-8"), content_type="application/json")
        put_bytes(cfg.datalake_bucket, success_key, b"")

        tracking.update_status(rk, "BRONZE_WRITTEN", extra={"bronze_key": data_key, "contract_key": contract_key})

        # 2) Trigger transform (on n’envoie que source/entity, la lambda transform déduira schema)
        send_json(cfg.transform_queue_url, {
            "source": source,
            "entity": entity,
            "run_id": run_id,
            "params": params,
            "bronze_bucket": cfg.datalake_bucket,
            "bronze_key": data_key,
        })

        logger.info("ingest_done", extra={"extra": {"run_id": run_id, "bronze_key": data_key}})

    except Exception as e:
        tracking.mark_failed(rk, str(e))
        raise
