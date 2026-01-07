locals {
  glue_database_name    = "${var.project}_${var.env}"
  athena_workgroup_name = "${var.project}-${var.env}"
}

module "glue_catalog" {
  source = "../glue_catalog"

  project = var.project
  env     = var.env
  tags    = var.tags

  datalake_bucket_name = var.datalake_bucket_name
  glue_database_name   = local.glue_database_name
  silver_s3_prefix     = "data/silver/"

  # ✅ EventBridge trigger
  enable_eventbridge_crawler_trigger      = true
  eventbridge_crawler_schedule_expression = "rate(15 minutes)"

  # on n'utilise plus le schedule Glue natif
  crawler_schedule_expression = null
}


module "athena" {
  source = "../athena"

  project = var.project
  env     = var.env
  tags    = var.tags

  monitoring_bucket_name = var.monitoring_bucket_name

  athena_workgroup_name = local.athena_workgroup_name
  athena_results_prefix = "athena-results/"
}


