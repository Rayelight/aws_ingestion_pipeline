# s3 monitoring outputs
output "monitoring_bucket_name" { value = module.s3_monitoring.bucket_name }
output "monitoring_bucket_arn" { value = module.s3_monitoring.bucket_arn }

# s3 datalake outputs
output "datalake_bucket_name" { value = module.s3_datalake.bucket_name }
output "datalake_bucket_arn" { value = module.s3_datalake.bucket_arn }

# sqs outputs
output "sqs_ingest_queue_url" { value = module.sqs.ingest_queue_url }
output "sqs_transform_queue_url" { value = module.sqs.transform_queue_url }

output "sqs_ingest_dlq_name" { value = module.sqs.ingest_dlq_name }
output "sqs_transform_dlq_name" { value = module.sqs.transform_dlq_name }

# eventbridge ingest schedule outputs
output "ingest_schedule_rule_name" {
  value = module.eventbridge_ingest_schedule.rule_name
}


# iam outputs
output "lambda_ingest_role_arn" { value = module.iam.lambda_ingest_role_arn }
output "lambda_transform_role_arn" { value = module.iam.lambda_transform_role_arn }
output "glue_role_arn" { value = module.iam.glue_role_arn }


# lambda outputs
output "lambda_ingest_function_name" { value = module.lambda.ingest_function_name }
output "lambda_transform_function_name" { value = module.lambda.transform_function_name }

output "lambda_layers_arn" {
  value = local.lambda_layers
}


#dynamodb outputs
output "tracking_table_name" { value = module.dynamodb_ingestion_tracking.table_name }
output "tracking_table_arn" { value = module.dynamodb_ingestion_tracking.table_arn }


# athena and glue outputs
output "glue_database_name" {
  value = module.glue_catalog.glue_database_name
}

output "silver_crawler_name" {
  value = module.glue_catalog.silver_crawler_name
}

output "athena_workgroup_name" {
  value = module.athena.workgroup_name
}
