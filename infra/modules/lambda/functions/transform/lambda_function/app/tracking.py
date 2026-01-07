from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import boto3
from botocore.config import Config as BotoConfig

_ddb = boto3.client("dynamodb", config=BotoConfig(retries={"max_attempts": 5, "mode": "standard"}))


def _s(v: str) -> Dict[str, str]:
    return {"S": v}


def _n(v: int) -> Dict[str, str]:
    return {"N": str(v)}


def _json(v: Dict[str, Any]) -> Dict[str, str]:
    return {"S": json.dumps(v, ensure_ascii=False)}


@dataclass(frozen=True)
class RunKey:
    pk: str
    sk: str  # run_id


class TrackingStore:
    def __init__(self, table_name: str) -> None:
        self.table_name = table_name

    def upsert_requested(self, rk: RunKey, source: str, entity: str, run_id: str, params: Dict[str, Any]) -> None:
        now = int(time.time() * 1000)
        _ddb.put_item(
            TableName=self.table_name,
            Item={
                "pk": _s(rk.pk),
                "sk": _s(rk.sk),
                "source": _s(source),
                "entity": _s(entity),
                "run_id": _s(run_id),
                "status": _s("REQUESTED"),
                "requested_at_ms": _n(now),
                "params": _json(params),
            },
        )

    def update_status(self, rk: RunKey, status: str, extra: Optional[Dict[str, Any]] = None) -> None:
        now = int(time.time() * 1000)
        expr = "SET #s = :s, updated_at_ms = :t"
        names = {"#s": "status"}
        vals = {":s": _s(status), ":t": _n(now)}

        if extra:
            # on stocke l’extra en JSON string simple
            expr += ", extra = :e"
            vals[":e"] = _json(extra)

        _ddb.update_item(
            TableName=self.table_name,
            Key={"pk": _s(rk.pk), "sk": _s(rk.sk)},
            UpdateExpression=expr,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=vals,
        )

    def mark_failed(self, rk: RunKey, error_message: str) -> None:
        self.update_status(rk, "FAILED", extra={"error": error_message})
