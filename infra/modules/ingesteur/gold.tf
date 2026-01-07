module "gold_ctas" {
  source = "../gold_ctas"

  project = var.project
  env     = var.env
  tags    = var.tags

  datalake_bucket_name   = var.datalake_bucket_name
  monitoring_bucket_name = var.monitoring_bucket_name

  glue_database_name    = module.glue_catalog.glue_database_name
  athena_workgroup_name = module.athena.workgroup_name

  gold_sql_prefix = "configs/gold/sql/"
  gold_s3_prefix  = "data/gold/"

  # si tu veux lui mettre tes layers "common"
  lambda_layers = []
}
