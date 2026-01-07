variable "project" { type = string }
variable "env" { type = string }

variable "datalake_bucket_arn" { type = string }
variable "monitoring_bucket_arn" { type = string }

variable "sqs_ingest_queue_arn" { type = string }
variable "sqs_transform_queue_arn" { type = string }

# Prefixes S3
variable "configs_contracts_prefix" {
  type    = string
  default = "configs/contracts/"
}
variable "configs_schema_prefix" {
  type    = string
  default = "configs/schema/"
}

variable "bronze_prefix" {
  type    = string
  default = "data/bronze/"
}
variable "silver_prefix" {
  type    = string
  default = "data/silver/"
}
variable "gold_prefix" {
  type    = string
  default = "data/gold/"
}


# Tracking table (DynamoDB)
variable "ingestion_tracking_table_arn" { type = string }

variable "tags" {
  type    = map(string)
  default = {}
}
