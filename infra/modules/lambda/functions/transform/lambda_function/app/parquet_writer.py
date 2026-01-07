from __future__ import annotations

import io
from typing import Any, Dict, List

import pyarrow as pa
import pyarrow.parquet as pq


def rows_to_parquet_bytes(rows: List[Dict[str, Any]]) -> bytes:
    table = pa.Table.from_pylist(rows)
    buf = io.BytesIO()
    pq.write_table(table, buf, compression="snappy")
    return buf.getvalue()
