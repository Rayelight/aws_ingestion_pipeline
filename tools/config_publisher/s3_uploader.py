from __future__ import annotations

import hashlib
from dataclasses import dataclass

import boto3


@dataclass(frozen=True)
class UploadResult:
    s3_key: str
    size_kb: float
    sha256_12: str


class S3Uploader:
    def __init__(self, region: str, bucket: str) -> None:
        self.bucket = bucket
        self.s3 = boto3.client("s3", region_name=region)

    def put_yaml(self, key: str, text: str) -> UploadResult:
        data = text.encode("utf-8")
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType="text/yaml")
        sha = hashlib.sha256(data).hexdigest()[:12]
        size_kb = len(data) / 1024.0
        return UploadResult(s3_key=key, size_kb=size_kb, sha256_12=sha)
