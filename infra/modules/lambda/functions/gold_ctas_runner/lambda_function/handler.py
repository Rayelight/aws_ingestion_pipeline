import os
import time
import boto3

athena = boto3.client("athena")
s3 = boto3.client("s3")

def lambda_handler(event, context):
    """
    event attendu (ex) :
    {
      "query_key": "configs/gold/sql/gold_trades.sql",
      "output_prefix": "data/gold/trades/"
    }
    """
    sql_bucket = os.environ["GOLD_SQL_BUCKET"]
    query_key  = event["query_key"]

    obj = s3.get_object(Bucket=sql_bucket, Key=query_key)
    sql = obj["Body"].read().decode("utf-8")

    workgroup = os.environ["ATHENA_WORKGROUP"]
    db = os.environ["GLUE_DATABASE_NAME"]

    # Le SQL CTAS doit contenir sa propre LOCATION vers s3://.../data/gold/...
    qid = athena.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": db},
        WorkGroup=workgroup,
    )["QueryExecutionId"]

    # wait simple
    while True:
        st = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]["State"]
        if st in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
        time.sleep(2)

    if st != "SUCCEEDED":
        raise RuntimeError(f"Athena query failed: {qid} state={st}")

    return {"query_execution_id": qid, "state": st}
