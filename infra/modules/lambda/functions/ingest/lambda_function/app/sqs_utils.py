import json
from typing import Any, Dict

import boto3
from botocore.config import Config as BotoConfig

_sqs = boto3.client("sqs", config=BotoConfig(retries={"max_attempts": 5, "mode": "standard"}))


def send_json(queue_url: str, payload: Dict[str, Any]) -> None:
    _sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(payload))
