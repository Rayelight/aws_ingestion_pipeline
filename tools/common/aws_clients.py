from __future__ import annotations

from dataclasses import dataclass

import boto3
from botocore.config import Config as BotoConfig


@dataclass(frozen=True)
class AwsClients:
    sts: any
    sqs: any
    s3: any
    dynamodb: any


def make_aws_clients(region: str) -> AwsClients:
    cfg = BotoConfig(retries={"max_attempts": 8, "mode": "standard"})
    return AwsClients(
        sts=boto3.client("sts", region_name=region, config=cfg),
        sqs=boto3.client("sqs", region_name=region, config=cfg),
        s3=boto3.client("s3", region_name=region, config=cfg),
        dynamodb=boto3.client("dynamodb", region_name=region, config=cfg),
    )


def get_account_id(sts_client) -> str:
    return sts_client.get_caller_identity()["Account"]
