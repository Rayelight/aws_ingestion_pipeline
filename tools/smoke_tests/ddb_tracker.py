from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional


def _s(v: str) -> Dict[str, str]:
    return {"S": v}


@dataclass(frozen=True)
class DdbRunState:
    status: Optional[str]
    extra: Optional[Dict[str, Any]]


def get_run_state(dynamodb_client, table_name: str, source: str, entity: str, run_id: str) -> DdbRunState:
    pk = f"{source}#{entity}"
    sk = run_id

    resp = dynamodb_client.get_item(
        TableName=table_name,
        Key={"pk": _s(pk), "sk": _s(sk)},
        ConsistentRead=True,
    )

    item = resp.get("Item")
    if not item:
        return DdbRunState(status=None, extra=None)

    status = item.get("status", {}).get("S")
    extra_raw = item.get("extra", {}).get("S")
    extra = None
    if extra_raw:
        try:
            extra = json.loads(extra_raw)
        except Exception:
            extra = {"_raw": extra_raw}

    return DdbRunState(status=status, extra=extra)
