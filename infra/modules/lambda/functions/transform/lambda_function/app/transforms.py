from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional


class TransformError(ValueError):
    pass


SUPPORTED_TYPES = {
    "string",
    "int64",
    "float64",
    "boolean",
    "timestamp_ms",
    "timestamp_s",
    "date",
}


def apply_transforms(rows: List[Dict[str, Any]], transforms: Dict[str, Any], params: Dict[str, Any]) -> List[Dict[str, Any]]:
    keep = transforms.get("keep")
    drop = transforms.get("drop")
    rename = transforms.get("rename") or {}
    add_columns = transforms.get("add_columns") or []
    cast = transforms.get("cast") or {}
    trim_cols = transforms.get("trim") or []
    lower_cols = transforms.get("lower") or []
    upper_cols = transforms.get("upper") or []
    null_if = transforms.get("null_if") or {}
    fillna = transforms.get("fillna") or {}
    required = transforms.get("required") or []
    non_null = transforms.get("non_null") or []

    # 1) keep/drop (sur noms originaux)
    out = []
    for r in rows:
        rr = dict(r)

        if keep:
            rr = {k: rr.get(k) for k in keep if k in rr}
        if drop:
            for k in drop:
                rr.pop(k, None)

        # 2) rename
        for old, new in rename.items():
            if old in rr:
                rr[new] = rr.pop(old)

        # 3) add_columns
        for spec in add_columns:
            name = spec["name"]
            if "from_param" in spec:
                rr[name] = params.get(spec["from_param"])
            elif "literal" in spec:
                rr[name] = spec["literal"]
            elif "from_column" in spec:
                rr[name] = rr.get(spec["from_column"])
            else:
                raise TransformError(f"add_columns invalid spec for {name}")

        # 4) cast (simple python cast; pyarrow fera aussi une inference)
        for col, typ in cast.items():
            if typ not in SUPPORTED_TYPES:
                raise TransformError(f"Unsupported type: {typ}")
            if col not in rr:
                continue
            rr[col] = _cast_value(rr[col], typ)

        # 5) trim/lower/upper/null_if/fillna
        for col in trim_cols:
            if isinstance(rr.get(col), str):
                rr[col] = rr[col].strip()

        for col in lower_cols:
            if isinstance(rr.get(col), str):
                rr[col] = rr[col].lower()

        for col in upper_cols:
            if isinstance(rr.get(col), str):
                rr[col] = rr[col].upper()

        for col, values in null_if.items():
            v = rr.get(col)
            if v in values:
                rr[col] = None

        for col, default in fillna.items():
            if rr.get(col) is None:
                rr[col] = default

        # 6) required/non_null validation
        for col in required:
            if col not in rr:
                raise TransformError(f"Missing required column: {col}")

        for col in non_null:
            if rr.get(col) is None:
                raise TransformError(f"Null value for non_null column: {col}")

        out.append(rr)

    return out


def _cast_value(v: Any, typ: str) -> Any:
    if v is None:
        return None
    if typ == "string":
        return str(v)
    if typ == "int64":
        return int(v)
    if typ == "float64":
        return float(v)
    if typ == "boolean":
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return bool(v)
        s = str(v).lower()
        return s in {"true", "1", "yes", "y"}
    if typ == "timestamp_ms":
        # keep as int milliseconds; parquet writer can map it later if needed
        return int(v)
    if typ == "timestamp_s":
        return int(v)
    if typ == "date":
        # accept YYYY-MM-DD
        if isinstance(v, str):
            return v
        if isinstance(v, dt.date):
            return v.isoformat()
        return str(v)
    raise TransformError(f"Unsupported cast type: {typ}")
