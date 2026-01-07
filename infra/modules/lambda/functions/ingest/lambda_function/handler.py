import json
from typing import Any, Dict

from app.logging_utils import logger, with_context
from app.ingest_service import process_ingest_message


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    records = event.get("Records", [])
    failures = []

    for rec in records:
        msg_id = rec.get("messageId", "unknown")
        try:
            body = json.loads(rec["body"])
            with_context(message_id=msg_id, source=body.get("source"), entity=body.get("entity"), run_id=body.get("run_id"))
            process_ingest_message(body)
        except Exception as e:
            logger.exception("ingest_failed", extra={"message_id": msg_id, "error": str(e)})
            failures.append({"itemIdentifier": msg_id})

    # SQS partial batch response
    return {"batchItemFailures": failures}
