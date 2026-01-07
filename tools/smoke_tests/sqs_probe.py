from __future__ import annotations

from dataclasses import dataclass

from tools.common.aws_clients import get_account_id


@dataclass(frozen=True)
class QueueCounts:
    visible: int
    inflight: int


def _queue_url(region: str, account_id: str, queue_name: str) -> str:
    return f"https://sqs.{region}.amazonaws.com/{account_id}/{queue_name}"


def get_queue_counts(sts_client, sqs_client, region: str, queue_name: str) -> QueueCounts:
    account_id = get_account_id(sts_client)
    url = _queue_url(region, account_id, queue_name)

    resp = sqs_client.get_queue_attributes(
        QueueUrl=url,
        AttributeNames=["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"],
    )
    attrs = resp.get("Attributes", {})
    return QueueCounts(
        visible=int(attrs.get("ApproximateNumberOfMessages", "0")),
        inflight=int(attrs.get("ApproximateNumberOfMessagesNotVisible", "0")),
    )
