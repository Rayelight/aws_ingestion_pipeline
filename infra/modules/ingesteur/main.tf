module "s3_monitoring" {
  source = "../s3_monitoring"

  project       = var.project
  env           = var.env
  bucket_name   = var.monitoring_bucket_name
  force_destroy = var.monitoring_force_destroy
  tags          = var.tags
}

module "s3_datalake" {
  source = "../s3_datalake"

  project                = var.project
  env                    = var.env
  bucket_name            = var.datalake_bucket_name
  force_destroy          = var.datalake_force_destroy
  monitoring_bucket_name = module.s3_monitoring.bucket_name
  access_logs_prefix     = "s3-access/datalake/"
  tags                   = var.tags
}

module "sqs" {
  source = "../sqs"

  project = var.project
  env     = var.env

  lambda_ingest_timeout_sec    = var.lambda_ingest_timeout_sec
  lambda_transform_timeout_sec = var.lambda_transform_timeout_sec
  max_receive_count            = var.sqs_max_receive_count

  tags = var.tags
}

module "eventbridge_ingest_schedule" {
  source = "../eventbridge_ingest_schedule"

  project = var.project
  env     = var.env

  schedule_expression  = var.ingest_schedule_expression
  target_sqs_queue_arn = module.sqs.ingest_queue_arn
  target_sqs_queue_url = module.sqs.ingest_queue_url

  # Exemple de payload par défaut (tu peux le surcharger au root)
  default_message = var.ingest_default_message

  tags = var.tags
}

module "iam" {
  source = "../iam"

  project = var.project
  env     = var.env

  datalake_bucket_arn   = module.s3_datalake.bucket_arn
  monitoring_bucket_arn = module.s3_monitoring.bucket_arn

  sqs_ingest_queue_arn    = module.sqs.ingest_queue_arn
  sqs_transform_queue_arn = module.sqs.transform_queue_arn

  configs_contracts_prefix = "configs/contracts/"
  configs_schema_prefix    = "configs/schema/"

  bronze_prefix = "data/bronze/"
  silver_prefix = "data/silver/"
  gold_prefix   = "data/gold/"

  ingestion_tracking_table_arn = module.dynamodb_ingestion_tracking.table_arn

  tags = var.tags
}

module "lambda_layer" {
  for_each = toset(var.lambda_layers_list)
  source   = "../lambda_layer"

  project = var.project
  env     = var.env
  name    = each.key
  tags    = var.tags
}

locals {
  lambda_layers = var.use_layer ? [
    for name in var.lambda_layers_list : module.lambda_layer[name].layer_arn
  ] : []
}

module "lambda" {
  source = "../lambda"

  project = var.project
  env     = var.env

  datalake_bucket_name = module.s3_datalake.bucket_name

  ingest_queue_arn = module.sqs.ingest_queue_arn
  ingest_queue_url = module.sqs.ingest_queue_url

  transform_queue_arn = module.sqs.transform_queue_arn
  transform_queue_url = module.sqs.transform_queue_url

  lambda_ingest_role_arn    = module.iam.lambda_ingest_role_arn
  lambda_transform_role_arn = module.iam.lambda_transform_role_arn

  lambda_ingest_timeout_sec    = var.lambda_ingest_timeout_sec
  lambda_transform_timeout_sec = var.lambda_transform_timeout_sec

  log_retention_days = var.log_retention_days

  layers = local.lambda_layers
  tags   = var.tags

  tracking_table_name = module.dynamodb_ingestion_tracking.table_name

  configs_contracts_prefix = "configs/contracts/"
  configs_schema_prefix    = "configs/schema/"

  data_bronze_prefix = "data/bronze/"
  data_silver_prefix = "data/silver/"
}

locals {
  effective_tracking_table_name = (
    var.tracking_table_name == null
    ? "${var.project}-${var.env}-ingestion-runs"
    : var.tracking_table_name
  )
}

module "dynamodb_ingestion_tracking" {
  source = "../dynamodb"

  project    = var.project
  env        = var.env
  table_name = local.effective_tracking_table_name
  tags       = var.tags
}
