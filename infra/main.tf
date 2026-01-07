module "ingesteur" {
  source = "./modules/ingesteur"

  project = var.project
  env     = var.env
  region  = var.region

  monitoring_bucket_name   = "ingesteur-dev-monitoring"
  monitoring_force_destroy = true

  datalake_bucket_name   = "ingesteur-dev-datalake"
  datalake_force_destroy = true

  lambda_ingest_timeout_sec    = 60
  lambda_transform_timeout_sec = 300

  ingest_schedule_expression = "rate(1 hour)"

  # can be set to any ingestion
  ingest_default_message = {
    source = "my_api"
    entity = "orders"
    params = {}
  }

  use_layer          = true
  lambda_layers_list = ["base", "parquet"]

  log_retention_days = 30

  tags = var.tags
}
