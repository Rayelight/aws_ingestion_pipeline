from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, List, Optional


@dataclass(frozen=True)
class RunArtifacts:
    bronze_success_key: Optional[str]
    bronze_data_key: Optional[str]
    silver_success_key: Optional[str]
    silver_parquet_key: Optional[str]


def _list_keys(s3_client, bucket: str, prefix: str) -> Iterator[str]:
    token = None
    while True:
        kwargs = {"Bucket": bucket, "Prefix": prefix, "MaxKeys": 1000}
        if token:
            kwargs["ContinuationToken"] = token
        resp = s3_client.list_objects_v2(**kwargs)
        for obj in resp.get("Contents", []):
            yield obj["Key"]
        if resp.get("IsTruncated"):
            token = resp.get("NextContinuationToken")
        else:
            break


def find_run_artifacts(
    s3_client,
    bucket: str,
    bronze_prefix: str,
    silver_prefix: str,
    source: str,
    entity: str,
    run_id: str,
) -> RunArtifacts:
    """
    Cherche par run_id sous:
      data/bronze/source=<source>/entity=<entity>/
      data/silver/source=<source>/entity=<entity>/
    """
    bronze_root = f"{bronze_prefix}source={source}/entity={entity}/"
    silver_root = f"{silver_prefix}source={source}/entity={entity}/"

    # run folder fragment
    run_fragment = f"run_id={run_id}/"

    bronze_success = None
    bronze_data = None
    for k in _list_keys(s3_client, bucket, bronze_root):
        if run_fragment not in k:
            continue
        if k.endswith("_SUCCESS"):
            bronze_success = k
        elif k.endswith("data.jsonl"):
            bronze_data = k

    silver_success = None
    silver_parquet = None
    for k in _list_keys(s3_client, bucket, silver_root):
        if run_fragment not in k:
            continue
        if k.endswith("_SUCCESS"):
            silver_success = k
        elif k.endswith(".parquet"):
            silver_parquet = k

    return RunArtifacts(
        bronze_success_key=bronze_success,
        bronze_data_key=bronze_data,
        silver_success_key=silver_success,
        silver_parquet_key=silver_parquet,
    )
