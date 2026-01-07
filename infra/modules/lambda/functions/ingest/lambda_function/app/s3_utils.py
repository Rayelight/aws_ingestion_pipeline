from __future__ import annotations

import hashlib
from typing import Optional

import boto3
from botocore.config import Config as BotoConfig

_s3 = boto3.client("s3", config=BotoConfig(retries={"max_attempts": 5, "mode": "standard"}))


def exists(bucket: str, key: str) -> bool:
    try:
        _s3.head_object(Bucket=bucket, Key=key)
        return True
    except Exception:
        return False


def get_bytes(bucket: str, key: str) -> bytes:
    obj = _s3.get_object(Bucket=bucket, Key=key)
    return obj["Body"].read()


def get_text(bucket: str, key: str, encoding: str = "utf-8") -> str:
    return get_bytes(bucket, key).decode(encoding)


def put_bytes(bucket: str, key: str, data: bytes, content_type: Optional[str] = None) -> None:
    kwargs = {"Bucket": bucket, "Key": key, "Body": data}
    if content_type:
        kwargs["ContentType"] = content_type
    _s3.put_object(**kwargs)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
