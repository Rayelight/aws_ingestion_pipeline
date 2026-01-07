variable "project" { type = string }
variable "env" { type = string }

variable "datalake_bucket_name" { type = string }

variable "ingest_queue_arn" { type = string }
variable "ingest_queue_url" { type = string }

variable "transform_queue_arn" { type = string }
variable "transform_queue_url" { type = string }

variable "lambda_ingest_role_arn" { type = string }
variable "lambda_transform_role_arn" { type = string }

variable "lambda_ingest_timeout_sec" {
  type    = number
  default = 60
}
variable "lambda_transform_timeout_sec" {
  type    = number
  default = 300
}

variable "lambda_ingest_memory_mb" {
  type    = number
  default = 256
}
variable "lambda_transform_memory_mb" {
  type    = number
  default = 512
}

variable "layers" {
  type        = list(string)
  default     = []
  description = "Liste d'ARNs de layers à attacher aux lambdas"
}

variable "log_retention_days" {
  type    = number
  default = 30
}

variable "tags" {
  type    = map(string)
  default = {}
}

variable "tracking_table_name" { type = string }

variable "configs_contracts_prefix" {
  type    = string
  default = "configs/contracts/"
}
variable "configs_schema_prefix" {
  type    = string
  default = "configs/schema/"
}

variable "data_bronze_prefix" {
  type    = string
  default = "data/bronze/"
}
variable "data_silver_prefix" {
  type    = string
  default = "data/silver/"
}
