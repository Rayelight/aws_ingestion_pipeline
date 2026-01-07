locals {
  name_prefix               = "${var.project}-${var.env}"
  lambda_ingest_zip_path    = "${path.module}/functions/ingest/package/lambda.zip"
  lambda_transform_zip_path = "${path.module}/functions/transform/package/lambda.zip"
}

resource "aws_cloudwatch_log_group" "ingest" {
  name              = "/aws/lambda/${local.name_prefix}-ingest"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

resource "aws_cloudwatch_log_group" "transform" {
  name              = "/aws/lambda/${local.name_prefix}-transform"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

resource "aws_lambda_function" "ingest" {
  function_name = "${local.name_prefix}-ingest"
  role          = var.lambda_ingest_role_arn

  runtime       = "python3.12"
  architectures = ["x86_64"]
  handler       = "handler.handler"

  filename         = local.lambda_ingest_zip_path
  source_code_hash = filebase64sha256(local.lambda_ingest_zip_path)

  timeout     = var.lambda_ingest_timeout_sec
  memory_size = var.lambda_ingest_memory_mb
  layers      = var.layers

  environment {
    variables = {
      DATALAKE_BUCKET = var.datalake_bucket_name

      CONFIG_PREFIX_CONTRACTS = var.configs_contracts_prefix
      CONFIG_PREFIX_SCHEMA    = var.configs_schema_prefix

      DATA_PREFIX_BRONZE = var.data_bronze_prefix

      TRANSFORM_QUEUE_URL = var.transform_queue_url

      TRACKING_TABLE = var.tracking_table_name
    }
  }

  tags       = var.tags
  depends_on = [aws_cloudwatch_log_group.ingest]
}

resource "aws_lambda_function" "transform" {
  function_name = "${local.name_prefix}-transform"
  role          = var.lambda_transform_role_arn

  runtime       = "python3.12"
  architectures = ["x86_64"]
  handler       = "handler.handler"

  filename         = local.lambda_transform_zip_path
  source_code_hash = filebase64sha256(local.lambda_transform_zip_path)

  timeout     = var.lambda_transform_timeout_sec
  memory_size = var.lambda_transform_memory_mb
  layers      = var.layers

  environment {
    variables = {
      DATALAKE_BUCKET = var.datalake_bucket_name

      CONFIG_PREFIX_SCHEMA = var.configs_schema_prefix

      DATA_PREFIX_BRONZE = var.data_bronze_prefix
      DATA_PREFIX_SILVER = var.data_silver_prefix

      TRACKING_TABLE = var.tracking_table_name
    }
  }

  tags       = var.tags
  depends_on = [aws_cloudwatch_log_group.transform]
}

resource "aws_lambda_event_source_mapping" "ingest_sqs" {
  event_source_arn = var.ingest_queue_arn
  function_name    = aws_lambda_function.ingest.arn
  batch_size       = 1
}

resource "aws_lambda_event_source_mapping" "transform_sqs" {
  event_source_arn = var.transform_queue_arn
  function_name    = aws_lambda_function.transform.arn
  batch_size       = 1
}
