from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from tools.common.app_config import load_app_config
from tools.common.aws_clients import make_aws_clients, get_account_id
from tools.common.contracts_loader import load_contract_from_s3, ContractSpec

from .models import IngestionRequest
from .validator import (
    RequestValidationError,
    validate_request,
    validate_params_against_contract,
    validate_params_shape,
)


@dataclass(frozen=True)
class RequesterConfig:
    region: str
    datalake_bucket: str

    ingest_queue_name: str
    transform_schema_check: bool

    s3_contracts_prefix: str
    s3_schema_prefix: str

    # Generic defaults
    default_limit: int
    default_time_window_minutes: int  # used when deriving start_ms/end_ms from date/hour


def load_requester_config() -> RequesterConfig:
    app = load_app_config()
    return RequesterConfig(
        region=app.aws.region,
        datalake_bucket=app.aws.datalake_bucket,
        ingest_queue_name=app.aws.ingest_queue_name,
        transform_schema_check=True,
        s3_contracts_prefix=app.prefixes.s3_contracts_prefix,
        s3_schema_prefix=app.prefixes.s3_schema_prefix,
        default_limit=1000,
        default_time_window_minutes=60,
    )


def _queue_url(region: str, account_id: str, queue_name: str) -> str:
    return f"https://sqs.{region}.amazonaws.com/{account_id}/{queue_name}"


def _contract_key(cfg: RequesterConfig, source: str, entity: str) -> str:
    return f"{cfg.s3_contracts_prefix}{source}/{entity}.yaml"


def _schema_key(cfg: RequesterConfig, source: str, entity: str) -> str:
    return f"{cfg.s3_schema_prefix}{source}/{entity}.yaml"


def _head_s3_object(s3_client, bucket: str, key: str) -> bool:
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except Exception:
        return False


def _iso_utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _default_run_id(source: str, entity: str, params: Dict[str, Any]) -> str:
    """
    run_id stable & lisible.
    Si date/hour existent -> format proche ancien script.
    Sinon timestamp.
    """
    date = params.get("date")
    hour = params.get("hour")
    symbol = params.get("symbol")
    endpoint = params.get("endpoint") or entity

    if date and hour and symbol:
        return f"{date}T{hour}-{source}-{endpoint}-{symbol}"
    return f"{_iso_utc_now_compact()}-{source}-{entity}"


def _derive_time_window_ms_from_date_hour(
    date_str: str,
    hour_str: str,
    window_minutes: int,
) -> Tuple[int, int]:
    """
    Derive start_ms/end_ms in UTC from date(YYYY-MM-DD) + hour(HH).
    """
    if not isinstance(date_str, str) or len(date_str) != 10:
        raise RequestValidationError("date must be YYYY-MM-DD to derive start_ms/end_ms")
    if not isinstance(hour_str, str) or len(hour_str) != 2:
        raise RequestValidationError("hour must be HH to derive start_ms/end_ms")

    dt_start = datetime(
        year=int(date_str[0:4]),
        month=int(date_str[5:7]),
        day=int(date_str[8:10]),
        hour=int(hour_str),
        minute=0,
        second=0,
        tzinfo=timezone.utc,
    )
    dt_end = dt_start + timedelta(minutes=window_minutes)
    start_ms = int(dt_start.timestamp() * 1000)
    end_ms = int(dt_end.timestamp() * 1000)
    return start_ms, end_ms


def _fill_defaults_and_derivations(cfg: RequesterConfig, contract: ContractSpec, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generic enrichment:
    - if 'limit' is needed by placeholders and missing => default_limit
    - if 'start_ms'/'end_ms' required (or needed by placeholders) and missing:
        - derive from date/hour if provided (UTC) with default window
    """
    out = dict(params)

    needed = set(contract.query_placeholders)

    # default limit
    if "limit" in needed and ("limit" not in out or out.get("limit") in (None, "")):
        out["limit"] = cfg.default_limit

    # derive time window
    need_start = ("start_ms" in needed) or ("start_ms" in contract.required_params)
    need_end = ("end_ms" in needed) or ("end_ms" in contract.required_params)

    if (need_start and (out.get("start_ms") in (None, ""))) or (need_end and (out.get("end_ms") in (None, ""))):
        # only if date/hour exist
        if out.get("date") and out.get("hour"):
            start_ms, end_ms = _derive_time_window_ms_from_date_hour(
                date_str=str(out["date"]),
                hour_str=str(out["hour"]),
                window_minutes=cfg.default_time_window_minutes,
            )
            out.setdefault("start_ms", start_ms)
            out.setdefault("end_ms", end_ms)

    return out


def build_request_from_contract(
    source: str,
    entity: str,
    params: Dict[str, Any],
    run_id: Optional[str] = None,
) -> IngestionRequest:
    """
    ✅ Adaptable à toute API :
    - lit le contract en S3
    - enrichit params (defaults/derivations génériques)
    - valide contre contract.params + placeholders
    - construit un message SQS minimal
    """
    cfg = load_requester_config()
    clients = make_aws_clients(cfg.region)

    validate_params_shape(params)

    ck = _contract_key(cfg, source, entity)
    sk = _schema_key(cfg, source, entity)

    if not _head_s3_object(clients.s3, cfg.datalake_bucket, ck):
        raise RuntimeError(f"Missing contract in S3: s3://{cfg.datalake_bucket}/{ck}")
    if cfg.transform_schema_check and not _head_s3_object(clients.s3, cfg.datalake_bucket, sk):
        raise RuntimeError(f"Missing schema in S3: s3://{cfg.datalake_bucket}/{sk}")

    contract = load_contract_from_s3(
        s3_client=clients.s3,
        bucket=cfg.datalake_bucket,
        key=ck,
        expected_source=source,
        expected_entity=entity,
    )

    enriched_params = _fill_defaults_and_derivations(cfg, contract, params)

    # validate params vs contract
    validate_params_against_contract(
        params=enriched_params,
        required=contract.required_params,
        optional=contract.optional_params,
        placeholders=contract.query_placeholders,
    )

    rid = run_id or _default_run_id(source, entity, enriched_params)
    req = IngestionRequest(source=source, entity=entity, run_id=rid, params=enriched_params)
    validate_request(req)
    return req


def send_request(req: IngestionRequest) -> str:
    """
    Envoie 1 message SQS.
    """
    cfg = load_requester_config()
    clients = make_aws_clients(cfg.region)
    account_id = get_account_id(clients.sts)
    qurl = _queue_url(cfg.region, account_id, cfg.ingest_queue_name)

    body = json.dumps(
        {"source": req.source, "entity": req.entity, "run_id": req.run_id, "params": req.params},
        ensure_ascii=False,
    )
    resp = clients.sqs.send_message(QueueUrl=qurl, MessageBody=body)
    return resp["MessageId"]


def request_and_send(
    source: str,
    entity: str,
    params: Dict[str, Any],
    run_id: Optional[str] = None,
) -> str:
    """
    Convenience: build from contract + send.
    """
    req = build_request_from_contract(source=source, entity=entity, params=params, run_id=run_id)
    mid = send_request(req)
    print(f"✅ Sent: {source}/{entity} run_id={req.run_id}")
    print(f"→ MessageId: {mid}")
    return mid


def request_hourly(
    source: str,
    entity: str,
    date: str,
    endpoint: str,
    base_params: Dict[str, Any],
    hours: Optional[List[int]] = None,
) -> List[Tuple[str, str]]:
    """
    Batch helper (optionnel) :
    envoie des runs par heure en réutilisant build_request_from_contract.
    Compatible avec n’importe quel dataset qui a date/hour dans ses params.
    """
    hours = hours or list(range(0, 24))
    results: List[Tuple[str, str]] = []
    for h in hours:
        hour_str = str(h).zfill(2)
        params = dict(base_params)
        params.update({"date": date, "hour": hour_str, "endpoint": endpoint})

        req = build_request_from_contract(source=source, entity=entity, params=params, run_id=None)
        mid = send_request(req)
        results.append((hour_str, mid))

        print(f"✅ Sent hourly: {source}/{entity} date={date} hour={hour_str} run_id={req.run_id}")
        print(f"→ MessageId: {mid}")

    return results
